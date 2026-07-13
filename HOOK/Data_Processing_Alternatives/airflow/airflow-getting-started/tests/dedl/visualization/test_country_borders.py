from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAGS_PATH = PROJECT_ROOT / "dags"
if str(DAGS_PATH) not in sys.path:
    sys.path.insert(0, str(DAGS_PATH))

from dedl.visualization.country_borders import load_country_border_lines  # noqa: E402


def test_load_country_border_lines_extracts_linestring_and_multilinestring(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("cartopy")
    from shapely.geometry import LineString, MultiLineString

    fake_geometries_by_name = {
        "admin_0_boundary_lines_land": [
            LineString([(0.0, 40.0), (1.0, 41.0), (2.0, 42.0)]),
            MultiLineString(
                [
                    [(10.0, 50.0), (11.0, 51.0)],
                    [(20.0, 60.0), (21.0, 61.0), (22.0, 62.0)],
                ]
            ),
        ],
        "coastline": [
            LineString([(30.0, 70.0), (31.0, 71.0)]),
        ],
    }

    def _fake_natural_earth(**kwargs):
        return kwargs["name"]

    class _FakeReader:
        def __init__(self, path):
            self._path = path

        def geometries(self):
            return iter(fake_geometries_by_name[self._path])

    monkeypatch.setattr("cartopy.io.shapereader.natural_earth", _fake_natural_earth)
    monkeypatch.setattr("cartopy.io.shapereader.Reader", _FakeReader)

    lines = load_country_border_lines()

    assert lines == [
        [(0.0, 40.0), (1.0, 41.0), (2.0, 42.0)],
        [(10.0, 50.0), (11.0, 51.0)],
        [(20.0, 60.0), (21.0, 61.0), (22.0, 62.0)],
        [(30.0, 70.0), (31.0, 71.0)],
    ]


def test_load_country_border_lines_passes_expected_natural_earth_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("cartopy")
    captured_calls = []

    def _fake_natural_earth(**kwargs):
        captured_calls.append(kwargs)
        return "fake/path.shp"

    class _FakeReader:
        def __init__(self, path):
            pass

        def geometries(self):
            return iter([])

    monkeypatch.setattr("cartopy.io.shapereader.natural_earth", _fake_natural_earth)
    monkeypatch.setattr("cartopy.io.shapereader.Reader", _FakeReader)

    load_country_border_lines()

    assert captured_calls == [
        {
            "resolution": "50m",
            "category": "cultural",
            "name": "admin_0_boundary_lines_land",
        },
        {
            "resolution": "50m",
            "category": "physical",
            "name": "coastline",
        },
    ]
