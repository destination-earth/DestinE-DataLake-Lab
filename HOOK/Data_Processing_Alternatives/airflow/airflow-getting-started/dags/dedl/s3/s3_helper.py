from __future__ import annotations

from pathlib import Path
import posixpath

import boto3


def _delete_prefix_contents(s3_client, bucket_name: str, prefix: str) -> int:
    if not prefix:
        return 0

    deleted_count = 0
    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name, Prefix=f"{prefix}/"):
        objects = page.get("Contents", [])
        if not objects:
            continue

        delete_payload = {"Objects": [{"Key": item["Key"]} for item in objects]}
        s3_client.delete_objects(Bucket=bucket_name, Delete=delete_payload)
        deleted_count += len(delete_payload["Objects"])

    return deleted_count


def upload_directory_to_s3(
    local_directory_path: str,
    bucket_name: str,
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
    destination_prefix: str | None = None,
    replace_existing: bool = True,
) -> dict:
    local_directory = Path(local_directory_path)
    if not local_directory.exists():
        raise FileNotFoundError(f"Local directory not found: {local_directory_path}")
    if not local_directory.is_dir():
        raise NotADirectoryError(f"Local path is not a directory: {local_directory_path}")

    normalized_prefix = (destination_prefix or local_directory.name).strip("/")

    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )

    deleted_object_count = 0
    if replace_existing:

        print(f"Replacing existing objects in s3://{bucket_name}/{normalized_prefix}/")

        deleted_object_count = _delete_prefix_contents(
            s3_client=s3_client,
            bucket_name=bucket_name,
            prefix=normalized_prefix,
        )

        print(f"Deleted {deleted_object_count} existing objects in s3://{bucket_name}/{normalized_prefix}/")

    uploaded_files: list[str] = []
    for file_path in sorted(path for path in local_directory.rglob("*") if path.is_file()):
        relative_path = file_path.relative_to(local_directory).as_posix()
        s3_key = (
            posixpath.join(normalized_prefix, relative_path)
            if normalized_prefix
            else relative_path
        )
        s3_client.upload_file(str(file_path), bucket_name, s3_key)
        uploaded_files.append(s3_key)

    result_prefix = normalized_prefix
    return {
        "success": True,
        "local_directory_path": str(local_directory),
        "bucket_name": bucket_name,
        "destination_prefix": result_prefix,
        "s3_uri": f"s3://{bucket_name}/{result_prefix}" if result_prefix else f"s3://{bucket_name}",
        "replaced_existing": replace_existing,
        "deleted_object_count": deleted_object_count,
        "uploaded_file_count": len(uploaded_files),
        "uploaded_keys": uploaded_files,
    }
