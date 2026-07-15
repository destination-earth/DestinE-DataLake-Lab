from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DAGS_PATH = PROJECT_ROOT / "dags"
if str(DAGS_PATH) not in sys.path:
    sys.path.insert(0, str(DAGS_PATH))

from dedl.demo2.s3.s3_helper import clear_s3_prefix, upload_directory_to_s3, upload_file_to_s3  # noqa: E402


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

    monkeypatch.setattr("dedl.demo2.s3.s3_helper.boto3.client", fake_boto3_client)

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

    monkeypatch.setattr("dedl.demo2.s3.s3_helper.boto3.client", fake_boto3_client)

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


def test_upload_directory_to_s3_uploads_concurrently_when_requested(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_dir = tmp_path / "concatenated.zarr"
    source_dir.mkdir()
    (source_dir / "first.bin").write_text("one", encoding="utf-8")
    (source_dir / "second.bin").write_text("two", encoding="utf-8")

    active_uploads = 0
    max_active_uploads = 0
    lock = __import__("threading").Lock()

    class _ConcurrentDummyS3Client:
        def upload_file(self, filename: str, bucket: str, key: str, **kwargs) -> None:
            nonlocal active_uploads, max_active_uploads
            with lock:
                active_uploads += 1
                max_active_uploads = max(max_active_uploads, active_uploads)
            __import__("time").sleep(0.05)
            with lock:
                active_uploads -= 1

        def get_paginator(self, name: str):
            assert name == "list_objects_v2"

            class _Paginator:
                def paginate(self, Bucket: str, Prefix: str):
                    yield {"Contents": []}

            return _Paginator()

        def delete_objects(self, Bucket: str, Delete: dict) -> None:
            return None

    dummy_client = _ConcurrentDummyS3Client()

    monkeypatch.setattr("dedl.demo2.s3.s3_helper.boto3.client", lambda *args, **kwargs: dummy_client)

    result = upload_directory_to_s3(
        local_directory_path=str(source_dir),
        bucket_name="my-bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
        max_concurrency=2,
    )

    assert result["uploaded_file_count"] == 2
    assert max_active_uploads >= 2


def test_upload_directory_to_s3_skips_existing_files_when_requested(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source_dir = tmp_path / "concatenated.zarr"
    source_dir.mkdir()
    (source_dir / "existing.bin").write_text("keep-me", encoding="utf-8")
    (source_dir / "new.bin").write_text("new-data", encoding="utf-8")

    class _SkipExistingDummyS3Client:
        def __init__(self) -> None:
            self.uploaded_keys: list[str] = []
            self.head_calls: list[str] = []

        def upload_file(self, filename: str, bucket: str, key: str, **kwargs) -> None:
            self.uploaded_keys.append(key)

        def head_object(self, Bucket: str, Key: str) -> dict:
            self.head_calls.append(Key)
            if Key.endswith("existing.bin"):
                return {"Key": Key}
            raise Exception("missing")

        def get_paginator(self, name: str):
            assert name == "list_objects_v2"

            class _Paginator:
                def paginate(self, Bucket: str, Prefix: str):
                    yield {"Contents": []}

            return _Paginator()

        def delete_objects(self, Bucket: str, Delete: dict) -> None:
            return None

    dummy_client = _SkipExistingDummyS3Client()
    monkeypatch.setattr("dedl.demo2.s3.s3_helper.boto3.client", lambda *args, **kwargs: dummy_client)

    result = upload_directory_to_s3(
        local_directory_path=str(source_dir),
        bucket_name="my-bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
        replace_existing=False,
        skip_existing=True,
    )

    assert result["uploaded_file_count"] == 1
    assert dummy_client.uploaded_keys == ["concatenated.zarr/new.bin"]
    assert dummy_client.head_calls == ["concatenated.zarr/existing.bin", "concatenated.zarr/new.bin"]


def test_upload_file_to_s3_accepts_transfer_options_without_crashing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "movie.mp4"
    file_path.write_text("video-bits", encoding="utf-8")

    class _MultipartDummyS3Client:
        def __init__(self) -> None:
            self.upload_kwargs: list[dict] = []

        def upload_file(self, filename: str, bucket: str, key: str, **kwargs) -> None:
            self.upload_kwargs.append({"filename": filename, "bucket": bucket, "key": key, **kwargs})

    dummy_client = _MultipartDummyS3Client()
    monkeypatch.setattr("dedl.demo2.s3.s3_helper.boto3.client", lambda *args, **kwargs: dummy_client)

    result = upload_file_to_s3(
        local_file_path=str(file_path),
        bucket_name="my-bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
        destination_key="visualization/ch9/ch9_timelapse.mp4",
        multipart_threshold_bytes=16 * 1024 * 1024,
        max_concurrency=2,
    )

    assert result["success"] is True
    assert dummy_client.upload_kwargs[0]["filename"] == str(file_path)
    assert dummy_client.upload_kwargs[0]["bucket"] == "my-bucket"
    assert dummy_client.upload_kwargs[0]["key"] == "visualization/ch9/ch9_timelapse.mp4"
    assert dummy_client.upload_kwargs[0] == {
        "filename": str(file_path),
        "bucket": "my-bucket",
        "key": "visualization/ch9/ch9_timelapse.mp4",
    }


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


def test_clear_s3_prefix_deletes_existing_objects_and_returns_count(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_client = _DummyS3Client()

    def fake_boto3_client(service_name: str, **kwargs):
        assert service_name == "s3"
        assert kwargs["endpoint_url"] == "https://example.invalid"
        assert kwargs["aws_access_key_id"] == "access"
        assert kwargs["aws_secret_access_key"] == "secret"
        return dummy_client

    monkeypatch.setattr("dedl.demo2.s3.s3_helper.boto3.client", fake_boto3_client)

    deleted_count = clear_s3_prefix(
        bucket_name="my-bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
        prefix="my_ch9_zarr_data",
    )

    assert deleted_count == 2
    assert dummy_client.paginator_prefixes == ["my_ch9_zarr_data/"]
    assert dummy_client.deleted_payloads == [
        {
            "Bucket": "my-bucket",
            "Delete": {
                "Objects": [
                    {"Key": "my_ch9_zarr_data/stale.json"},
                    {"Key": "my_ch9_zarr_data/old/chunk-1"},
                ]
            },
        }
    ]


def test_clear_s3_prefix_strips_leading_and_trailing_slashes(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_client = _DummyS3Client()
    monkeypatch.setattr("dedl.demo2.s3.s3_helper.boto3.client", lambda *args, **kwargs: dummy_client)

    clear_s3_prefix(
        bucket_name="my-bucket",
        endpoint_url="https://example.invalid",
        access_key_id="access",
        secret_access_key="secret",
        prefix="/my_ch9_zarr_data/",
    )

    assert dummy_client.paginator_prefixes == ["my_ch9_zarr_data/"]


def test_upload_file_to_s3_uploads_single_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    file_path = tmp_path / "movie.mp4"
    file_path.write_text("video-bits", encoding="utf-8")

    dummy_client = _DummyS3Client()

    def fake_boto3_client(service_name: str, **kwargs):
        assert service_name == "s3"
        return dummy_client

    monkeypatch.setattr("dedl.demo2.s3.s3_helper.boto3.client", fake_boto3_client)

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

    monkeypatch.setattr("dedl.demo2.s3.s3_helper.boto3.client", fake_boto3_client)

    with pytest.raises(ValueError, match="destination_key must not be empty"):
        upload_file_to_s3(
            local_file_path=str(file_path),
            bucket_name="my-bucket",
            endpoint_url="https://example.invalid",
            access_key_id="access",
            secret_access_key="secret",
            destination_key="/",
        )