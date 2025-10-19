#!/usr/bin/env python3
import os
import sys
import uuid
import time
import argparse
import mimetypes
from pathlib import Path

from supabase import create_client, Client  # supabase-py v2
from storage3.exceptions import StorageApiError

def build_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY/ANON_KEY in env")
    return create_client(url, key)

def guess_content_type(fname: str) -> str:
    ct, _ = mimetypes.guess_type(fname)
    # GLB special case
    if fname.lower().endswith(".glb"):
        return "model/gltf-binary"
    return ct or "application/octet-stream"

def make_unique_key(prefix: str, filename: str) -> str:
    """
    Always create a unique object key so we never overwrite.
    """
    prefix = (prefix or "").strip("/")
    stem, ext = os.path.splitext(os.path.basename(filename))
    unique = f"{stem}_{int(time.time())}-{uuid.uuid4().hex[:8]}{ext}"
    return f"{prefix}/{unique}" if prefix else unique

def upload_dir(
    client: Client,
    local_dir: str,
    bucket: str,
    prefix: str = "",
    make_public: bool = False,
    sign_expires: int = 3600,  # seconds, if you want signed URLs instead of public
    job_id: str | None = None,
    gender: str | None = None,
):
    """
    Upload all files in local_dir to 'bucket/prefix/<unique>' without overwriting.
    Insert a metadata row per file into public.glb_files.
    """
    storage = client.storage.from_(bucket)
    local_dir = Path(local_dir)
    if not local_dir.is_dir():
        raise FileNotFoundError(f"Local dir not found: {local_dir}")

    results = []

    for fp in sorted(local_dir.glob("**/*")):
        if not fp.is_file():
            continue

        key = make_unique_key(prefix, fp.name)
        data = fp.read_bytes()
        size_bytes = fp.stat().st_size
        content_type = guess_content_type(fp.name)

        # 1) Upload (unique key avoids 409)
        try:
            storage.upload(
                key,
                data,
                {"content-type": content_type},
            )
        except StorageApiError as e:
            # If you still somehow collide (extremely unlikely), re-roll once
            if getattr(e, "code", None) == 409:
                key = make_unique_key(prefix, fp.name)
                storage.upload(key, data, {"content-type": content_type})
            else:
                raise

        # 2) Build URL
        public_url = None
        signed_url = None
        try:
            if make_public:
                public_url = storage.get_public_url(key)
            else:
                # signed URLs require a public bucket setting OFF; they work with either
                try:
                    signed = storage.create_signed_url(key, sign_expires)
                    # supabase-py v2 returns dict with 'signedURL' or 'signed_url' depending on version
                    signed_url = signed.get("signedURL") or signed.get("signed_url")
                except Exception:
                    # fall back to public if signed fails and bucket is public
                    try:
                        public_url = storage.get_public_url(key)
                    except Exception:
                        pass
        except Exception:
            pass

        # 3) Insert metadata row
        row = {
            "job_id": job_id,
            "gender": gender,
            "filename": fp.name,
            "storage_bucket": bucket,
            "storage_key": key,
            "content_type": content_type,
            "size_bytes": size_bytes,
            "public_url": public_url,
            "signed_url": signed_url,
        }
        # Use service role for guaranteed insert; with anon, ensure RLS policy allows insert
        ins = client.table("avatars").insert(row).execute()
        inserted = ins.data[0] if ins.data else row

        results.append(
            {
                "file": str(fp),
                "bucket": bucket,
                "key": key,
                "public_url": public_url,
                "signed_url": signed_url,
                "db_row": inserted,
            }
        )

    return results

def main():
    ap = argparse.ArgumentParser(description="Upload directory to Supabase Storage and log in table.")
    ap.add_argument("--dir", required=True, help="local directory with files to upload")
    ap.add_argument("--bucket", required=True, help="Supabase storage bucket name")
    ap.add_argument("--prefix", default="", help="prefix inside the bucket (e.g., blender/outputs)")
    ap.add_argument("--public", action="store_true", help="make uploaded files public (get_public_url)")
    ap.add_argument("--sign-expires", type=int, default=3600, help="seconds for signed URL expiry")
    ap.add_argument("--gender", choices=["male","female"],required=True)
    ap.add_argument("--job-id", help="optional job id to group records")
    args = ap.parse_args()

    client = build_client()
    results = upload_dir(
        client,
        args.dir,
        args.bucket,
        prefix=args.prefix,
        make_public=args.public,
        sign_expires=args.sign_expires,
        job_id=args.job_id,
        gender=args.gender,
    )

    # Print a compact summary
    for r in results:
        url = r["public_url"] or r["signed_url"] or "(no URL)"
        print(f"[OK] {r['file']} -> {r['bucket']}/{r['key']}  url={url}")

if __name__ == "__main__":
    main()
