# app.py
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# your pipeline (must expose: async def main_function(gender, websocket=None))
from full_code import main_function

APP_ROOT = Path(__file__).parent.resolve()
INPUT_DIR = APP_ROOT / "input"
INPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="3D-GLB Pipeline API", version="1.0.0")

# ---- CORS (loose for dev; tighten for prod) ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # change to your domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Simple test page (optional) ----
@app.get("/", response_class=HTMLResponse)
def index():
    return """
<!doctype html>
<html>
  <head><meta charset="utf-8"><title>3D-GLB WS Test</title></head>
  <body>
    <h1>WebSocket Pipeline Test</h1>
    <p>Open the console to see messages.</p>
    <script>
      const ws = new WebSocket(`ws://${location.host}/ws`);
      ws.onopen = () => {
        console.log("WS open");
        // Tell server which gender to run
        ws.send(JSON.stringify({ gender: "male" }));
      };
      ws.onmessage = (ev) => {
        console.log("WS message:", ev.data);
      };
      ws.onclose = () => console.log("WS closed");
      ws.onerror = (e) => console.error("WS error", e);
    </script>
  </body>
</html>
    """

# ---- Healthcheck ----
@app.get("/health")
def health():
    py37 = os.getenv("PYTHON_37_PATH")
    py311 = os.getenv("PYTHON_311_PATH")
    return {
        "status": "ok",
        "cwd": str(APP_ROOT),
        "py37": py37,
        "py311": py311,
        "input_exists": INPUT_DIR.exists(),
        "input_files": sorted([p.name for p in INPUT_DIR.glob("*")]),
    }

# ---- HTTP upload + run (no streaming over HTTP; see /ws for live stream) ----
@app.post("/generate")
async def generate(
    gender: str = Form(..., pattern="^(male|female)$"),
    image: Optional[UploadFile] = File(None),
):
    """
    Use this if you just want a single HTTP request/response.
    - Saves the uploaded image (if provided) into ./input
    - Runs the pipeline to completion
    - Returns the best-known outputs (e.g., public GLB URL if your uploader wrote it)
    For live logs, use /ws instead.
    """
    # Save image if included
    if image is not None:
        dest_path = INPUT_DIR / image.filename
        with dest_path.open("wb") as f:
            f.write(await image.read())

    # Run the pipeline (server log will show progress; /ws streams it)
    try:
        await main_function(gender)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=f"Pipeline missing resource: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    # Try to return a public URL if your uploader wrote a manifest
    # (Adjust this to match whatever your supabase_upload.py writes.)
    manifest = APP_ROOT / "Blender" / "output" / "manifest.json"
    outputs = []
    if manifest.exists():
        try:
            import json
            with manifest.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                # Expecting a top-level "files" list with {"public_url": "..."} items
                outputs = [f.get("public_url") or f.get("signed_url") for f in data.get("files", []) if f]
                outputs = [u for u in outputs if u]  # remove Nones
        except Exception:
            pass
    else:
        # fallback: any .glb (not public URLs; just paths)
        out_dir = APP_ROOT / "Blender" / "output"
        if out_dir.exists():
            outputs = sorted([str(p) for p in out_dir.glob("*.glb")])

    return JSONResponse({"status": "completed", "gender": gender, "outputs": outputs})

# ---- WebSocket with live streaming ----
@app.websocket("/ws")
async def ws_progress(websocket: WebSocket):
    """
    1) Client connects via WS
    2) Immediately sends: {"gender":"male"|"female"}
    3) Server streams each step line-by-line as JSON messages:
       - {"status":"progress","stepIndex":...,"title":...}
       - {"status":"stream","stepIndex":...,"stream":"stdout|stderr","line":"..."}
       - {"status":"done-step",...}
       - {"status":"error",...}
       - {"status":"done","message":"..."}
    """
    await websocket.accept()
    try:
        init = await websocket.receive_json()
        gender = init.get("gender")
        if gender not in ("male", "female"):
            await websocket.send_json({"status": "error", "message": "gender must be 'male' or 'female'"})
            await websocket.close(code=1003)
            return

        # Kick off the pipeline; it will call websocket.send_json(...) for every line
        await main_function(gender, websocket=websocket)

        # Optionally send final manifest/public URLs (same logic as /generate)
        from json import load
        manifest = APP_ROOT / "Blender" / "output" / "manifest.json"
        outputs = []
        if manifest.exists():
            try:
                with manifest.open("r", encoding="utf-8") as fh:
                    data = load(fh)
                    outputs = [f.get("public_url") or f.get("signed_url") for f in data.get("files", []) if f]
                    outputs = [u for u in outputs if u]
            except Exception:
                outputs = []
        await websocket.send_json({"status": "done", "message": "Pipeline finished!", "outputs": outputs})
        await websocket.close(code=1000)

    except WebSocketDisconnect:
        # Client disconnected; you can choose to stop/ignore the running job.
        return
    except Exception as e:
        try:
            await websocket.send_json({"status": "error", "message": str(e)})
        finally:
            await websocket.close(code=1011)
