import subprocess
import sys
import shutil
import os
import glob

def move_resources(src_dir, dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    for filename in os.listdir(src_dir):
        src_path = os.path.join(src_dir, filename)
        dst_path = os.path.join(dst_dir, filename)
        if os.path.isfile(src_path):
            shutil.move(src_path, dst_path)

def move_deca_result(base_dir, obj_destination, png_destination1, png_destination2):
    all_dirs = [os.path.join(base_dir, d) for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not all_dirs:
        print("No folders found in results.")
        return
    dynamic_folder = max(all_dirs, key=os.path.getmtime)
    folder_name = os.path.basename(dynamic_folder)
    obj_file = f"{folder_name}.obj"
    png_file = f"{folder_name}.png"

    src_obj = os.path.join(dynamic_folder, obj_file)
    dst_obj = os.path.join(obj_destination, obj_file)
    if os.path.exists(src_obj):
        if os.path.exists(dst_obj):
            os.remove(dst_obj)
        shutil.copy2(src_obj, dst_obj)
        print(f"Copied {obj_file} to {obj_destination}")
    else:
        print(f"File not found: {obj_file}")

    src_png = os.path.join(dynamic_folder, png_file)
    for png_dest in [png_destination1, png_destination2]:
        dst_png = os.path.join(png_dest, png_file)
        if os.path.exists(src_png):
            if os.path.exists(dst_png):
                os.remove(dst_png)
            shutil.copy2(src_png, dst_png)
            print(f"Copied {png_file} to {png_dest}")
        else:
            print(f"File not found: {png_file}")

    shutil.rmtree(dynamic_folder)
    print(f"Deleted folder: {dynamic_folder}")

# Define interpreters
python_37 = "/usr/bin/python3.7"
python_311 = "/usr/bin/python3.11"

gender = os.getenv("GENDER", "male")

commands = [
    {
        "dir": ".",
        "command": lambda: move_resources("input", "hair_mapper/stylegan-encoder/raw_images")
    },
    {
        "dir": "hair_mapper/stylegan-encoder",
        "command": [python_37, "align_images.py", "raw_images", "aligned_images"]
    },
    {
        "dir": "hair_mapper/stylegan-encoder",
        "command": lambda: [
            os.remove(os.path.join("hair_mapper/stylegan-encoder/raw_images", f))
            for f in os.listdir("hair_mapper/stylegan-encoder/raw_images")
            if os.path.isfile(os.path.join("hair_mapper/stylegan-encoder/raw_images", f))
        ]
    },
    {
        "dir": ".",
        "command": lambda: move_resources("hair_mapper/stylegan-encoder/aligned_images", "hair_mapper/HairMapper/test_data/origin")
    },
    {
        "dir": "hair_mapper/HairMapper/encoder4editing",
        "command": [python_37, "encode.py", "--data_dir", "../test_data"]
    },
    {
        "dir": "hair_mapper/HairMapper",
        "command": [python_37, "main_mapper.py", "--data_dir", "test_data"]
    },
    {
        "dir": ".",
        "command": lambda: move_resources("hair_mapper/HairMapper/test_data/mapper_res", "DECA/TestSamples/examples")
    },
    {
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
        "dir": ".",
        "command": lambda: (
            move_deca_result("DECA/TestSamples/examples/results", "Blender/ready to use model/head", "Texture/input", "Blender/Texture_body/input"),
            [os.remove(f) for f in glob.glob("DECA/TestSamples/examples/*.png")]
        ) and None
    },
    {
        "dir": "Texture",
        "command": [python_311, "texture.py"]
    },
    {
        "dir": "Texture",
        "command": [python_311, "-c", "import os, glob; [os.remove(f) for f in glob.glob('input/*.png')]"]
    },
    {
        "dir": ".",
        "command": lambda: shutil.move("Texture/output/final_texture.jpeg", "Blender/ready to use model/head/final_texture.jpeg")
    },
    {
        "dir": "Blender/Texture_body",
        "command": [python_311, "texture_body.py"]
    },
    {
        "dir": "Texture_body",
        "command": [python_311, "-c", "import os, glob; [os.remove(f) for f in glob.glob('input/*.png')]"]
    },
    {
        "dir": "Blender",
        "command": [python_311, "blender_merging.py", "--g", gender]
    }
]

for step in commands:
    print(f"\n🔄 Running in directory: {step['dir']}")
    if callable(step["command"]):
        try:
            step["command"]()
        except Exception as e:
            print(f"❌ Function failed in step: {step['dir']}, Error: {e}")
            break
    else:
        result = subprocess.run(step["command"], cwd=step["dir"])
        if result.returncode != 0:
            print(f"❌ Command failed: {' '.join(step['command'])}")
            break
