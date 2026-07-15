from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import xarray as xr

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAGS_PATH = PROJECT_ROOT / "dags"
if str(DAGS_PATH) not in sys.path:
    sys.path.insert(0, str(DAGS_PATH))

from airflow.sdk.definitions.param import DagParam  # noqa: E402
from dedl.demo2.eodag.eodag_helper import filter_and_sort_nat_files  # noqa: E402
from dedl.demo2 import tutorial_taskflow_api_demo2 as demo2  # noqa: E402


def test_transform_contract_ignores_stale_folder_files() -> None:
    stale_folder_files = [
        "/home/eouser/eodag_downloads/msg_hrseviri/old_20260701091531.nat",
        "/home/eouser/eodag_downloads/msg_hrseviri/old_20260701093000.nat",
    ]

    extract_output = {
        "search_results": 2,
        "downloaded_nat_files": [
            "/home/eouser/eodag_downloads/msg_hrseviri/new_20260708091531.nat",
            "/home/eouser/eodag_downloads/msg_hrseviri/new_20260708093000.nat",
        ],
    }

    selected_for_transform = filter_and_sort_nat_files(
        extract_output["downloaded_nat_files"]
    )

    assert [path.name for path in selected_for_transform] == [
        "new_20260708091531.nat",
        "new_20260708093000.nat",
    ]
    assert all(path.name.startswith("new_") for path in selected_for_transform)
    assert all(path.name not in {Path(p).name for p in stale_folder_files} for path in selected_for_transform)


def test_channel_param_resolves_from_dag_run_conf(monkeypatch) -> None:
    monkeypatch.setattr(
        demo2,
        "get_current_context",
        lambda: {
            "dag_run": SimpleNamespace(conf={"channel": "ch1"}),
            "params": {},
        },
    )

    channel_param = DagParam(demo2.dag, "channel", default="ch9")

    assert demo2._normalize_channel(channel_param) == "ch1"


def test_normalize_channel_rejects_path_separators() -> None:
    for invalid in ["ch1/sub", "ch1\\sub"]:
        try:
            demo2._normalize_channel(invalid)
        except ValueError as exc:
            assert str(exc) == "channel must not contain path separators"
        else:
            raise AssertionError("Expected ValueError for channel with separator")


def test_normalize_channel_strips_whitespace() -> None:
    assert demo2._normalize_channel("  ch9  ") == "ch9"


def test_channels_param_resolves_from_dag_run_conf(monkeypatch) -> None:
    monkeypatch.setattr(
        demo2,
        "get_current_context",
        lambda: {
            "dag_run": SimpleNamespace(conf={"channels": ["ch1", "ch9"]}),
            "params": {},
        },
    )

    channels_param = DagParam(demo2.dag, "channels", default=["ch9"])

    assert demo2._normalize_channels(channels_param) == ["ch1", "ch9"]


def test_normalize_channels_deduplicates_list_entries() -> None:
    assert demo2._normalize_channels(["ch1", "ch9", "ch1"]) == ["ch1", "ch9"]


def test_normalize_channels_rejects_string_input() -> None:
    try:
        demo2._normalize_channels("ch1")
    except TypeError as exc:
        assert str(exc) == "channels must be a list of strings"
    else:
        raise AssertionError("Expected TypeError for string channel input")


def test_colormap_for_channel_uses_gray_for_visible_channels() -> None:
    for channel in ["ch1", "ch2", "ch3"]:
        assert demo2._colormap_for_channel(channel) == "gray"


def test_colormap_for_channel_uses_cividis_for_water_vapour_channels() -> None:
    for channel in ["ch5", "ch6"]:
        assert demo2._colormap_for_channel(channel) == "cividis"


def test_colormap_for_channel_defaults_to_reversed_gray_for_infrared_and_unknown() -> None:
    for channel in ["ch4", "ch7", "ch8", "ch9", "ch10", "ch11", "ch99"]:
        assert demo2._colormap_for_channel(channel) == "gray_r"


def test_is_thermal_channel_true_for_non_visible_channels() -> None:
    for channel in ["ch4", "ch5", "ch6", "ch7", "ch8", "ch9", "ch10", "ch11"]:
        assert demo2._is_thermal_channel(channel) is True


def test_is_thermal_channel_false_for_visible_channels() -> None:
    for channel in ["ch1", "ch2", "ch3"]:
        assert demo2._is_thermal_channel(channel) is False


def test_build_channel_calibration_map_selects_brightness_temperature_for_thermal_channels() -> None:
    assert demo2._build_channel_calibration_map(["ch1", "ch9"]) == {
        "vis_0.6": "radiance",
        "ir_10.8": "brightness_temperature",
    }


def test_build_channel_calibration_map_covers_default_channel_param() -> None:
    # Mirrors the DAG's default "channels" Param value (ch1-ch9).
    default_channels = ["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8", "ch9"]
    calibration_map = demo2._build_channel_calibration_map(default_channels)
    assert len(calibration_map) == len(default_channels)
    assert set(calibration_map.values()) <= {"radiance", "brightness_temperature"}
    assert calibration_map["vis_0.6"] == "radiance"
    assert calibration_map["ir_10.8"] == "brightness_temperature"


def test_build_channel_calibration_map_rejects_unknown_channel() -> None:
    try:
        demo2._build_channel_calibration_map(["ch99"])
    except ValueError as exc:
        assert "ch99" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown channel")


def test_normalize_search_limit_rejects_non_positive_values() -> None:
    for invalid in [0, -1]:
        try:
            demo2._normalize_search_limit(invalid)
        except ValueError as exc:
            assert str(exc) == "search_limit must be greater than 0"
        else:
            raise AssertionError("Expected ValueError for non-positive search_limit")


def test_build_visualization_annotation_metadata_includes_expected_fields() -> None:
    result = demo2._build_visualization_annotation_metadata(
        {
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "bbox": [-10.0, 35.0, 30.0, 65.0],
        },
        {
            "reprojection_bounds": [-25.0, 34.0, 45.0, 72.0],
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
        },
        "ch9",
        {
            "start_time": "2004-01-19 10:30:00",
            "grid_mapping": "spatial_ref",
            "long_name": "High-resolution visible channel",
        },
    )

    assert result == {
        "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
        "bbox": [-25.0, 34.0, 45.0, 72.0],
        "channel_name": "ch9",
        "reprojection_crs": "EPSG:4326",
        "resampling": "bilinear",
        "resolution": 0.05,
        "resolution_unit": "degrees",
        "start_time": "2004-01-19 10:30:00",
        "grid_mapping": "spatial_ref",
        "long_name": "High-resolution visible channel",
    }


def test_build_visualization_annotation_metadata_defaults_grid_mapping() -> None:
    result = demo2._build_visualization_annotation_metadata(
        {
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "bbox": [-10.0, 35.0, 30.0, 65.0],
        },
        {
            "reprojection_bounds": [-25.0, 34.0, 45.0, 72.0],
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
        },
        "ch9",
        {
            "long_name": "High-resolution visible channel",
        },
    )

    assert result["grid_mapping"] == "spatial_ref"


def test_build_visualization_annotation_metadata_source_overrides_grid_mapping() -> None:
    result = demo2._build_visualization_annotation_metadata(
        {
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "bbox": [-10.0, 35.0, 30.0, 65.0],
        },
        {
            "reprojection_bounds": [-25.0, 34.0, 45.0, 72.0],
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
        },
        "ch9",
        channel_attrs={
            "start_time": "2004-01-19 10:30:00",
            "grid_mapping": "spatial_ref",
            "long_name": "High-resolution visible channel",
        },
        source_channel_attrs={
            "grid_mapping": "geostationary",
            "platform_name": "MSG3",
        },
    )

    assert result["grid_mapping"] == "geostationary"
    assert result["platform_name"] == "MSG3"
    # channel_attrs-only fields (unaffected by reprojection) are preserved
    assert result["start_time"] == "2004-01-19 10:30:00"
    assert result["long_name"] == "High-resolution visible channel"


def test_build_visualization_annotation_metadata_ignores_empty_source_fields() -> None:
    result = demo2._build_visualization_annotation_metadata(
        {
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "bbox": [-10.0, 35.0, 30.0, 65.0],
        },
        {
            "reprojection_bounds": [-25.0, 34.0, 45.0, 72.0],
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
        },
        "ch9",
        channel_attrs={"grid_mapping": "spatial_ref"},
        source_channel_attrs={"grid_mapping": None, "platform_name": None},
    )

    assert result["grid_mapping"] == "spatial_ref"
    assert "platform_name" not in result


def test_build_visualization_annotation_metadata_includes_city_overlay_active_when_true() -> None:
    result = demo2._build_visualization_annotation_metadata(
        {
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "bbox": [-10.0, 35.0, 30.0, 65.0],
        },
        {
            "reprojection_bounds": [-25.0, 34.0, 45.0, 72.0],
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
        },
        "ch9",
        city_overlay_active=True,
    )

    assert result["city_overlay_active"] is True


def test_build_visualization_annotation_metadata_includes_country_borders_active_when_true() -> None:
    base_args = (
        {
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "bbox": [-10.0, 35.0, 30.0, 65.0],
        },
        {
            "reprojection_bounds": [-25.0, 34.0, 45.0, 72.0],
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
        },
        "ch9",
    )

    result_active = demo2._build_visualization_annotation_metadata(
        *base_args, country_borders_active=True
    )
    result_inactive = demo2._build_visualization_annotation_metadata(*base_args)

    assert result_active["country_borders_active"] is True
    assert "country_borders_active" not in result_inactive


def test_restore_dropped_time_coordinate_recovers_healpix_backend_output() -> None:
    # Mirrors what the astropy_healpix reprojection backend produces: "time"
    # survives as a bare dimension but the coordinate itself is gone, so
    # xarray substitutes a virtual 0, 1, 2, ... integer index.
    original = xr.Dataset(
        {"ch9": (("time", "y", "x"), np.zeros((2, 3, 3)))},
        coords={"time": pd.to_datetime(["2004-01-19T10:30:00", "2004-01-19T10:45:00"])},
    )
    reprojected_values = xr.DataArray(
        np.zeros((2, 5)), dims=("time", "healpix_index")
    ).to_dataset(name="ch9")
    assert "time" not in reprojected_values.coords

    restored = demo2._restore_dropped_time_coordinate(reprojected_values, original)

    assert "time" in restored.coords
    np.testing.assert_array_equal(restored["time"].values, original["time"].values)


def test_restore_dropped_time_coordinate_is_noop_when_time_coordinate_present() -> None:
    # Mirrors the rioxarray/EPSG:4326 backend, which preserves "time" as a
    # real coordinate; the helper must not touch it or return a copy.
    original = xr.Dataset(
        {"ch9": (("time", "y", "x"), np.zeros((2, 3, 3)))},
        coords={"time": pd.to_datetime(["2004-01-19T10:30:00", "2004-01-19T10:45:00"])},
    )

    restored = demo2._restore_dropped_time_coordinate(original, original)

    assert restored is original


def test_build_visualization_annotation_metadata_falls_back_to_search_bbox() -> None:
    result = demo2._build_visualization_annotation_metadata(
        {
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "bbox": [-10.0, 35.0, 30.0, 65.0],
        },
        {
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
        },
        "ch9",
    )

    assert result["bbox"] == [-10.0, 35.0, 30.0, 65.0]
