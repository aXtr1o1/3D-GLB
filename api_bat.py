from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
import shutil
import subprocess

app = FastAPI()

UPLOAD_DIR = "input"

def run_bat_file(gender: str):
    command = f'cmd /c ""C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" && "C:\\Users\\sanje_3wfdh8z\\OneDrive\\Desktop\\3d_final\\3D-GLB\\run_pipeline.bat" {gender}"'

    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        return {"status": "error", "message": result.stderr}
    return {"status": "success", "output": result.stdout}

@app.post("/upload")
async def upload_image(
    file: UploadFile = File(...), 
    gender: str = Form(...)
):
    filename = file.filename or "default.png"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Save the uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Run the .bat file with the specified gender
    run_result = run_bat_file(gender)
    
    return JSONResponse({
        "status": run_result["status"],
        "gender": gender,
        "saved_path": file_path,
        "output": run_result.get("output", ""),
        "error_message": run_result.get("message", ""),
    })
