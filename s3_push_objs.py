# save as: s3_push_objs.py
#!/usr/bin/env python3
"""
Upload all .obj files from a local folder to S3 and print URLs.

Example:
  python s3_push_objs.py \
    --dir "Blender/ready to use model/head" \
    --bucket your-bucket-name \
    --prefix renders/session-001 \
    --region ap-south-1 \
    --public
"""

import argparse
import json
import mimetypes
import os
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

mimetypes.add_type('text/plain', '.glb')

load_dotenv() 
def get_s3_client(region: Optional[str] = None):
    session = boto3.session.Session(region_name=region)
    return session.client("s3")


def ensure_bucket_exists(s3, bucket: str, region: Optional[str]):
    try:
        s3.head_bucket(Bucket=bucket)
        return
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code not in ("404", "NoSuchBucket", "NotFound"):
            raise

    kwargs = {"Bucket": bucket}
    if region and region != "us-east-1":
        kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region}
    s3.create_bucket(**kwargs)

    # Best effort: default bucket encryption
    try:
        s3.put_bucket_encryption(
            Bucket=bucket,
            ServerSideEncryptionConfiguration={
                "Rules": [{
                    "ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}
                }]
            },
        )
    except ClientError:
        pass


def virtual_hosted_url(bucket: str, key: str, region: Optional[str]) -> str:
    region_to_use = region or boto3.session.Session().region_name or "us-east-1"
    if region_to_use == "us-east-1":
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    return f"https://{bucket}.s3.{region_to_use}.amazonaws.com/{key}"


def upload_objs_in_dir(
    directory: str,
    bucket: str,
    prefix: str = "",
    region: Optional[str] = None,
    make_public: bool = False,
    storage_class: str = "STANDARD",
    presign: bool = False,
    presign_expiry: int = 3600,
) -> List[Dict[str, str]]:
    s3 = get_s3_client(region)
    ensure_bucket_exists(s3, bucket, region)

    base = Path(directory)
    if not base.exists():
        raise FileNotFoundError(f"Directory not found: {base}")

    objs = sorted([p for p in base.iterdir() if p.is_file() and p.suffix.lower() == ".glb"])
    results = []

    for p in objs:
        key = f"{prefix.rstrip('/')}/{p.name}" if prefix else p.name
        extra = {
            "ContentType": mimetypes.guess_type(str(p))[0] or "application/octet-stream",
            "StorageClass": storage_class,
            "ServerSideEncryption": "AES256",
        }
        # if make_public:
        #     extra["ACL"] = "public-read"

        s3.upload_file(str(p), bucket, key, ExtraArgs=extra)

        url = virtual_hosted_url(bucket, key, region)
        item = {"file": str(p), "key": key, "url": url}

        if presign and not make_public:
            item["presigned_url"] = s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=presign_expiry,
            )

        results.append(item)

    return results


def main():
    ap = argparse.ArgumentParser(description="Upload all .obj files from a folder to S3")
    ap.add_argument("--dir", required=True, help="Local folder containing .obj files")
    ap.add_argument("--bucket", default=os.getenv("S3_BUCKET_NAME"), help="Target S3 bucket")
    ap.add_argument("--prefix", default=os.getenv("S3_PREFIX", ""), help="Key prefix/folder in the bucket")
    ap.add_argument("--region", default=os.getenv("AWS_DEFAULT_REGION"), help="AWS region, e.g., ap-south-1")
    ap.add_argument("--public", action="store_true", help="Make uploaded objects public-read")
    ap.add_argument("--presign", action="store_true", help="Also print a 1-hour presigned URL for private objects")
    ap.add_argument("--storage-class", default="STANDARD", help="S3 storage class (STANDARD, STANDARD_IA, etc.)")
    ap.add_argument("--presign-expiry", type=int, default=3600, help="Presigned URL expiry seconds")
    args = ap.parse_args()

    results = upload_objs_in_dir(
        directory=args.dir,
        bucket=args.bucket,
        prefix=args.prefix,
        region=args.region,
        make_public=args.public,
        storage_class=args.storage_class,
        presign=args.presign,
        presign_expiry=args.presign_expiry,
    )

    # Print a compact JSON summary for downstream scripts
    print(json.dumps({"uploaded": results}, ensure_ascii=False, indent=2))

    # Convenience: also print plain URLs (one per line)
    for r in results:
        print(r.get("presigned_url") or r["url"])


if __name__ == "__main__":
    main()
