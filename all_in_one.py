import subprocess
from pathlib import Path
import sys
import shutil
import os
import glob
import argparse


def move_resources(src_dir,dst_dir):
    os.makedirs(dst_dir, exist_ok=True)

    for filename in os.listdir(src_dir):
        src_path = os.path.join(src_dir, filename)
        dst_path = os.path.join(dst_dir, filename)

        if os.path.isfile(src_path):
            shutil.move(src_path, dst_path)


def move_deca_result(base_dir, obj_destination, png_destination1):
    all_dirs = [
        os.path.join(base_dir, d) for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
    ]

    if not all_dirs:
        print("No folders found in results.")
    else:
        dynamic_folder = max(all_dirs, key=os.path.getmtime)
        folder_name = os.path.basename(dynamic_folder)

        obj_file = f"{folder_name}.obj"
        png_file = f"{folder_name}.png"

        # Handle the .obj file
        src_obj = os.path.join(dynamic_folder, obj_file)
        dst_obj = os.path.join(obj_destination, obj_file)
        if os.path.exists(src_obj):
            if os.path.exists(dst_obj):
                os.remove(dst_obj)
            shutil.copy2(src_obj, dst_obj)
            print(f"Copied {obj_file} to {obj_destination}")
        else:
            print(f"File not found: {obj_file}")

        # Handle the .png file (copy only to png_destination1)
        src_png = os.path.join(dynamic_folder, png_file)
        dst_png = os.path.join(png_destination1, png_file)
        if os.path.exists(src_png):
            if os.path.exists(dst_png):
                os.remove(dst_png)
            shutil.copy2(src_png, dst_png)
            print(f"Copied {png_file} to {png_destination1}")
        else:
            print(f"File not found: {png_file}")


        # Delete the dynamic folder
        shutil.rmtree(dynamic_folder)
        print(f"Deleted folder: {dynamic_folder}")


# Use system's default Python interpreter
python_executable = sys.executable
python_37 = r"C:\Users\tamil\AppData\Local\Programs\Python\Python37\python.exe"
python_311 = r"C:\Users\tamil\AppData\Local\Programs\Python\Python311\python.exe"




async def main_function(gender, websocket=None):
    async def send_progress(step_msg):
        if websocket:
            await websocket.send_json({"status": "progress", "message": step_msg})

    async def run_command(step, step_index):
        print(f"\n🔧 Running Step {step_index + 1}: {step['title']} ({step['dir']})")
        if websocket:await websocket.send_json({"status": "progress","stepIndex": step_index,"title": step["title"]})
        
        # await send_progress({"status": "progress","stepIndex": step_index,"title": step["title"]})
        try:
            if callable(step["command"]):
                step["command"]()
            else:
                result = subprocess.run(step["command"], cwd=step["dir"])
                print(result.stdout)
                print(result.stderr)
                if result.returncode != 0:
                    await send_progress(f"❌ Failed at step: {' '.join(step['command'])}")
                    return False
        except Exception as e:
            await send_progress(f"🔥 Exception at {step['dir']}: {str(e)}")
            return False
        return True
        

    commands = [
        {
            "title": "Moving Input Image",
            "dir": ".",  
            "command": lambda: move_resources(
                "input",
                "hair_mapper/stylegan-encoder/raw_images"
            )
        },
        {
            "title": "Analyzing Image",
            "dir": "hair_mapper/stylegan-encoder",
            "command": [
                python_37,
                "align_images.py",
                "raw_images",
                "aligned_images"
            ]
        },
        {
            "title": "Cleaning image",
            "dir": "hair_mapper/stylegan-encoder",
            "command": lambda: [
                os.remove(os.path.join("hair_mapper/stylegan-encoder/raw_images", f))
                for f in os.listdir("hair_mapper/stylegan-encoder/raw_images")
                if os.path.isfile(os.path.join("hair_mapper/stylegan-encoder/raw_images", f))
            ]
        },
        
        {
            "title": "Moving",
            "dir": ".",  
            "command": lambda: move_resources(
                "hair_mapper/stylegan-encoder/aligned_images",
                "hair_mapper/HairMapper/test_data/origin"
            )
        },
        {
            "title": "Encoding image",
            "dir": "hair_mapper/HairMapper/encoder4editing",
            "command": [
                python_37,
                "encode.py",
                "--data_dir",
                "../test_data"
            ]
        },
        {
            "title": "Hair removal",
            "dir":"hair_mapper/HairMapper",
            "command":[
                python_37,
                "main_mapper.py",
                "--data_dir",
                "test_data"
            ]
        },
        {
            "title": "Background Removal",
            "dir": ".",  
            "command":[python_37,
                       "background_remover.py"]
        },
        {
            "title": "Cleaning",
            "dir": ".",
            "command": lambda: [
                os.remove(os.path.join("hair_mapper/HairMapper/test_data/mapper_res", f))
                for f in os.listdir("hair_mapper/HairMapper/test_data/mapper_res")
                if os.path.isfile(os.path.join("hair_mapper/HairMapper/test_data/mapper_res", f))
            ]
        },

        {
            "title": "Removing raw image",
            "dir": "hair_mapper/HairMapper/test_data",
            "command": lambda: [
                shutil.rmtree(os.path.join("hair_mapper/HairMapper/test_data", folder, item))
                if os.path.isdir(os.path.join("hair_mapper/HairMapper/test_data", folder, item))
                else os.remove(os.path.join("hair_mapper/HairMapper/test_data", folder, item))
                for folder in ["code", "mapper_res", "origin"]
                for item in os.listdir(os.path.join("hair_mapper/HairMapper/test_data", folder))
            ]
        },


        {
            "title": "Building 3D Mesh",
            "dir": "DECA",
            "command": [
                python_37,
                "demos/demo_reconstruct.py",
                "-i", "TestSamples/examples",
                "--saveDepth", "True",
                "--saveObj", "True",
                "--useTex", "True"
            ]
        },

    ]

    for index, step in enumerate(commands):
        success = await run_command(step, index)
        if not success:
            break

    await send_progress("✅ Avatar generation completed.")
    
import asyncio
asyncio.run( main_function(gender="male"))
    