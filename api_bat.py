from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
import asyncio
import re
import time
import uuid
import subprocess

app = FastAPI()

# Locate the project root as the folder containing the .bat
# Adjust only if your bat is elsewhere
PROJECT_ROOT = r"C:\Users\sanje_3wfdh8z\OneDrive\Desktop\3d_final\3D-GLB"
BATCH_FILE   = os.path.join(PROJECT_ROOT, "run_pipeline.bat")
UPLOAD_DIR   = os.path.join(PROJECT_ROOT, "input")

os.makedirs(UPLOAD_DIR, exist_ok=True)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")

def safe_filename(name: str) -> str:
    base = os.path.basename(name or "")
    if not base:
        base = "upload"
    base = _SAFE_NAME.sub("_", base)
    return base[:120]  # keep it short

@app.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    gender: str = Form(...),
):
    gender_norm = (gender or "").strip().lower()
    if gender_norm.startswith("-"):
        gender_norm = gender_norm[1:]
    if gender_norm not in {"male", "female"}:
        raise HTTPException(status_code=400, detail="gender must be 'male' or 'female'")

    if not os.path.isfile(BATCH_FILE):
        raise HTTPException(status_code=500, detail="Batch file not found at expected path.")

    # Build a unique filename (avoid collisions and path traversal)
    stem = os.path.splitext(safe_filename(file.filename or "upload.png"))[0]
    unique = f"{stem}_{int(time.time())}_{uuid.uuid4().hex[:8]}.png"
    saved_path = os.path.join(UPLOAD_DIR, unique)

    try:
        with open(saved_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {e}")

    # Run the pipeline. The BAT expects: run_pipeline.bat <male|female>
    cmd = ["cmd", "/c", BATCH_FILE, gender_norm]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=PROJECT_ROOT,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
        )
        # 30 min timeout; tune if needed
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=1800)
        exit_code = proc.returncode
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        raise HTTPException(status_code=504, detail="Avatar pipeline timed out.")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Failed to start pipeline: cmd or BAT not found.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start pipeline: {e}")

    out_text = (stdout or b"").decode(errors="replace")
    err_text = (stderr or b"").decode(errors="replace")

    MAX_LOG = 6000  # a bit more room
    out_tail = out_text[-MAX_LOG:] if len(out_text) > MAX_LOG else out_text
    err_tail = err_text[-MAX_LOG:] if len(err_text) > MAX_LOG else err_text

    if exit_code != 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Avatar pipeline failed",
                "exit_code": exit_code,
                "stdout_tail": out_tail,
                "stderr_tail": err_tail,
            },
        )

    return JSONResponse({
        "status": "success",
        "gender": gender_norm,
        "saved_path": saved_path,
        "exit_code": exit_code,
        "stdout_tail": out_tail,
        "stderr_tail": err_tail,
    })