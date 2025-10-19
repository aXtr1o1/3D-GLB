import subprocess
from pathlib import Path
import sys
import shutil
import os
import glob
import argparse
import logging
from dotenv import load_dotenv

load_dotenv()
LOG_FILE = "pipeline.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("Pipeline")

def move_resources(src_dir,dst_dir):
    os.makedirs(dst_dir, exist_ok=True)
    for filename in os.listdir(src_dir):
        src_path = os.path.join(src_dir, filename)
        dst_path = os.path.join(dst_dir, filename)
        if os.path.isfile(src_path):
            shutil.move(src_path, dst_path)

def move_deca_result(base_dir, obj_destination, tex_destination):
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
    tex_candidates += sorted(
        [p for p in glob.glob(os.path.join(dynamic_folder, "*.*"))
         if os.path.splitext(p)[1].lower() in [".png", ".jpg", ".jpeg"]],
        key=os.path.getmtime, reverse=True
    )

    src_obj = next((p for p in obj_candidates if os.path.exists(p)), None)
    if not src_obj:
        raise FileNotFoundError(f"OBJ not found in {dynamic_folder}")

    src_tex = next((p for p in tex_candidates if os.path.exists(p)), None)
    if not src_tex:
        raise FileNotFoundError(f"Texture image (.png/.jpg) not found in {dynamic_folder}")

    dst_obj = os.path.join(obj_destination, os.path.basename(src_obj))
    if os.path.exists(dst_obj):
        os.remove(dst_obj)
    shutil.copy2(src_obj, dst_obj)
    logger.info(f"Copied {os.path.basename(dst_obj)} to {obj_destination}")

    dst_tex = os.path.join(tex_destination, os.path.basename(src_tex))
    if os.path.exists(dst_tex):
        os.remove(dst_tex)
    shutil.copy2(src_tex, dst_tex)
    logger.info(f"Copied {os.path.basename(dst_tex)} to {tex_destination}")

    shutil.rmtree(dynamic_folder)
    logger.info(f"Deleted folder: {dynamic_folder}")

python_executable = sys.executable
import os
python_37 = os.getenv('PYTHON_37_PATH')
python_311 = os.getenv('PYTHON_311_PATH')

# ---------- helper to fetch latest public URL from Supabase ----------
def fetch_latest_public_url(gender: str):
    """
    Query Supabase 'avatars' table for the latest row for this gender
    and return its public_url (if available) and the full row.
    """
    from supabase import create_client, Client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        logger.warning("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set; cannot fetch public_url.")
        return None, None

    client: Client = create_client(url, key)
    res = client.table("avatars") \
        .select("*") \
        .eq("gender", gender) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    if res.data:
        row = res.data[0]
        return row.get("public_url"), row
    return None, None
# ---------------------------------------------------------------------

async def main_function(gender, websocket=None):

    async def send_progress(step_msg):
        logger.info(step_msg)
        if websocket:
            await websocket.send_json({"status": "progress", "message": step_msg})

    async def run_command(step, step_index):
        title = f"\n🔧 Running Step {step_index + 1}: {step['title']} ({step['dir']})"
        logger.info(title)
        if websocket:
            await websocket.send_json({"status": "progress","stepIndex": step_index,"title": step["title"]})
        try:
            if callable(step["command"]):
                step["command"]()
                return True

            env = os.environ.copy()
            if step["title"] in ("Hair removal",):
                env.update({
                    "CUDA_HOME": "/usr/local/cuda-11.7",
                    "CC": "/usr/bin/gcc-11",
                    "CXX": "/usr/bin/g++-11",
                    "CUDAHOSTCXX": "/usr/bin/g++-11",
                    "TORCH_CUDA_ARCH_LIST": "7.5",
                    "NVCC_FLAGS": "-allow-unsupported-compiler",
                    "CUDAFLAGS": "-allow-unsupported-compiler",
                    "MAX_JOBS": "1",
                })

            result = subprocess.run(
                step["command"],
                cwd=step["dir"],
                text=True,
                capture_output=True,
                env=env
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print(result.stderr, file=sys.stderr)
            if result.returncode != 0:
                await send_progress(f"❌ Failed at step: {' '.join(map(str, step['command']))} (exit {result.returncode})")
                return False
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            await send_progress(f"🔥 Exception at {step['dir']}: {e}")
            return False

    commands = [
        {"title": "Moving Input Image","dir": ".","command": lambda: move_resources("input","hair_mapper/stylegan-encoder/raw_images")},
        {"title": "Analyzing Image","dir": "hair_mapper/stylegan-encoder","command": [python_37,"align_images.py","raw_images","aligned_images"]},
        {"title": "Cleaning image","dir": "hair_mapper/stylegan-encoder","command": lambda: [os.remove(os.path.join("hair_mapper/stylegan-encoder/raw_images", f)) for f in os.listdir("hair_mapper/stylegan-encoder/raw_images") if os.path.isfile(os.path.join("hair_mapper/stylegan-encoder/raw_images", f))]},
        {"title": "Moving","dir": ".","command": lambda: move_resources("hair_mapper/stylegan-encoder/aligned_images","hair_mapper/HairMapper/test_data/origin")},
        {"title": "Encoding image","dir": "hair_mapper/HairMapper/encoder4editing","command": [python_37,"encode.py","--data_dir","../test_data"]},
        {"title": "Hair removal","dir":"hair_mapper/HairMapper","command":[python_37,"main_mapper.py","--data_dir","test_data"]},
        {"title": "Background Removal","dir": ".","command":[python_37,"background_remover.py"]},
        {"title": "Cleaning","dir": ".","command": lambda: [os.remove(os.path.join("hair_mapper/HairMapper/test_data/mapper_res", f)) for f in os.listdir("hair_mapper/HairMapper/test_data/mapper_res") if os.path.isfile(os.path.join("hair_mapper/HairMapper/test_data/mapper_res", f))]},
        {"title": "Removing raw image","dir": "hair_mapper/HairMapper/test_data","command": lambda: [shutil.rmtree(os.path.join("hair_mapper/HairMapper/test_data", folder, item)) if os.path.isdir(os.path.join("hair_mapper/HairMapper/test_data", folder, item)) else os.remove(os.path.join("hair_mapper/HairMapper/test_data", folder, item)) for folder in ["code", "mapper_res", "origin"] for item in os.listdir(os.path.join("hair_mapper/HairMapper/test_data", folder))]},
        {"title": "Building 3D Mesh","dir": "DECA","command": [python_37,"demos/demo_reconstruct.py","-i","TestSamples/examples","--saveDepth","True","--saveObj","True","--useTex","True"]},
        {"title": "Moving","dir": ".","command": lambda: (move_deca_result("DECA/TestSamples/examples/results", "Blender/ready to use model/head", "Texture/input"), [os.remove(f) for f in glob.glob("DECA/TestSamples/examples/*.png")]) and None},
        {"title": "Applying Textures","dir": "Texture","command": [python_311,"texture.py"]},
        {"title": "Cleaning","dir": "Texture","command": [python_311,"-c","import os, glob; [os.remove(f) for f in glob.glob('input/*.png')]"]},
        {"title": "Moving","dir": ".","command": lambda: shutil.move("Texture/output/final_texture.jpeg","Blender/ready to use model/head/final_texture.jpeg")},
        {"title": "Texture moving","dir": ".","command": lambda: shutil.move("Texture/output/blend_image.jpg","Blender/Texture_body/input/blend_image.jpg")},
        {"title": "body Importing","dir": "Blender/Texture_body","command": [python_311,"texture_body.py"]},
        {"title": "Final Rendering","dir": "Blender","command": [python_311,"blender_merging.py","--g",gender]},
        {"title": "Output","dir": "Blender/ready to use model/head","command": lambda: ([os.remove(os.path.join("Blender/ready to use model/head", f)) for f in os.listdir("Blender/ready to use model/head") if os.path.isfile(os.path.join("Blender/ready to use model/head", f))])},
        # IMPORTANT: we pass --gender so the uploader can insert that in DB
        {"title": "Upload to Supabase","dir": ".","command": [python_311,"supabase_upload.py","--dir","Blender/output","--bucket",os.getenv("SUPABASE_BUCKET","three-d-outputs"),"--prefix",os.getenv("SUPABASE_PREFIX","blender/outputs"),"--gender",gender,"--public"]},
        {"title": "Cleaning Up","dir": ".","command": lambda: ([os.remove(f) for f in glob.glob("Blender/output/*.glb")]) and None},
    ]

    all_ok = True
    for index, step in enumerate(commands):
        success = await run_command(step, index)
        if not success:
            all_ok = False
            break

    # Always try to fetch a URL if upload step passed
    public_url, row = fetch_latest_public_url(gender)

    await send_progress("✅ Avatar generation completed.")
    if public_url:
        await send_progress(f"Public GLB URL: {public_url}")

    # Return object that your FastAPI route can send back to the client
    return {
        "status": "completed" if all_ok else "failed",
        "gender": gender,
        "outputs": [public_url] if public_url else [],
        "db_row": row or {}
    }

if __name__ == "__main__":
    import asyncio
    ap = argparse.ArgumentParser(description="3D-GLB end-to-end runner")
    ap.add_argument("--gender", choices=["male", "female"], required=True)
    ap.add_argument("--image", help="absolute path to selfie; will be copied to input/ if provided")
    args = ap.parse_args()

    if args.image:
        os.makedirs("input", exist_ok=True)
        if not os.path.isfile(args.image):
            raise FileNotFoundError(f"Image not found: {args.image}")
        shutil.copy2(args.image, os.path.join("input", os.path.basename(args.image)))
        logger.info(f"Copied input image to ./input")

    result = asyncio.run(main_function(args.gender))
    print(result)
