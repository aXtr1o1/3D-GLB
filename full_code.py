import subprocess
from pathlib import Path
import sys
import shutil
import os
import glob
import argparse
from dotenv import load_dotenv

load_dotenv()


def move_resources(src_dir,dst_dir):
    os.makedirs(dst_dir, exist_ok=True)

    for filename in os.listdir(src_dir):
        src_path = os.path.join(src_dir, filename)
        dst_path = os.path.join(dst_dir, filename)

        if os.path.isfile(src_path):
            shutil.move(src_path, dst_path)


def move_deca_result(base_dir, obj_destination, tex_destination):
    # ensure destinations exist
    os.makedirs(obj_destination, exist_ok=True)
    os.makedirs(tex_destination, exist_ok=True)

    all_dirs = [
        os.path.join(base_dir, d) for d in os.listdir(base_dir)
        if os.path.isdir(os.path.join(base_dir, d))
    ]
    if not all_dirs:
        raise FileNotFoundError(f"No result folders in {base_dir}")

    dynamic_folder = max(all_dirs, key=os.path.getmtime)
    folder_name = os.path.basename(dynamic_folder)

    obj_candidates = [
        os.path.join(dynamic_folder, f"{folder_name}.obj"),
        os.path.join(dynamic_folder, "mesh.obj"),
    ]
    tex_candidates = []
    for ext in (".png", ".jpg", ".jpeg"):
        tex_candidates.append(os.path.join(dynamic_folder, f"{folder_name}{ext}"))
        tex_candidates.append(os.path.join(dynamic_folder, f"texture{ext}"))
    # also pick the first image file if names differ
    tex_candidates += sorted(
        [p for p in glob.glob(os.path.join(dynamic_folder, "*.*"))
         if os.path.splitext(p)[1].lower() in [".png", ".jpg", ".jpeg"]],
        key=os.path.getmtime, reverse=True
    )

    # pick first existing obj
    src_obj = next((p for p in obj_candidates if os.path.exists(p)), None)
    if not src_obj:
        raise FileNotFoundError(f"OBJ not found in {dynamic_folder}")

    # pick first existing texture
    src_tex = next((p for p in tex_candidates if os.path.exists(p)), None)
    if not src_tex:
        raise FileNotFoundError(f"Texture image (.png/.jpg) not found in {dynamic_folder}")

    # copy obj
    dst_obj = os.path.join(obj_destination, os.path.basename(src_obj))
    if os.path.exists(dst_obj):
        os.remove(dst_obj)
    shutil.copy2(src_obj, dst_obj)
    print(f"Copied {os.path.basename(dst_obj)} to {obj_destination}")
    dst_tex = os.path.join(tex_destination, os.path.basename(src_tex))
    if os.path.exists(dst_tex):
        os.remove(dst_tex)
    shutil.copy2(src_tex, dst_tex)
    print(f"Copied {os.path.basename(dst_tex)} to {tex_destination}")
    shutil.rmtree(dynamic_folder)
    print(f"Deleted folder: {dynamic_folder}")


# Use system's default Python interpreter
python_executable = sys.executable
import os

python_37 = os.getenv('PYTHON_37_PATH')
python_311 = os.getenv('PYTHON_311_PATH')





async def main_function(gender, websocket=None):
    async def send_progress(step_msg):
        if websocket:
            await websocket.send_json({"status": "progress", "message": step_msg})

    async def run_command(step, step_index):
        print(f"\n🔧 Running Step {step_index + 1}: {step['title']} ({step['dir']})")
        if websocket:await websocket.send_json({"status": "progress","stepIndex": step_index,"title": step["title"]})
        try:
            if callable(step["command"]):
                step["command"]()
            else:
                result = subprocess.run(step["command"], cwd=step["dir"])
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
        {
            "title": "Moving",
            "dir": ".",
            "command": lambda: (
                move_deca_result("DECA/TestSamples/examples/results", "Blender/ready to use model/head", "Texture/input"),
                [os.remove(f) for f in glob.glob("DECA/TestSamples/examples/*.png")]
            ) and None  
        },
        {
            "title": "Applying Textures",
            "dir": "Texture",
            "command": [
                python_311,
                "texture.py",
            ]
        },
        {
            "title": "Cleaning",
            "dir": "Texture",
            "command": [
                python_311,
                "-c",
                "import os, glob; [os.remove(f) for f in glob.glob('input/*.png')]"
            ]
        },

        {
            "title": "Moving",
            "dir": ".",  
            "command": lambda: shutil.move(
                "Texture/output/final_texture.jpeg",
                "Blender/ready to use model/head/final_texture.jpeg"
            )
        },
        {
            "title": "Texture moving",
            "dir": ".",  
            "command": lambda: shutil.move(
                "Texture/output/blend_image.jpg",
                "Blender/Texture_body/input/blend_image.jpg"
            )


        },
        {
            "title": "body Importing",
            "dir": "Blender/Texture_body",
            "command": [
                python_311,
                "texture_body.py",
            ]
        },
       
        {
            "title": "Final Rendering",
            "dir": "Blender",
            "command": [
                python_311,
                "blender_merging.py",
                "--g",
                gender,
            ]
        },
        {
            "title": "Output",
            "dir": "Blender/ready to use model/head",
            "command": lambda: (
                [os.remove(os.path.join("Blender/ready to use model/head", f)) 
                for f in os.listdir("Blender/ready to use model/head") 
                if os.path.isfile(os.path.join("Blender/ready to use model/head", f))]
            )
        },
        {
            "title": "Upload to S3",
            "dir": ".",
            "command": [
                "python_311",
                "s3_push_objs.py",
                "--dir", "Blender/output",
                "--bucket", "3dglbops",
                "--prefix", "blender/outputs",
                "--region", "ap-south-1",
                "--public"
            ]
        },
        {
            "title": "Cleaning Up",
            "dir": ".",
            "command": lambda: (
                [os.remove(f) for f in glob.glob("Blender/output/*.glb")]
            ) and None
        }


    ]

    for index, step in enumerate(commands):
        success = await run_command(step, index)
        if not success:
            break

    await send_progress("✅ Avatar generation completed.")
