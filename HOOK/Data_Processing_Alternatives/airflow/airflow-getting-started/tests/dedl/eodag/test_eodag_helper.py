from __future__ import annotations

import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAGS_PATH = PROJECT_ROOT / "dags"
if str(DAGS_PATH) not in sys.path:
    sys.path.insert(0, str(DAGS_PATH))

from dedl.eodag.eodag_helper import (  # noqa: E402
    clean_directory,
    extract_zip_files,
    filename_timestamp_sort_key,
    filter_and_sort_nat_files,
    find_dedl_collection_by_eodag_id,
    find_eodag_collection_id_by_dedl_id,
    get_collection_search_params,
    get_eodag_collection_info,
    shift_iso_date,
)


class _DummyConfig:
    def __init__(self, products: dict):
        self.products = products


class _DummyProvider:
    def __init__(self, products: dict):
        self.config = _DummyConfig(products)


class _DummyDag:
    def __init__(self, products: dict):
        self.providers = {"dedl": _DummyProvider(products)}


class _DummyCollection:
    def __init__(self, collection_id: str, title: str):
        self.id = collection_id
        self.title = title

    def model_dump(self) -> dict:
        return {"id": self.id, "title": self.title}


class _DummyCollectionDag:
    def __init__(self, collections: list[_DummyCollection]):
        self._collections = collections

    def list_collections(self, provider: str = "dedl") -> list[_DummyCollection]:
        return self._collections


def _build_dummy_products() -> dict:
    return {
        "S2_MSI_L2A": {"_collection": "EO.ESA.DAT.SENTINEL-2.MSI.L2A"},
        "S2_MSI_L1C": {"_collection": "EO.ESA.DAT.SENTINEL-2.MSI.L1C"},
        "S3_EFR": {"_collection": "EO.EUM.DAT.SENTINEL-3.OL_1_EFR___"},
    }


def test_find_eodag_collection_id_by_dedl_id_success() -> None:
    dag = _DummyDag(_build_dummy_products())

    result = find_eodag_collection_id_by_dedl_id(
        "EO.ESA.DAT.SENTINEL-2.MSI.L2A",
        dag=dag,
    )

    assert result == "S2_MSI_L2A"


def test_find_eodag_collection_id_by_dedl_id_case_insensitive() -> None:
    dag = _DummyDag(_build_dummy_products())

    result = find_eodag_collection_id_by_dedl_id(
        "eo.esa.dat.sentinel-2.msi.l2a",
        dag=dag,
    )

    assert result == "S2_MSI_L2A"


def test_find_eodag_collection_id_by_dedl_id_unknown() -> None:
    dag = _DummyDag(_build_dummy_products())

    with pytest.raises(ValueError, match="No normalized EODAG collection id found"):
        find_eodag_collection_id_by_dedl_id(
            "EO.ESA.DAT.DOES-NOT-EXIST",
            dag=dag,
        )


def test_find_eodag_collection_id_by_dedl_id_ambiguous() -> None:
    products = _build_dummy_products()
    products["S2_MSI_ALIAS"] = {"_collection": "EO.ESA.DAT.SENTINEL-2.MSI.L2A"}
    dag = _DummyDag(products)

    with pytest.raises(ValueError, match="Ambiguous mapping"):
        find_eodag_collection_id_by_dedl_id(
            "EO.ESA.DAT.SENTINEL-2.MSI.L2A",
            dag=dag,
        )


def test_find_dedl_collection_by_eodag_id() -> None:
    dag = _DummyDag(_build_dummy_products())

    results = find_dedl_collection_by_eodag_id("S2_MSI_L2A", dag=dag)

    assert results == [
        {
            "eodag_collection_id": "S2_MSI_L2A",
            "provider_collection_id": "EO.ESA.DAT.SENTINEL-2.MSI.L2A",
        }
    ]


def test_get_eodag_collection_info_success() -> None:
    dag = _DummyCollectionDag(
        [
            _DummyCollection("S2_MSI_L1C", "Sentinel-2 MSI L1C"),
            _DummyCollection("S2_MSI_L2A", "Sentinel-2 MSI L2A"),
        ]
    )

    result = get_eodag_collection_info("S2_MSI_L2A", dag=dag)

    assert result == {
        "id": "S2_MSI_L2A",
        "title": "Sentinel-2 MSI L2A",
    }


def test_get_eodag_collection_info_unknown() -> None:
    dag = _DummyCollectionDag([_DummyCollection("S2_MSI_L2A", "Sentinel-2 MSI L2A")])

    with pytest.raises(ValueError, match="Collection not found in provider"):
        get_eodag_collection_info("UNKNOWN_COLLECTION", dag=dag)


def test_get_collection_search_params_from_extent() -> None:
    collection_info = {
        "extent": {
            "temporal": {
                "interval": [["2024-07-01T00:00:00Z", "2024-07-31T23:59:59Z"]],
            },
            "spatial": {
                "bbox": [[2.2, 48.8, 2.4, 49.0]],
            },
        }
    }

    params = get_collection_search_params(collection_info)

    assert params["start"] == "2024-07-01"
    assert params["end"] == "2024-07-31"
    assert params["bbox"] == [2.2, 48.8, 2.4, 49.0]
    assert params["geom"] == "POLYGON((2.2 48.8, 2.4 48.8, 2.4 49.0, 2.2 49.0, 2.2 48.8))"


def test_get_collection_search_params_from_temporal_extents_and_root_bbox() -> None:
    collection_info = {
        "temporal_extents": [["2024-08-10", "2024-08-30"]],
        "bbox": [10.0, 45.0, 12.0, 46.0],
    }

    params = get_collection_search_params(collection_info)

    assert params["start"] == "2024-08-10"
    assert params["end"] == date.today().isoformat()
    assert params["bbox"] == [10.0, 45.0, 12.0, 46.0]


def test_get_collection_search_params_missing_start_date() -> None:
    collection_info = {
        "extent": {
            "spatial": {
                "bbox": [[2.2, 48.8, 2.4, 49.0]],
            },
        }
    }

    with pytest.raises(ValueError, match="Collection start date not found"):
        get_collection_search_params(collection_info)


def test_get_collection_search_params_missing_bbox() -> None:
    collection_info = {
        "extent": {
            "temporal": {
                "interval": [["2024-07-01", None]],
            }
        }
    }

    with pytest.raises(ValueError, match="Collection bbox not found"):
        get_collection_search_params(collection_info)


def test_get_collection_search_params_tuple_interval_and_bbox() -> None:
    collection_info = {
        "extent": {
            "temporal": {
                "interval": (("2018-03-26 00:00:00+00:00", None),),
            },
            "spatial": {
                "bbox": ((-180.0, -90.0, 180.0, 90.0),),
            },
        }
    }

    params = get_collection_search_params(collection_info)

    assert params["start"] == "2018-03-26"
    assert params["end"] == date.today().isoformat()
    assert params["bbox"] == [-180.0, -90.0, 180.0, 90.0]


def test_get_collection_search_params_with_end_datetime_fallback() -> None:
    collection_info = {
        "start_datetime": "2021-01-01T00:00:00Z",
        "end_datetime": "2021-01-15T00:00:00Z",
        "bbox": [-5.0, 40.0, 5.0, 50.0],
    }

    params = get_collection_search_params(collection_info)

    assert params["start"] == "2021-01-01"
    assert params["end"] == "2021-01-15"


def test_get_collection_search_params_with_datetime_interval_values() -> None:
    collection_info = {
        "extent": {
            "temporal": {
                "interval": [[datetime(2018, 3, 26, tzinfo=timezone.utc), None]],
            },
            "spatial": {
                "bbox": [[-180.0, -90.0, 180.0, 90.0]],
            },
        }
    }

    params = get_collection_search_params(collection_info)

    assert params["start"] == "2018-03-26"
    assert params["end"] == date.today().isoformat()


def test_get_collection_search_params_with_date_start_datetime() -> None:
    collection_info = {
        "start_datetime": date(2020, 1, 2),
        "bbox": [-5.0, 40.0, 5.0, 50.0],
    }

    params = get_collection_search_params(collection_info)

    assert params["start"] == "2020-01-02"
    assert params["end"] == date.today().isoformat()


def test_shift_iso_date_from_iso_string() -> None:
    assert shift_iso_date("2018-03-26", days=30) == "2018-04-25"


def test_filename_timestamp_sort_key_prefers_timestamp_when_present() -> None:
    key = filename_timestamp_sort_key("MSG4-SEVI-MSG15-0100-NA-20260708091531.nat")

    assert key[0] == 0
    assert key[1] == "20260708091531"


def test_filename_timestamp_sort_key_falls_back_to_filename() -> None:
    key = filename_timestamp_sort_key("product_without_date.nat")

    assert key[0] == 1
    assert key[1] == ""
    assert key[2] == "product_without_date.nat"


def test_filter_and_sort_nat_files_keeps_only_nat_and_orders_by_filename_time() -> None:
    files = [
        "/tmp/MSG4-SEVI-MSG15-0100-NA-20260708093000.nat",
        "/tmp/ignore_me.txt",
        "/tmp/MSG4-SEVI-MSG15-0100-NA-20260708091531.nat",
        "/tmp/no_timestamp_product.nat",
    ]

    result = filter_and_sort_nat_files(files)

    assert [path.name for path in result] == [
        "MSG4-SEVI-MSG15-0100-NA-20260708091531.nat",
        "MSG4-SEVI-MSG15-0100-NA-20260708093000.nat",
        "no_timestamp_product.nat",
    ]


def test_clean_directory_renames_attachment_artifact(tmp_path: Path) -> None:
    bad_file = tmp_path / 'product.zip", attachment'
    bad_file.write_text("data")

    renamed = clean_directory(str(tmp_path))

    assert [p.name for p in renamed] == ["product.zip"]
    assert (tmp_path / "product.zip").exists()
    assert not bad_file.exists()


def test_clean_directory_renames_stray_quotes(tmp_path: Path) -> None:
    bad_file = tmp_path / '"product.zip"'
    bad_file.write_text("data")

    renamed = clean_directory(str(tmp_path))

    assert [p.name for p in renamed] == ["product.zip"]
    assert (tmp_path / "product.zip").exists()


def test_clean_directory_leaves_clean_names_untouched(tmp_path: Path) -> None:
    clean_file = tmp_path / "product.zip"
    clean_file.write_text("data")

    renamed = clean_directory(str(tmp_path))

    assert renamed == []
    assert clean_file.exists()


def test_clean_directory_skips_subdirectories(tmp_path: Path) -> None:
    (tmp_path / 'sub", attachment').mkdir()

    renamed = clean_directory(str(tmp_path))

    assert renamed == []
    assert (tmp_path / 'sub", attachment').exists()


def _build_zip(zip_path: Path, member_name: str, content: str) -> None:
    with zipfile.ZipFile(zip_path, "w") as z:
        z.writestr(member_name, content)


def test_extract_zip_files_extracts_into_stem_folder(tmp_path: Path) -> None:
    zip_path = tmp_path / "product.zip"
    _build_zip(zip_path, "data.txt", "hello")

    extracted_folders = extract_zip_files([zip_path])

    assert extracted_folders == [tmp_path / "product"]
    assert (tmp_path / "product" / "data.txt").read_text() == "hello"


def test_extract_zip_files_ignores_non_zip_paths(tmp_path: Path) -> None:
    txt_path = tmp_path / "notes.txt"
    txt_path.write_text("hello")

    extracted_folders = extract_zip_files([txt_path])

    assert extracted_folders == []


def test_extract_zip_files_overwrite_false_keeps_existing_member(tmp_path: Path) -> None:
    zip_path = tmp_path / "product.zip"
    _build_zip(zip_path, "data.txt", "new content")

    extract_dir = tmp_path / "product"
    extract_dir.mkdir()
    (extract_dir / "data.txt").write_text("original content")

    extract_zip_files([zip_path], overwrite=False)

    assert (extract_dir / "data.txt").read_text() == "original content"
