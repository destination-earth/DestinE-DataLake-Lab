import os
import argparse
import boto3
from botocore.client import Config
from dotenv import load_dotenv


# Load .env into environment variables (safe to call even if file doesn't exist)
load_dotenv()


def should_fetch_real_file(key: str) -> bool:
    parts = key.split("/")
    return key.endswith("item_config.json") or "metadata" in parts


def mirror_s3_structure(
    bucket_name: str,
    endpoint_url: str | None = None,
    region_name: str | None = None,
    aws_access_key_id: str | None = None,
    aws_secret_access_key: str | None = None,
    local_root: str = "structure",
):
    """
    Mirror the structure of an S3 bucket locally, downloading only specific files.

    Args:
        bucket_name (str): Name of the S3 bucket.
        endpoint_url (str | None): Custom endpoint URL for the S3 service.
        region_name (str | None): AWS region name.
        aws_access_key_id (str | None): AWS access key ID.
        aws_secret_access_key (str | None): AWS secret access key.
        local_root (str): Local directory to mirror the S3 structure into.
    
    Returns:
        None

    """

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        config=Config(signature_version="s3v4"),
    )

    paginator = s3.get_paginator("list_objects_v2")
    os.makedirs(local_root, exist_ok=True)

    for page in paginator.paginate(Bucket=bucket_name):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            local_path = os.path.join(local_root, key)

            # Directory marker
            if key.endswith("/"):
                os.makedirs(local_path, exist_ok=True)
                continue

            parent_dir = os.path.dirname(local_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)

            if should_fetch_real_file(key):
                if not os.path.exists(local_path):
                    s3.download_file(bucket_name, key, local_path)
            else:
                if not os.path.exists(local_path):
                    open(local_path, "a").close()


def main():

    print("Starting S3 structure mirroring...")

    endpoint_url: str = "https://s3.central.data.destination-earth.eu"
    region: str | None = None
    access_key: str | None = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key: str | None = os.getenv("AWS_SECRET_ACCESS_KEY")
    
    bucket = "usergenerated-proposal-eo.vito.dat.urban-heats-maps"
    output = "EO.VITO.DAT.URBAN_HEAT_MAPS"
    
    #bucket: str = "test-bucket-2"
    #output: str = "test-bucket-2-structure"
    
    # Blocking credential check
    if not access_key or not secret_key:
        raise RuntimeError(
            "AWS credentials not found.\n\n"
            "Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY via:\n"
            "  .env file\n"
            "  or environment variables\n"
        )

    mirror_s3_structure(
        bucket_name=bucket,
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        local_root=output,
    )

    print("Finished S3 structure mirroring.")


if __name__ == "__main__":
    """
    This script mirrors the structure of a specified S3 bucket locally,
    downloading only files that match certain criteria.
    1. item_config.json files
    2. Any files within directories named 'metadata'
    3. Directory markers (empty files for directories)
    Usage:
        python s3_mirror.py
    Ensure AWS credentials are set in environment variables or a .env file.

    Note: this is useful for creating a local representation of the S3 bucket
    without downloading all files, which can be large in size.
    This allows regeneration of metadata without needing full data download.

    """
    main()
