# supabase_upload.py
import os
import argparse
from pathlib import Path
from mimetypes import guess_type

from supabase import create_client, Client

def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set (e.g., in .env).")
    return create_client(url, key)

def ensure_bucket(client: Client, bucket: str, public: bool = True):
    # idempotent: if exists, ignore error
    try:
        client.storage.create_bucket(bucket, public=public)
    except Exception:
        pass  # bucket likely exists

def upload_dir(
    client: Client,
    local_dir: Path,
    bucket: str,
    prefix: str = "",
    make_public: bool = True,
) -> list[dict]:
    """
    Upload all files under local_dir to supabase storage at {bucket}/{prefix}/<filename>.
    Returns list of dicts: {"file": str, "key": str, "public_url" or "signed_url"}.
    """
    results = []
    storage = client.storage
    bucket_api = storage.from_(bucket)

    # normalized prefix (no leading slash; trailing slash if non-empty)
    prefix = prefix.strip().lstrip("/").rstrip("/")
    if prefix:
        prefix = prefix + "/"

    for p in sorted(local_dir.glob("*")):
        if not p.is_file():
            continue
        data = p.read_bytes()
        # try to infer proper content-type
        content_type, _ = guess_type(p.name)
        # sensible default for .glb
        if p.suffix.lower() == ".glb":
            content_type = content_type or "model/gltf-binary"
        elif p.suffix.lower() in {".jpg", ".jpeg"}:
            content_type = content_type or "image/jpeg"
        elif p.suffix.lower() == ".png":
            content_type = content_type or "image/png"

        key = f"{prefix}{p.name}" if prefix else p.name
        # upsert=True to overwrite if it already exists
        bucket_api.upload(key, data, {"content-type": content_type or "application/octet-stream"})

        url_info = {"file": str(p), "key": key}
        if make_public:
            url_info["public_url"] = bucket_api.get_public_url(key)
        else:
            # 7-day signed URL as example (in seconds)
            url_info["signed_url"] = bucket_api.create_signed_url(key, 7 * 24 * 3600)
        results.append(url_info)

    return results

def main():
    ap = argparse.ArgumentParser(description="Upload a directory to Supabase Storage")
    ap.add_argument("--dir", required=True, help="Local directory to upload (e.g., Blender/output)")
    ap.add_argument("--bucket", default=os.environ.get("SUPABASE_BUCKET", "three-d-outputs"))
    ap.add_argument("--prefix", default=os.environ.get("SUPABASE_PREFIX", ""))
    ap.add_argument("--public", action="store_true", help="Make files public & return public URLs")
    args = ap.parse_args()

    local = Path(args.dir).resolve()
    if not local.exists() or not local.is_dir():
        raise FileNotFoundError(f"Upload dir not found: {local}")

    client = get_client()
    ensure_bucket(client, args.bucket, public=args.public)

    results = upload_dir(client, local, args.bucket, args.prefix, make_public=args.public)

    print("\n=== Supabase upload results ===")
    for r in results:
        if "public_url" in r:
            print(f"{r['file']} -> {r['public_url']}")
        else:
            print(f"{r['file']} -> signed_url: {r['signed_url']}")
    print("=== Done ===")

if __name__ == "__main__":
    main()
