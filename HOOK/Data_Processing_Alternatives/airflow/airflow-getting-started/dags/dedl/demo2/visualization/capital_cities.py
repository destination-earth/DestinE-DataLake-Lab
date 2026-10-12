from __future__ import annotations

from typing import NamedTuple


class CityCoordinate(NamedTuple):
    """A labeled point (e.g. a capital city) to sample/overlay on frames."""

    name: str
    lat: float
    lon: float


# European capitals (name, lat, lon in decimal degrees). Not pre-filtered to
# any particular reprojection AOI: the DAG's bbox is a user-settable param,
# so AOI membership is checked at render time against the actual data
# array's coordinate extent (see visualization_helper._resolve_city_pixels).
EUROPEAN_CAPITALS: tuple[CityCoordinate, ...] = (
    CityCoordinate("Reykjavik", 64.1466, -21.9426),
    CityCoordinate("Dublin", 53.3498, -6.2603),
    CityCoordinate("London", 51.5074, -0.1278),
    CityCoordinate("Lisbon", 38.7223, -9.1393),
    CityCoordinate("Madrid", 40.4168, -3.7038),
    CityCoordinate("Paris", 48.8566, 2.3522),
    CityCoordinate("Clermont-Ferrand", 45.7772, 3.0870),
    CityCoordinate("Brussels", 50.8503, 4.3517),
    CityCoordinate("Amsterdam", 52.3676, 4.9041),
    CityCoordinate("Luxembourg", 49.6116, 6.1319),
    CityCoordinate("Bern", 46.9480, 7.4474),
    CityCoordinate("Rome", 41.9028, 12.4964),
    CityCoordinate("Vaduz", 47.1410, 9.5209),
    CityCoordinate("Monaco", 43.7384, 7.4246),
    CityCoordinate("San Marino", 43.9424, 12.4578),
    CityCoordinate("Valletta", 35.8989, 14.5146),
    CityCoordinate("Andorra la Vella", 42.5063, 1.5218),
    CityCoordinate("Berlin", 52.5200, 13.4050),
    CityCoordinate("Copenhagen", 55.6761, 12.5683),
    CityCoordinate("Oslo", 59.9139, 10.7522),
    CityCoordinate("Stockholm", 59.3293, 18.0686),
    CityCoordinate("Helsinki", 60.1699, 24.9384),
    CityCoordinate("Tallinn", 59.4370, 24.7536),
    CityCoordinate("Riga", 56.9496, 24.1052),
    CityCoordinate("Vilnius", 54.6872, 25.2797),
    CityCoordinate("Warsaw", 52.2297, 21.0122),
    CityCoordinate("Prague", 50.0755, 14.4378),
    CityCoordinate("Vienna", 48.2082, 16.3738),
    CityCoordinate("Bratislava", 48.1486, 17.1077),
    CityCoordinate("Budapest", 47.4979, 19.0402),
    CityCoordinate("Ljubljana", 46.0569, 14.5058),
    CityCoordinate("Zagreb", 45.8150, 15.9819),
    CityCoordinate("Sarajevo", 43.8563, 18.4131),
    CityCoordinate("Podgorica", 42.4304, 19.2594),
    CityCoordinate("Belgrade", 44.7866, 20.4489),
    CityCoordinate("Pristina", 42.6629, 21.1655),
    CityCoordinate("Skopje", 41.9981, 21.4254),
    CityCoordinate("Tirana", 41.3275, 19.8187),
    CityCoordinate("Athens", 37.9838, 23.7275),
    CityCoordinate("Sofia", 42.6977, 23.3219),
    CityCoordinate("Bucharest", 44.4268, 26.1025),
    CityCoordinate("Chisinau", 47.0105, 28.8638),
    CityCoordinate("Kyiv", 50.4501, 30.5234),
    CityCoordinate("Minsk", 53.9006, 27.5590),
    CityCoordinate("Nicosia", 35.1856, 33.3823),
)
