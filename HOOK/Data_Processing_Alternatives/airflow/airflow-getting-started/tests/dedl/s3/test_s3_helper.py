from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAGS_PATH = PROJECT_ROOT / "dags"
if str(DAGS_PATH) not in sys.path:
    sys.path.insert(0, str(DAGS_PATH))

from dedl.s3.s3_helper import upload_directory_to_s3, upload_file_to_s3  # noqa: E402


class _DummyS3Client:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []
        self.deleted_payloads: list[dict] = []
        self.paginator_prefixes: list[str] = []

    def upload_file(self, filename: str, bucket: str, key: str) -> None:
        self.calls.append((filename, bucket, key))

    def get_paginator(self, name: str):
        assert name == "list_objects_v2"

        class _Paginator:
            def __init__(self, outer: _DummyS3Client) -> None:
                self._outer = outer

            def paginate(self, Bucket: str, Prefix: str):
                self._outer.paginator_prefixes.append(Prefix)
                yield {
                    "Contents": [
                        {"Key": f"{Prefix}stale.json"},
                        {"Key": f"{Prefix}old/chunk-1"},
                    ]
                }

        return _Paginator(self)

    def delete_objects(self, Bucket: str, Delete: dict) -> None:
        self.deleted_payloads.append({"Bucket": Bucket, "Delete": Delete})


def test_upload_directory_to_s3_uploads_nested_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_dir = tmp_path / "concatenated.zarr"
    nested_dir = source_dir / "ch9"
    nested_dir.mkdir(parents=True)
    (source_dir / "zarr.json").write_text("root-metadata", encoding="utf-8")
    (nested_dir / "0.0.0").write_text("chunk-data", encoding="utf-8")

    dummy_client = _DummyS3Client()

    def fake_boto3_client(service_name: str, **kwargs):
        assert service_name == "s3"
        assert kwargs["endpoint_url"] == "https://example.invalid"
        assert kwargs["aws_access_key_id"] == "access"
        assert kwargs["aws_secret_access_key"] == "secret"
        return dummy_client

    monkeypatch.setattr("dedl.s3.s3_helper.boto3.client", fake_boto3_client)

    result = upload_directory_to_s3(
        local_directory_path=str(source_dir),
        bucket_name="my-bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
    )

    assert result["success"] is True
    assert result["bucket_name"] == "my-bucket"
    assert result["destination_prefix"] == "concatenated.zarr"
    assert result["s3_uri"] == "s3://my-bucket/concatenated.zarr"
    assert result["replaced_existing"] is True
    assert result["deleted_object_count"] == 2
    assert result["uploaded_file_count"] == 2
    assert result["uploaded_keys"] == ["concatenated.zarr/ch9/0.0.0", "concatenated.zarr/zarr.json"]
    assert dummy_client.paginator_prefixes == ["concatenated.zarr/"]
    assert dummy_client.deleted_payloads == [
        {
            "Bucket": "my-bucket",
            "Delete": {
                "Objects": [
                    {"Key": "concatenated.zarr/stale.json"},
                    {"Key": "concatenated.zarr/old/chunk-1"},
                ]
            },
        }
    ]
    assert dummy_client.calls == [
        (str(nested_dir / "0.0.0"), "my-bucket", "concatenated.zarr/ch9/0.0.0"),
        (str(source_dir / "zarr.json"), "my-bucket", "concatenated.zarr/zarr.json"),
    ]


def test_upload_directory_to_s3_can_preserve_existing_prefix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_dir = tmp_path / "concatenated.zarr"
    source_dir.mkdir()
    (source_dir / "zarr.json").write_text("root-metadata", encoding="utf-8")

    dummy_client = _DummyS3Client()

    def fake_boto3_client(service_name: str, **kwargs):
        return dummy_client

    monkeypatch.setattr("dedl.s3.s3_helper.boto3.client", fake_boto3_client)

    result = upload_directory_to_s3(
        local_directory_path=str(source_dir),
        bucket_name="my-bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
        replace_existing=False,
    )

    assert result["replaced_existing"] is False
    assert result["deleted_object_count"] == 0
    assert dummy_client.paginator_prefixes == []
    assert dummy_client.deleted_payloads == []


def test_upload_directory_to_s3_missing_directory() -> None:
    with pytest.raises(FileNotFoundError, match="Local directory not found"):
        upload_directory_to_s3(
            local_directory_path="/does/not/exist",
            bucket_name="my-bucket",
            endpoint_url="https://example.invalid",
            access_key_id="access",
            secret_access_key="secret",
        )


def test_upload_directory_to_s3_rejects_non_directory(tmp_path: Path) -> None:
    file_path = tmp_path / "not-a-dir.txt"
    file_path.write_text("content", encoding="utf-8")

    with pytest.raises(NotADirectoryError, match="Local path is not a directory"):
        upload_directory_to_s3(
            local_directory_path=str(file_path),
            bucket_name="my-bucket",
            endpoint_url="https://example.invalid",
            access_key_id="access",
            secret_access_key="secret",
        )


def test_upload_file_to_s3_uploads_single_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "movie.mp4"
    file_path.write_text("video-bits", encoding="utf-8")

    dummy_client = _DummyS3Client()

    def fake_boto3_client(service_name: str, **kwargs):
        assert service_name == "s3"
        return dummy_client

    monkeypatch.setattr("dedl.s3.s3_helper.boto3.client", fake_boto3_client)

    result = upload_file_to_s3(
        local_file_path=str(file_path),
        bucket_name="my-bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
        destination_key="visualization/ch9/ch9_timelapse.mp4",
    )

    assert result == {
        "success": True,
        "local_file_path": str(file_path),
        "bucket_name": "my-bucket",
        "destination_key": "visualization/ch9/ch9_timelapse.mp4",
        "s3_uri": "s3://my-bucket/visualization/ch9/ch9_timelapse.mp4",
    }
    assert dummy_client.calls == [
        (
            str(file_path),
            "my-bucket",
            "visualization/ch9/ch9_timelapse.mp4",
        )
    ]


def test_upload_file_to_s3_missing_file() -> None:
    with pytest.raises(FileNotFoundError, match="Local file not found"):
        upload_file_to_s3(
            local_file_path="/does/not/exist.mp4",
            bucket_name="my-bucket",
            endpoint_url="https://example.invalid",
            access_key_id="access",
            secret_access_key="secret",
            destination_key="visualization/ch9/ch9_timelapse.mp4",
        )


def test_upload_file_to_s3_rejects_directory(tmp_path: Path) -> None:
    with pytest.raises(IsADirectoryError, match="Local path is not a file"):
        upload_file_to_s3(
            local_file_path=str(tmp_path),
            bucket_name="my-bucket",
            endpoint_url="https://example.invalid",
            access_key_id="access",
            secret_access_key="secret",
            destination_key="visualization/ch9/ch9_timelapse.mp4",
        )


def test_upload_file_to_s3_rejects_empty_destination_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "movie.mp4"
    file_path.write_text("video-bits", encoding="utf-8")

    dummy_client = _DummyS3Client()

    def fake_boto3_client(service_name: str, **kwargs):
        return dummy_client

    monkeypatch.setattr("dedl.s3.s3_helper.boto3.client", fake_boto3_client)

    with pytest.raises(ValueError, match="destination_key must not be empty"):
        upload_file_to_s3(
            local_file_path=str(file_path),
            bucket_name="my-bucket",
            endpoint_url="https://example.invalid",
            access_key_id="access",
            secret_access_key="secret",
            destination_key="/",
        )