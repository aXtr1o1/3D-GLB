
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
import shutil
from full_code import main_function

app = FastAPI()

UPLOAD_DIR = "input"

def process_image(image_path: str, gender: str) -> str:
    processed_path = os.path.join(UPLOAD_DIR, f"processed_{gender}.png")
    shutil.copy(image_path, processed_path)
    return processed_path

@app.post("/upload")
async def upload_image(
    file: UploadFile = File(...), 
    gender: str = Form(...)
):
    filename = file.filename or "default.png"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    await main_function(gender=gender)

    return JSONResponse({
        "status": "success",
        "gender": gender,
        "saved_path": file_path,

    })


