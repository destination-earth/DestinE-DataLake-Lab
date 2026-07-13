from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DAGS_PATH = PROJECT_ROOT / "dags"
if str(DAGS_PATH) not in sys.path:
    sys.path.insert(0, str(DAGS_PATH))

from dedl.visualization.capital_cities import CityCoordinate, EUROPEAN_CAPITALS  # noqa: E402


def test_european_capitals_non_empty() -> None:
    assert len(EUROPEAN_CAPITALS) > 0


def test_european_capitals_names_are_unique() -> None:
    names = [city.name for city in EUROPEAN_CAPITALS]
    assert len(names) == len(set(names))


def test_european_capitals_lat_within_valid_range() -> None:
    for city in EUROPEAN_CAPITALS:
        assert -90.0 <= city.lat <= 90.0


def test_european_capitals_lon_within_valid_range() -> None:
    for city in EUROPEAN_CAPITALS:
        assert -180.0 <= city.lon <= 180.0


def test_european_capitals_entries_are_city_coordinate_instances() -> None:
    for city in EUROPEAN_CAPITALS:
        assert isinstance(city, CityCoordinate)
