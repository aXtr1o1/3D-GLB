import os
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Import your pipeline's async function
# Make sure full_code.py is in the same directory (repo root).
from full_code import main_function

APP_ROOT = Path(__file__).parent.resolve()
INPUT_DIR = APP_ROOT / "input"
INPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="3D-GLB Pipeline API", version="1.0.0")

# Optional CORS (adjust origins to your needs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    # Basic sanity checks: Python paths via .env (optional)
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

@app.post("/generate")
async def generate(
    gender: str = Form(..., regex="^(male|female)$"),
    image: Optional[UploadFile] = File(None)
):
    """
    Upload an image (optional if already present in ./input) and run the pipeline.
    Returns JSON when finished. For live progress, use the /ws endpoint.
    """
    if image is not None:
        # Save uploaded image into ./input (pipeline reads from here)
        # Preserve original filename
        dest = INPUT_DIR / image.filename
        with dest.open("wb") as f:
            shutil.copyfileobj(image.file, f)

    # Run the pipeline; this will print progress to server logs.
    # For live progress over WebSocket, use /ws.
    try:
        await main_function(gender)
    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=f"Pipeline missing resource: {e}")
    except Exception as e:
        # Surface anything else as 500
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

    # If you want to return a specific artifact path, adjust here:
    output_dir = APP_ROOT / "Blender" / "output"
    outputs = sorted([str(p) for p in output_dir.glob("*.glb")]) if output_dir.exists() else []
    return JSONResponse({"status": "completed", "gender": gender, "outputs": outputs})

@app.websocket("/ws")
async def ws_progress(websocket: WebSocket):
    """
    WebSocket for live progress streaming.
    Client flow:
      1) Upload the image first using POST /generate (or copy to ./input)
      2) Connect here, then send a JSON message like: {"gender":"male"}
    """
    await websocket.accept()
    try:
        # Wait for the client to send a small JSON telling us the gender
        init = await websocket.receive_json()
        gender = init.get("gender")
        if gender not in ("male", "female"):
            await websocket.send_json({"status": "error", "message": "gender must be 'male' or 'female'"})
            await websocket.close(code=1003)
            return

        # Kick off the pipeline, passing the websocket so your code streams progress
        await main_function(gender, websocket=websocket)
        await websocket.send_json({"status": "done", "message": "✅ Avatar generation completed."})
        await websocket.close(code=1000)

    except WebSocketDisconnect:
        # Client went away — nothing to do (your pipeline may continue)
        return
    except Exception as e:
        # Send the error to client, then close
        try:
            await websocket.send_json({"status": "error", "message": str(e)})
        finally:
            await websocket.close(code=1011)
