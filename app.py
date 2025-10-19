from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os, shutil

from full_code import main_function

APP_ROOT = Path(__file__).parent.resolve()
INPUT_DIR = APP_ROOT / "input"
INPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="3D-GLB Pipeline API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post("/generate")
async def generate(
    gender: str = Form(..., regex="^(male|female)$"),
    image: UploadFile | None = File(None)
):
    try:
        if image is not None:
            dest = INPUT_DIR / image.filename
            with dest.open("wb") as f:
                shutil.copyfileobj(image.file, f)

        result = await main_function(gender)
        # result already contains outputs/public URL
        return JSONResponse(result)

    except FileNotFoundError as e:
        raise HTTPException(status_code=400, detail=f"Pipeline missing resource: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {e}")

@app.websocket("/ws")
async def ws_progress(websocket: WebSocket):
    await websocket.accept()
    try:
        init = await websocket.receive_json()
        gender = init.get("gender")
        if gender not in ("male", "female"):
            await websocket.send_json({"status": "error", "message": "gender must be 'male' or 'female'"})
            await websocket.close(code=1003)
            return

        result = await main_function(gender, websocket=websocket)
        await websocket.send_json({"status": "done", **result})
        await websocket.close(code=1000)

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await websocket.send_json({"status": "error", "message": str(e)})
        finally:
            await websocket.close(code=1011)
