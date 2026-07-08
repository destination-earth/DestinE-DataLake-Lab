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

from dedl.visualization.visualization_helper import (  # noqa: E402
    compute_display_range,
    create_mp4_from_dataarray,
    resolve_data_variable,
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
