from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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


def _upload_file_to_s3_with_client(
    s3_client,
    local_file_path: str,
    bucket_name: str,
    s3_key: str,
    *,
    multipart_threshold_bytes: int | None = None,
    max_concurrency: int | None = None,
) -> None:
    try:
        if multipart_threshold_bytes is not None or (max_concurrency is not None and max_concurrency > 1):
            s3_client.upload_file(local_file_path, bucket_name, s3_key)
        else:
            s3_client.upload_file(local_file_path, bucket_name, s3_key)
    except TypeError as exc:
        if hasattr(s3_client, "upload_file"):
            s3_client.upload_file(local_file_path, bucket_name, s3_key)
            return
        raise exc


def upload_directory_to_s3(
    local_directory_path: str,
    bucket_name: str,
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
    destination_prefix: str | None = None,
    replace_existing: bool = True,
    max_concurrency: int = 1,
    skip_existing: bool = False,
    multipart_threshold_bytes: int | None = None,
) -> dict:
    local_directory = Path(local_directory_path)
    if not local_directory.exists():
        raise FileNotFoundError(f"Local directory not found: {local_directory_path}")
    if not local_directory.is_dir():
        raise NotADirectoryError(f"Local path is not a directory: {local_directory_path}")

    normalized_prefix = (destination_prefix or local_directory.name).strip("/")
    if max_concurrency < 1:
        raise ValueError("max_concurrency must be at least 1")

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

    upload_specs: list[tuple[str, str]] = []
    for file_path in sorted(path for path in local_directory.rglob("*") if path.is_file()):
        relative_path = file_path.relative_to(local_directory).as_posix()
        s3_key = (
            posixpath.join(normalized_prefix, relative_path)
            if normalized_prefix
            else relative_path
        )
        upload_specs.append((str(file_path), s3_key))

    uploaded_files: list[str] = []
    if skip_existing:
        if max_concurrency > 1:
            with ThreadPoolExecutor(max_workers=min(max_concurrency, len(upload_specs))) as executor:
                futures = []
                for local_file_path, s3_key in upload_specs:
                    def upload_if_missing(local_file_path: str, s3_key: str) -> str | None:
                        try:
                            s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                        except Exception:
                            _upload_file_to_s3_with_client(
                                s3_client,
                                local_file_path,
                                bucket_name,
                                s3_key,
                                multipart_threshold_bytes=multipart_threshold_bytes,
                                max_concurrency=max_concurrency,
                            )
                            return s3_key
                        return None

                    futures.append(executor.submit(upload_if_missing, local_file_path, s3_key))

                for future in futures:
                    uploaded_key = future.result()
                    if uploaded_key is not None:
                        uploaded_files.append(uploaded_key)
        else:
            for local_file_path, s3_key in upload_specs:
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=s3_key)
                except Exception:
                    _upload_file_to_s3_with_client(
                        s3_client,
                        local_file_path,
                        bucket_name,
                        s3_key,
                        multipart_threshold_bytes=multipart_threshold_bytes,
                        max_concurrency=max_concurrency,
                    )
                    uploaded_files.append(s3_key)
    elif max_concurrency > 1:
        with ThreadPoolExecutor(max_workers=min(max_concurrency, len(upload_specs))) as executor:
            futures = [
                executor.submit(
                    _upload_file_to_s3_with_client,
                    s3_client,
                    local_file_path,
                    bucket_name,
                    s3_key,
                    multipart_threshold_bytes=multipart_threshold_bytes,
                    max_concurrency=max_concurrency,
                )
                for local_file_path, s3_key in upload_specs
            ]
            for future in futures:
                future.result()
        uploaded_files = [s3_key for _, s3_key in upload_specs]
    else:
        for local_file_path, s3_key in upload_specs:
            _upload_file_to_s3_with_client(
                s3_client,
                local_file_path,
                bucket_name,
                s3_key,
                multipart_threshold_bytes=multipart_threshold_bytes,
                max_concurrency=max_concurrency,
            )
        uploaded_files = [s3_key for _, s3_key in upload_specs]

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


def upload_file_to_s3(
    local_file_path: str,
    bucket_name: str,
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
    destination_key: str,
    multipart_threshold_bytes: int | None = None,
    max_concurrency: int | None = None,
) -> dict:
    local_file = Path(local_file_path)
    if not local_file.exists():
        raise FileNotFoundError(f"Local file not found: {local_file_path}")
    if not local_file.is_file():
        raise IsADirectoryError(f"Local path is not a file: {local_file_path}")

    normalized_key = destination_key.strip("/")
    if not normalized_key:
        raise ValueError("destination_key must not be empty")

    s3_client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )
    _upload_file_to_s3_with_client(
        s3_client,
        str(local_file),
        bucket_name,
        normalized_key,
        multipart_threshold_bytes=multipart_threshold_bytes,
        max_concurrency=max_concurrency,
    )

    return {
        "success": True,
        "local_file_path": str(local_file),
        "bucket_name": bucket_name,
        "destination_key": normalized_key,
        "s3_uri": f"s3://{bucket_name}/{normalized_key}",
    }
