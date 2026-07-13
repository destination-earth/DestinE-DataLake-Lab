from __future__ import annotations


def _load_natural_earth_lines(
    *, category: str, name: str, resolution: str
) -> list[list[tuple[float, float]]]:
    """
    Fetch (and cache) a Natural Earth shapefile via cartopy.io.shapereader
    and return each line geometry as a list of (lon, lat) vertex tuples in
    decimal degrees.

    cartopy caches the downloaded shapefile under its configured data_dir, so
    only the first call across the lifetime of that cache directory triggers
    a network fetch; subsequent calls (including from other mapped
    visualise_one task instances) reuse the cached file.

    cartopy is imported here, not at module scope, per this repo's
    convention for optional/heavy runtime deps. Raises whatever
    cartopy.io.shapereader.natural_earth/Reader raise on network or parsing
    failure — callers decide whether/how to degrade gracefully.
    """
    from cartopy.io import shapereader

    shapefile_path = shapereader.natural_earth(
        resolution=resolution,
        category=category,
        name=name,
    )
    reader = shapereader.Reader(shapefile_path)

    lines: list[list[tuple[float, float]]] = []
    for geometry in reader.geometries():
        if geometry.geom_type == "LineString":
            lines.append(list(geometry.coords))
        elif geometry.geom_type == "MultiLineString":
            lines.extend(list(part.coords) for part in geometry.geoms)
    return lines


def load_country_border_lines(
    resolution: str = "50m",
) -> list[list[tuple[float, float]]]:
    """
    Fetch (and cache) Natural Earth's admin_0_boundary_lines_land shapefile
    (internal country borders) and coastline shapefile (country outlines
    against the sea), and return the merged set of lines as (lon, lat)
    vertex-tuple polylines in decimal degrees.

    admin_0_boundary_lines_land alone stops wherever a border follows a
    coast, so a country like the UK or Iceland would otherwise render with
    no outline at all — merging in the coastline layer closes that gap.
    """
    return _load_natural_earth_lines(
        category="cultural",
        name="admin_0_boundary_lines_land",
        resolution=resolution,
    ) + _load_natural_earth_lines(
        category="physical",
        name="coastline",
        resolution=resolution,
    )
