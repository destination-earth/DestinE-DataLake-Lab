from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
import xarray as xr
from types import SimpleNamespace

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAGS_PATH = PROJECT_ROOT / "dags"
if str(DAGS_PATH) not in sys.path:
    sys.path.insert(0, str(DAGS_PATH))

from dedl.visualization.capital_cities import CityCoordinate  # noqa: E402
from dedl.visualization.visualization_helper import (  # noqa: E402
    _ResolvedCityPixel,
    _build_annotation_lines,
    _format_bbox,
    _format_frame_time,
    _resolve_city_pixels,
    _resolve_spatial_coord_names,
    _sample_city_temperatures_celsius,
    compute_display_range,
    create_mp4_from_dataarray,
    reproject_healpix_dataarray_to_raster,
    resolve_data_variable,
)


def _build_healpix_dataarray(nside: int = 2) -> xr.DataArray:
    # Real HEALPix pixel centres (ring order), matching what
    # defair_ops's AstropyHealpixBackend attaches as lon/lat coords on the
    # "healpix_index" dim.
    astropy_healpix = pytest.importorskip("astropy_healpix")
    npix = 12 * nside * nside
    hp = astropy_healpix.HEALPix(nside=nside, order="ring")
    lon, lat = hp.healpix_to_lonlat(np.arange(npix))

    data = np.tile(np.arange(npix, dtype=float), (2, 1))
    return xr.DataArray(
        data,
        dims=("time", "healpix_index"),
        coords={
            "time": np.array([0, 1]),
            "healpix_index": np.arange(npix),
            "lon": ("healpix_index", lon.to("deg").value),
            "lat": ("healpix_index", lat.to("deg").value),
        },
    )


def _build_dataset() -> xr.Dataset:
    data = np.arange(24, dtype=float).reshape(3, 2, 4)
    return xr.Dataset(
        data_vars={
            "ch9": (("time", "y", "x"), data),
            "other": (("time", "y", "x"), data + 100),
        },
        coords={"time": np.array([0, 1, 2])},
    )


def test_resolve_data_variable_prefers_requested_name() -> None:
    dataset = _build_dataset()

    result = resolve_data_variable(dataset, preferred_name="ch9")

    assert result.name == "ch9"


def test_resolve_data_variable_falls_back_to_first_data_var() -> None:
    dataset = xr.Dataset(
        data_vars={"other": (("time", "y", "x"), np.ones((2, 2, 2), dtype=float))},
        coords={"time": np.array([0, 1])},
    )

    result = resolve_data_variable(dataset, preferred_name="ch9")

    assert result.name == "other"


def test_resolve_data_variable_raises_for_empty_dataset() -> None:
    with pytest.raises(ValueError, match="No data variables found"):
        resolve_data_variable(xr.Dataset(), preferred_name="ch9")


def test_compute_display_range_uses_percentiles() -> None:
    values = np.array([0.0, 1.0, 2.0, 100.0])

    vmin, vmax = compute_display_range(values, low_percentile=0.0, high_percentile=75.0)

    assert vmin == 0.0
    assert vmax == pytest.approx(26.5)


def test_compute_display_range_raises_for_non_finite_values() -> None:
    with pytest.raises(ValueError, match="only NaN/inf"):
        compute_display_range(np.array([np.nan, np.inf]))


def test_create_mp4_from_dataarray_requires_time_dimension(tmp_path: Path) -> None:
    arr = xr.DataArray(np.ones((2, 2), dtype=float), dims=("y", "x"))

    with pytest.raises(ValueError, match="must contain a 'time' dimension"):
        create_mp4_from_dataarray(arr, str(tmp_path / "out.mp4"))


def test_create_mp4_from_dataarray_rejects_non_raster_spatial_dims(tmp_path: Path) -> None:
    # Unstructured/cell-indexed data (e.g. HEALPix output) has a single
    # spatial dim, not a (row, col) raster this function can draw frames for.
    arr = xr.DataArray(np.ones((3, 10), dtype=float), dims=("time", "cell"))

    with pytest.raises(ValueError, match="Unstructured/cell-indexed data"):
        create_mp4_from_dataarray(arr, str(tmp_path / "out.mp4"))


def test_reproject_healpix_dataarray_to_raster_requires_healpix_dim() -> None:
    arr = xr.DataArray(np.ones((2, 2), dtype=float), dims=("y", "x"))

    with pytest.raises(ValueError, match="requires a 'healpix_index' dim"):
        reproject_healpix_dataarray_to_raster(arr, bounds=(-25.0, 34.0, 45.0, 72.0))


def test_reproject_healpix_dataarray_to_raster_rejects_invalid_pixel_count() -> None:
    arr = xr.DataArray(
        np.ones((2, 10), dtype=float),
        dims=("time", "healpix_index"),
        coords={
            "healpix_index": np.arange(10),
            "lon": ("healpix_index", np.zeros(10)),
            "lat": ("healpix_index", np.zeros(10)),
        },
    )

    with pytest.raises(ValueError, match="not a valid HEALPix pixel count"):
        reproject_healpix_dataarray_to_raster(arr, bounds=(-25.0, 34.0, 45.0, 72.0))


def test_reproject_healpix_dataarray_to_raster_builds_regular_display_grid() -> None:
    data_array = _build_healpix_dataarray(nside=2)
    bounds = (-25.0, 34.0, 45.0, 72.0)

    raster = reproject_healpix_dataarray_to_raster(data_array, bounds=bounds)

    assert raster.dims == ("time", "y", "x")
    assert "healpix_index" not in raster.coords
    assert list(raster["time"].values) == [0, 1]

    lon_min, lat_min, lon_max, lat_max = bounds
    assert raster["lon"].values.min() == pytest.approx(lon_min)
    assert raster["lon"].values.max() == pytest.approx(lon_max)
    assert raster["lat"].values.min() == pytest.approx(lat_min)
    assert raster["lat"].values.max() == pytest.approx(lat_max)
    # row 0 is the northern edge, like a normal raster/image
    assert raster["lat"].values[0] > raster["lat"].values[-1]


def test_reproject_healpix_dataarray_to_raster_assigns_nearest_pixel_values() -> None:
    astropy_healpix = pytest.importorskip("astropy_healpix")
    nside = 2
    npix = 12 * nside * nside
    hp = astropy_healpix.HEALPix(nside=nside, order="ring")

    data_array = _build_healpix_dataarray(nside=nside)
    raster = reproject_healpix_dataarray_to_raster(data_array, bounds=(-25.0, 34.0, 45.0, 72.0))

    frame = raster.isel(time=0).values
    assert not np.isnan(frame).any()

    # Every rasterized value must be one of the source HEALPix pixel
    # indices (0..npix-1), since values are looked up, never interpolated.
    assert set(np.unique(frame).astype(int)).issubset(set(range(npix)))

    # Spot-check: the raster cell nearest a given pixel's own centre must
    # resolve back to that pixel's value.
    sample_pixel = npix // 2
    lon, lat = hp.healpix_to_lonlat(sample_pixel)
    lon_deg, lat_deg = lon.to("deg").value, lat.to("deg").value
    if -25.0 <= lon_deg <= 45.0 and 34.0 <= lat_deg <= 72.0:
        nearest = raster.sel(lon=lon_deg, lat=lat_deg, method="nearest").isel(time=0).item()
        assert nearest == sample_pixel


def test_create_mp4_from_dataarray_generates_expected_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dataset = _build_dataset()

    written_frames: list[np.ndarray] = []

    class _DummyWriter:
        def __init__(self, *_args, **_kwargs) -> None:
            self.closed = False

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            self.closed = True
            return False

        def append_data(self, frame: np.ndarray) -> None:
            written_frames.append(frame)

    monkeypatch.setattr(
        "dedl.visualization.visualization_helper.imageio",
        SimpleNamespace(get_writer=lambda *args, **kwargs: _DummyWriter()),
    )
    monkeypatch.setattr(
        "dedl.visualization.visualization_helper._to_uint8_rgb_frame",
        lambda values, vmin, vmax, colormap_name: np.zeros((*values.shape, 3), dtype=np.uint8),
    )

    result = create_mp4_from_dataarray(
        dataset["ch9"],
        str(tmp_path / "movie.mp4"),
        fps=5,
        frame_stride=2,
        max_frames=2,
        colormap_name="inferno",
        low_percentile=0.0,
        high_percentile=100.0,
    )

    assert result["frame_count"] == 2
    assert result["fps"] == 5
    assert result["video_path"].endswith("movie.mp4")
    assert result["vmin"] == 0.0
    assert result["vmax"] == 23.0
    assert len(written_frames) == 2
    assert written_frames[0].dtype == np.uint8
    assert written_frames[0].shape == (2, 4, 3)


def test_format_frame_time_supports_datetime64() -> None:
    result = _format_frame_time(np.datetime64("2024-07-09T12:34:56"))

    assert result == "09/07/2024 12:34:56"


def test_format_frame_time_supports_epoch_nanoseconds() -> None:
    # 2004-01-19 10:30:00 UTC represented in nanoseconds since epoch.
    result = _format_frame_time(1_074_508_200_000_000_000)

    assert result == "19/01/2004 10:30:00"


def test_format_frame_time_supports_seconds_plus_nanoseconds() -> None:
    result = _format_frame_time((1_074_508_200, 123_000_000))

    assert result == "19/01/2004 10:30:00"


def test_format_bbox_formats_four_coordinate_bbox() -> None:
    result = _format_bbox([-10, 35, 30.12345, 65])

    assert result == "-10.0000, 35.0000, 30.1235, 65.0000"


def test_build_annotation_lines_includes_time_collection_channel_and_bbox() -> None:
    result = _build_annotation_lines(
        time_value=np.datetime64("2024-07-09T12:34:56"),
        annotation_metadata={
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "channel_name": "ch9",
            "bbox": [-25.0, 34.0, 45.0, 72.0],
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
            "start_time": "2004-01-19 10:30:00",
            "grid_mapping": "spatial_ref",
            "long_name": "High-resolution visible channel",
        },
    )

    assert result == [
        "time: 09/07/2024 12:34:56",
        "collection: EO.EUM.DAT.MSG.HRSEVIRI",
        "channel: ch9",
        "bbox: -25.0000, 34.0000, 45.0000, 72.0000",
        "target: EPSG:4326",
        "resampling: bilinear",
        "resolution: 0.05 degrees",
        "grid_mapping: spatial_ref",
        "long_name: High-resolution visible channel",
    ]


def test_build_annotation_lines_includes_platform_name_when_present() -> None:
    result = _build_annotation_lines(
        time_value=np.datetime64("2024-07-09T12:34:56"),
        annotation_metadata={
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "channel_name": "ch9",
            "bbox": [-25.0, 34.0, 45.0, 72.0],
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
            "grid_mapping": "geostationary",
            "platform_name": "MSG3",
        },
    )

    assert result == [
        "time: 09/07/2024 12:34:56",
        "collection: EO.EUM.DAT.MSG.HRSEVIRI",
        "channel: ch9",
        "bbox: -25.0000, 34.0000, 45.0000, 72.0000",
        "target: EPSG:4326",
        "resampling: bilinear",
        "resolution: 0.05 degrees",
        "grid_mapping: geostationary",
        "platform_name: MSG3",
    ]


def test_build_annotation_lines_skips_missing_optional_channel_metadata() -> None:
    result = _build_annotation_lines(
        time_value=np.datetime64("2024-07-09T12:34:56"),
        annotation_metadata={
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "channel_name": "ch9",
            "bbox": [-25.0, 34.0, 45.0, 72.0],
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
        },
    )

    assert result == [
        "time: 09/07/2024 12:34:56",
        "collection: EO.EUM.DAT.MSG.HRSEVIRI",
        "channel: ch9",
        "bbox: -25.0000, 34.0000, 45.0000, 72.0000",
        "target: EPSG:4326",
        "resampling: bilinear",
        "resolution: 0.05 degrees",
    ]


def test_create_mp4_from_dataarray_applies_annotation_overlay(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    dataset = xr.Dataset(
        data_vars={"ch9": (("time", "y", "x"), np.arange(8, dtype=float).reshape(2, 2, 2))},
        coords={"time": np.array([np.datetime64("2024-07-09T00:00:00"), np.datetime64("2024-07-09T01:00:00")])},
    )

    written_frames: list[np.ndarray] = []
    captured_lines: list[list[str]] = []

    class _DummyWriter:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def append_data(self, frame: np.ndarray) -> None:
            written_frames.append(frame)

    monkeypatch.setattr(
        "dedl.visualization.visualization_helper.imageio",
        SimpleNamespace(get_writer=lambda *args, **kwargs: _DummyWriter()),
    )
    monkeypatch.setattr(
        "dedl.visualization.visualization_helper._to_uint8_rgb_frame",
        lambda values, vmin, vmax, colormap_name: np.zeros((*values.shape, 3), dtype=np.uint8),
    )

    def _capture_overlay(frame: np.ndarray, lines: list[str]) -> np.ndarray:
        captured_lines.append(lines)
        return frame

    monkeypatch.setattr(
        "dedl.visualization.visualization_helper._overlay_annotation_banner",
        _capture_overlay,
    )

    create_mp4_from_dataarray(
        dataset["ch9"],
        str(tmp_path / "annotated.mp4"),
        annotation_metadata={
            "collection_id": "EO.EUM.DAT.MSG.HRSEVIRI",
            "channel_name": "ch9",
            "bbox": [-25.0, 34.0, 45.0, 72.0],
            "reprojection_crs": "EPSG:4326",
            "resampling": "bilinear",
            "resolution": 0.05,
            "resolution_unit": "degrees",
            "start_time": "2004-01-19 10:30:00",
            "grid_mapping": "spatial_ref",
            "long_name": "High-resolution visible channel",
        },
        low_percentile=0.0,
        high_percentile=100.0,
    )

    assert len(written_frames) == 2
    assert captured_lines == [
        [
            "time: 09/07/2024 00:00:00",
            "collection: EO.EUM.DAT.MSG.HRSEVIRI",
            "channel: ch9",
            "bbox: -25.0000, 34.0000, 45.0000, 72.0000",
            "target: EPSG:4326",
            "resampling: bilinear",
            "resolution: 0.05 degrees",
            "grid_mapping: spatial_ref",
            "long_name: High-resolution visible channel",
        ],
        [
            "time: 09/07/2024 01:00:00",
            "collection: EO.EUM.DAT.MSG.HRSEVIRI",
            "channel: ch9",
            "bbox: -25.0000, 34.0000, 45.0000, 72.0000",
            "target: EPSG:4326",
            "resampling: bilinear",
            "resolution: 0.05 degrees",
            "grid_mapping: spatial_ref",
            "long_name: High-resolution visible channel",
        ],
    ]


def test_resolve_city_pixels_finds_nearest_grid_index() -> None:
    x_coords = np.array([-10.0, -5.0, 0.0, 5.0, 10.0])
    y_coords = np.array([50.0, 45.0, 40.0])

    resolved = _resolve_city_pixels(x_coords, y_coords, [CityCoordinate("Testville", 44.0, 4.5)])

    assert resolved == [_ResolvedCityPixel(name="Testville", row=1, col=3)]


def test_resolve_city_pixels_skips_cities_outside_grid_tolerance() -> None:
    x_coords = np.array([-10.0, -5.0, 0.0, 5.0, 10.0])
    y_coords = np.array([50.0, 45.0, 40.0])

    resolved = _resolve_city_pixels(x_coords, y_coords, [CityCoordinate("FarAway", 44.0, 500.0)])

    assert resolved == []


def test_resolve_city_pixels_handles_curvilinear_2d_coordinates() -> None:
    # Non-separable grid: both lat and lon vary along both dims, as on a
    # curvilinear/polar-stereographic reprojection target rather than a
    # plate-carrée raster.
    lon_grid = np.array([[0.0, 5.0, 10.0], [1.0, 6.0, 11.0]])
    lat_grid = np.array([[40.0, 41.0, 42.0], [45.0, 46.0, 47.0]])

    resolved = _resolve_city_pixels(lon_grid, lat_grid, [CityCoordinate("Testville", 46.0, 6.0)])

    assert resolved == [_ResolvedCityPixel(name="Testville", row=1, col=1)]


def test_resolve_city_pixels_skips_cities_outside_curvilinear_tolerance() -> None:
    lon_grid = np.array([[0.0, 5.0, 10.0], [1.0, 6.0, 11.0]])
    lat_grid = np.array([[40.0, 41.0, 42.0], [45.0, 46.0, 47.0]])

    resolved = _resolve_city_pixels(lon_grid, lat_grid, [CityCoordinate("FarAway", 90.0, 200.0)])

    assert resolved == []


def test_resolve_spatial_coord_names_prefers_lon_lat_when_present() -> None:
    data_array = xr.DataArray(
        np.zeros((2, 2)),
        dims=("lat", "lon"),
        coords={"lat": np.array([50.0, 40.0]), "lon": np.array([0.0, 10.0])},
    )

    assert _resolve_spatial_coord_names(data_array) == ("lon", "lat")


def test_resolve_spatial_coord_names_falls_back_to_x_y() -> None:
    data_array = xr.DataArray(
        np.zeros((2, 2)),
        dims=("y", "x"),
        coords={"y": np.array([50.0, 40.0]), "x": np.array([0.0, 10.0])},
    )

    assert _resolve_spatial_coord_names(data_array) == ("x", "y")


def test_resolve_spatial_coord_names_returns_none_when_absent() -> None:
    data_array = xr.DataArray(np.zeros((2, 2)), dims=("row", "col"))

    assert _resolve_spatial_coord_names(data_array) is None


def test_sample_city_temperatures_celsius_converts_and_skips_nan() -> None:
    values = np.array([[293.15, np.nan], [300.0, 310.0]])
    resolved_city_pixels = [
        _ResolvedCityPixel(name="Finite", row=0, col=0),
        _ResolvedCityPixel(name="Missing", row=0, col=1),
    ]

    samples = _sample_city_temperatures_celsius(values, resolved_city_pixels)

    assert samples == [("Finite", 0, 0, 20.0)]


def test_create_mp4_from_dataarray_applies_city_temperature_overlay(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    values = np.array(
        [
            [[300.0, 301.0], [302.0, 293.15]],
            [[300.0, 301.0], [302.0, np.nan]],
        ],
        dtype=float,
    )
    dataset = xr.Dataset(
        data_vars={"ch9": (("time", "y", "x"), values)},
        coords={
            "time": np.array([np.datetime64("2024-07-09T00:00:00"), np.datetime64("2024-07-09T01:00:00")]),
            "y": np.array([50.0, 40.0]),
            "x": np.array([0.0, 10.0]),
        },
    )

    written_frames: list[np.ndarray] = []
    captured_samples: list[list[tuple[str, int, int, float]]] = []

    class _DummyWriter:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def append_data(self, frame: np.ndarray) -> None:
            written_frames.append(frame)

    monkeypatch.setattr(
        "dedl.visualization.visualization_helper.imageio",
        SimpleNamespace(get_writer=lambda *args, **kwargs: _DummyWriter()),
    )
    monkeypatch.setattr(
        "dedl.visualization.visualization_helper._to_uint8_rgb_frame",
        lambda values, vmin, vmax, colormap_name: np.zeros((*values.shape, 3), dtype=np.uint8),
    )

    def _capture_city_overlay(frame: np.ndarray, samples: list[tuple[str, int, int, float]]) -> np.ndarray:
        captured_samples.append(samples)
        return frame

    monkeypatch.setattr(
        "dedl.visualization.visualization_helper._overlay_city_temperatures",
        _capture_city_overlay,
    )

    create_mp4_from_dataarray(
        dataset["ch9"],
        str(tmp_path / "city_overlay.mp4"),
        low_percentile=0.0,
        high_percentile=100.0,
        city_temperature_overlay=[CityCoordinate("Testville", 40.0, 10.0)],
    )

    assert len(written_frames) == 2
    assert captured_samples == [
        [("Testville", 1, 1, 20.0)],
        [],
    ]


def test_create_mp4_from_dataarray_applies_city_temperature_overlay_with_lon_lat_coords(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Regression test: the DAG's default reprojection_crs is EPSG:4326
    # (geographic), and defair_ops' rioxarray backend names reprojected
    # coordinates "lon"/"lat" for geographic targets (only "x"/"y" for
    # projected targets) — this is the real-world shape the overlay must
    # handle, not just the "x"/"y" case above.
    values = np.array(
        [
            [[300.0, 301.0], [302.0, 293.15]],
            [[300.0, 301.0], [302.0, np.nan]],
        ],
        dtype=float,
    )
    dataset = xr.Dataset(
        data_vars={"ch9": (("time", "lat", "lon"), values)},
        coords={
            "time": np.array([np.datetime64("2024-07-09T00:00:00"), np.datetime64("2024-07-09T01:00:00")]),
            "lat": np.array([50.0, 40.0]),
            "lon": np.array([0.0, 10.0]),
        },
    )

    written_frames: list[np.ndarray] = []
    captured_samples: list[list[tuple[str, int, int, float]]] = []

    class _DummyWriter:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def append_data(self, frame: np.ndarray) -> None:
            written_frames.append(frame)

    monkeypatch.setattr(
        "dedl.visualization.visualization_helper.imageio",
        SimpleNamespace(get_writer=lambda *args, **kwargs: _DummyWriter()),
    )
    monkeypatch.setattr(
        "dedl.visualization.visualization_helper._to_uint8_rgb_frame",
        lambda values, vmin, vmax, colormap_name: np.zeros((*values.shape, 3), dtype=np.uint8),
    )

    def _capture_city_overlay(frame: np.ndarray, samples: list[tuple[str, int, int, float]]) -> np.ndarray:
        captured_samples.append(samples)
        return frame

    monkeypatch.setattr(
        "dedl.visualization.visualization_helper._overlay_city_temperatures",
        _capture_city_overlay,
    )

    create_mp4_from_dataarray(
        dataset["ch9"],
        str(tmp_path / "city_overlay_lonlat.mp4"),
        low_percentile=0.0,
        high_percentile=100.0,
        city_temperature_overlay=[CityCoordinate("Testville", 40.0, 10.0)],
    )

    assert len(written_frames) == 2
    assert captured_samples == [
        [("Testville", 1, 1, 20.0)],
        [],
    ]


def test_create_mp4_from_dataarray_city_overlay_defaults_to_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dataset = _build_dataset()
    overlay_calls: list[object] = []

    class _DummyWriter:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def append_data(self, frame: np.ndarray) -> None:
            pass

    monkeypatch.setattr(
        "dedl.visualization.visualization_helper.imageio",
        SimpleNamespace(get_writer=lambda *args, **kwargs: _DummyWriter()),
    )
    monkeypatch.setattr(
        "dedl.visualization.visualization_helper._to_uint8_rgb_frame",
        lambda values, vmin, vmax, colormap_name: np.zeros((*values.shape, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(
        "dedl.visualization.visualization_helper._overlay_city_temperatures",
        lambda *args, **kwargs: overlay_calls.append(1),
    )

    create_mp4_from_dataarray(
        dataset["ch9"],
        str(tmp_path / "no_city_overlay.mp4"),
        low_percentile=0.0,
        high_percentile=100.0,
    )

    assert overlay_calls == []
