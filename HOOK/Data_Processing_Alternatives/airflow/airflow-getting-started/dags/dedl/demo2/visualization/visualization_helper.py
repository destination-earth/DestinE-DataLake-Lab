from __future__ import annotations

import math
from collections.abc import Sequence
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

from dedl.demo2.visualization.capital_cities import CityCoordinate

try:
    import imageio.v2 as imageio
except ModuleNotFoundError:  # pragma: no cover - depends on optional runtime deps
    imageio = None


def _format_frame_time(time_value: Any) -> str:
    scalar = np.asarray(time_value).item() if np.asarray(time_value).shape == () else time_value

    def _format_epoch_seconds(epoch_seconds: float) -> str:
        parsed = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        return parsed.strftime("%d/%m/%Y %H:%M:%S")

    if isinstance(scalar, np.datetime64):
        as_seconds = np.datetime64(scalar, "s")
        parsed = datetime.strptime(
            np.datetime_as_string(as_seconds, unit="s"),
            "%Y-%m-%dT%H:%M:%S",
        )
        return parsed.strftime("%d/%m/%Y %H:%M:%S")

    if isinstance(scalar, datetime):
        if scalar.tzinfo is None:
            scalar = scalar.replace(tzinfo=timezone.utc)
        else:
            scalar = scalar.astimezone(timezone.utc)
        return scalar.strftime("%d/%m/%Y %H:%M:%S")

    if isinstance(scalar, (list, tuple)) and len(scalar) == 2:
        seconds, nanoseconds = scalar
        if isinstance(seconds, (int, float, np.integer, np.floating)) and isinstance(
            nanoseconds,
            (int, float, np.integer, np.floating),
        ):
            return _format_epoch_seconds(float(seconds) + (float(nanoseconds) / 1_000_000_000.0))

    if isinstance(scalar, dict):
        seconds = scalar.get("seconds")
        nanoseconds = scalar.get("nanoseconds", 0)
        if isinstance(seconds, (int, float, np.integer, np.floating)) and isinstance(
            nanoseconds,
            (int, float, np.integer, np.floating),
        ):
            return _format_epoch_seconds(float(seconds) + (float(nanoseconds) / 1_000_000_000.0))

    if isinstance(scalar, (int, float, np.integer, np.floating)):
        epoch_value = float(scalar)
        abs_epoch_value = abs(epoch_value)
        if abs_epoch_value >= 1e17:
            return _format_epoch_seconds(epoch_value / 1_000_000_000.0)
        if abs_epoch_value >= 1e14:
            return _format_epoch_seconds(epoch_value / 1_000_000.0)
        if abs_epoch_value >= 1e11:
            return _format_epoch_seconds(epoch_value / 1_000.0)
        return _format_epoch_seconds(epoch_value)

    return str(scalar)


def _format_bbox(bbox: Any) -> str:
    if isinstance(bbox, (list, tuple)) and len(bbox) == 4:
        return ", ".join(
            f"{Decimal(str(coord)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP):f}"
            for coord in bbox
        )
    return str(bbox)


def _build_annotation_lines(*, time_value: Any, annotation_metadata: dict[str, Any]) -> list[str]:
    lines = [
        f"time: {_format_frame_time(time_value)}",
        f"collection: {annotation_metadata['collection_id']}",
        "source: EUMETSAT via DestinE Data Lake (DEDL)",
        f"channel: {annotation_metadata['channel_name']}",
        f"bbox: {_format_bbox(annotation_metadata['bbox'])}",
        f"target: {annotation_metadata.get('reprojection_crs', 'N/A')}",
        f"resampling: {annotation_metadata.get('resampling', 'N/A')}",
        f"resolution: {annotation_metadata.get('resolution', 'N/A')} {annotation_metadata.get('resolution_unit', '')}".rstrip(),
    ]

    if "grid_mapping" in annotation_metadata:
        lines.append(f"grid_mapping: {annotation_metadata['grid_mapping']}")
    if "platform_name" in annotation_metadata:
        lines.append(f"platform_name: {annotation_metadata['platform_name']}")
    if "long_name" in annotation_metadata:
        lines.append(f"long_name: {annotation_metadata['long_name']}")
    if "city_overlay_active" in annotation_metadata:
        lines.append("city markers: satellite brightness temp, not ground station data")
    if "country_borders_active" in annotation_metadata:
        lines.append("borders: Natural Earth (public domain)")

    return lines


def _overlay_annotation_banner(frame: np.ndarray, lines: list[str]) -> np.ndarray:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional runtime deps
        raise RuntimeError(
            "Pillow is required to render video annotations. Install pillow to enable overlays."
        ) from exc

    image = Image.fromarray(frame, mode="RGB")
    draw = ImageDraw.Draw(image, mode="RGBA")
    font = ImageFont.load_default()

    left_padding = 8
    top_padding = 8
    line_spacing = 4
    inner_padding = 8

    text_boxes = [draw.textbbox((0, 0), line, font=font) for line in lines]
    text_width = max((box[2] - box[0]) for box in text_boxes)
    text_height = sum((box[3] - box[1]) for box in text_boxes) + line_spacing * (len(lines) - 1)

    banner_right = left_padding + text_width + inner_padding * 2
    banner_bottom = top_padding + text_height + inner_padding * 2

    draw.rectangle(
        [(left_padding, top_padding), (banner_right, banner_bottom)],
        fill=(0, 0, 0, 170),
    )

    current_y = top_padding + inner_padding
    for line, box in zip(lines, text_boxes):
        draw.text((left_padding + inner_padding, current_y), line, fill=(255, 255, 255, 255), font=font)
        current_y += (box[3] - box[1]) + line_spacing

    return np.asarray(image)


class _ResolvedCityPixel(NamedTuple):
    name: str
    row: int
    col: int


_LON_COORD_CANDIDATES = ("lon", "x", "longitude")
_LAT_COORD_CANDIDATES = ("lat", "y", "latitude")


def _resolve_spatial_coord_names(data_array) -> tuple[str, str] | None:
    """
    Find the (lon_name, lat_name) coordinate pair on a reprojected
    DataArray. The reprojection backend names them "lon"/"lat" for
    geographic targets (e.g. EPSG:4326, this DAG's default) and "x"/"y" for
    projected targets (defair_ops rioxarray_backend.py:
    _build_reprojected_coordinates, target_crs.is_geographic branch).
    Returns None if neither pair is present.
    """
    lon_name = next((c for c in _LON_COORD_CANDIDATES if c in data_array.coords), None)
    lat_name = next((c for c in _LAT_COORD_CANDIDATES if c in data_array.coords), None)
    if lon_name is None or lat_name is None:
        return None
    return lon_name, lat_name


def _local_grid_step(grid: np.ndarray, axis: int) -> np.ndarray:
    """
    Local per-axis grid spacing at every cell: the adjacent-cell diff,
    edge-padded by replication so boundary cells inherit their nearest
    interior step rather than collapsing to zero. Reduces to a constant
    step on a regular grid (matching a global-step computation) and adapts
    to local cell size on a curvilinear grid. Shared by _resolve_city_pixels
    and _resolve_border_line_pixels.
    """
    if grid.shape[axis] < 2:
        return np.full(grid.shape, np.inf)
    diffs = np.abs(np.diff(grid, axis=axis))
    pad_width = [(0, 0), (0, 0)]
    pad_width[axis] = (0, 1)
    return np.pad(diffs, pad_width, mode="edge")


def _resolve_city_pixels(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    cities: Sequence[CityCoordinate],
) -> list[_ResolvedCityPixel]:
    """
    Resolve each city's nearest (row, col) grid index once, before the
    per-frame loop (the grid is static across frames). x_coords/y_coords are
    the DataArray's longitude/latitude coordinate arrays (named "lon"/"lat"
    or "x"/"y" depending on the reprojection target — see
    _resolve_spatial_coord_names). They may be 1-D axis vectors (a regular,
    axis-separable raster — today's EPSG:4326 default) or 2-D curvilinear
    fields sharing the data's (y, x) dims (e.g. a polar-stereographic or
    other non-separable reprojection target). Data dims are (y, x), so
    values[row, col] corresponds to lat/lon grid[row, col].

    A city is skipped if its nearest grid cell is farther than one local
    grid step away in either axis — i.e. it falls outside this render's
    actual AOI extent (the reprojection bbox is a user-settable DAG param,
    so a city's nominal coverage isn't guaranteed to match any given
    render).
    """
    if x_coords.size == 0 or y_coords.size == 0:
        return []

    if x_coords.ndim == 1 and y_coords.ndim == 1:
        lon_grid, lat_grid = np.meshgrid(x_coords, y_coords, indexing="xy")
    else:
        lon_grid, lat_grid = x_coords, y_coords

    lon_step = _local_grid_step(lon_grid, axis=1)
    lat_step = _local_grid_step(lat_grid, axis=0)

    resolved: list[_ResolvedCityPixel] = []
    for city in cities:
        distance_sq = (lat_grid - city.lat) ** 2 + (lon_grid - city.lon) ** 2
        row, col = np.unravel_index(np.argmin(distance_sq), distance_sq.shape)
        row, col = int(row), int(col)
        if (
            abs(lon_grid[row, col] - city.lon) > lon_step[row, col]
            or abs(lat_grid[row, col] - city.lat) > lat_step[row, col]
        ):
            continue
        resolved.append(_ResolvedCityPixel(name=city.name, row=row, col=col))
    return resolved


def _resolve_border_line_pixels(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    border_lines: Sequence[Sequence[tuple[float, float]]],
) -> list[list[tuple[int, int]]]:
    """
    Resolve each border-line vertex's nearest (row, col) grid index once,
    before the per-frame loop (borders are static across frames, exactly
    like city pixels — see _resolve_city_pixels). x_coords/y_coords are the
    same lon/lat coordinate arrays described there (1-D axis-separable or
    2-D curvilinear).

    Unlike _resolve_city_pixels' per-point skip, a border-line vertex that
    falls outside this render's AOI/grid tolerance must *break* the line
    rather than silently drop the vertex — otherwise the next in-tolerance
    vertex after a dropped one would be linked directly to the prior
    in-tolerance vertex with a straight line cutting across the whole frame.
    Each returned polyline has >= 2 points; input lines are split into as
    many output polylines as needed at out-of-bounds crossings.

    Nearest-vertex lookup uses a KD-tree over the grid's unit-sphere
    coordinates (via _lonlat_deg_to_unit_vectors, the same great-circle
    approach _nearest_healpix_pixel_grid uses), queried once per line's full
    vertex batch — a per-vertex full-grid argmin (as in _resolve_city_pixels,
    fine for a few dozen cities) would be far too slow across the thousands
    of vertices in a Natural Earth boundary-lines layer.
    """
    if x_coords.size == 0 or y_coords.size == 0:
        return []

    if x_coords.ndim == 1 and y_coords.ndim == 1:
        lon_grid, lat_grid = np.meshgrid(x_coords, y_coords, indexing="xy")
    else:
        lon_grid, lat_grid = x_coords, y_coords

    lon_step = _local_grid_step(lon_grid, axis=1)
    lat_step = _local_grid_step(lat_grid, axis=0)

    from scipy.spatial import cKDTree

    grid_xyz = _lonlat_deg_to_unit_vectors(lon_grid.ravel(), lat_grid.ravel())
    # Grid points lie on a 2-D manifold (a sphere surface) embedded in 3-D:
    # cKDTree's default compact_nodes/balanced_tree construction degrades to
    # near-linear query time on this shape (measured 126s to resolve a full
    # border+coastline set on a ~1M-cell grid). These kwargs, plus workers=-1
    # below, bring the same query down to ~0.05s with identical results.
    tree = cKDTree(grid_xyz, balanced_tree=False, compact_nodes=False)

    resolved_polylines: list[list[tuple[int, int]]] = []
    for line in border_lines:
        if len(line) < 2:
            continue
        lons = np.array([point[0] for point in line])
        lats = np.array([point[1] for point in line])
        _, flat_indices = tree.query(_lonlat_deg_to_unit_vectors(lons, lats), workers=-1)
        rows, cols = np.unravel_index(flat_indices, lon_grid.shape)

        current_segment: list[tuple[int, int]] = []
        for i in range(len(line)):
            row, col = int(rows[i]), int(cols[i])
            within_tolerance = (
                abs(lon_grid[row, col] - lons[i]) <= lon_step[row, col]
                and abs(lat_grid[row, col] - lats[i]) <= lat_step[row, col]
            )
            if within_tolerance:
                current_segment.append((row, col))
            else:
                if len(current_segment) >= 2:
                    resolved_polylines.append(current_segment)
                current_segment = []
        if len(current_segment) >= 2:
            resolved_polylines.append(current_segment)

    return resolved_polylines


def _sample_city_temperatures_celsius(
    values: np.ndarray, resolved_city_pixels: list[_ResolvedCityPixel]
) -> list[tuple[str, int, int, float]]:
    """
    Sample the raw (pre-colormap, pre-clip) Kelvin value at each resolved
    pixel from the already-loaded 2D frame array and convert to Celsius.
    Skips a city if its sample is NaN (off-disk / no data this frame).

    Returns (name, row, col, celsius) tuples — row/col are passed through so
    the drawing function doesn't need to re-resolve them.
    """
    samples: list[tuple[str, int, int, float]] = []
    for city in resolved_city_pixels:
        kelvin = values[city.row, city.col]
        if not np.isfinite(kelvin):
            continue
        samples.append((city.name, city.row, city.col, float(kelvin) - 273.15))
    return samples


def _overlay_city_temperatures(frame: np.ndarray, samples: list[tuple[str, int, int, float]]) -> np.ndarray:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional runtime deps
        raise RuntimeError(
            "Pillow is required to render city-temperature overlays. Install pillow to enable overlays."
        ) from exc

    image = Image.fromarray(frame, mode="RGB")
    draw = ImageDraw.Draw(image, mode="RGBA")
    font = ImageFont.load_default()

    marker_radius = 3
    for name, row, col, celsius in samples:
        x, y = int(col), int(row)
        draw.ellipse(
            [(x - marker_radius, y - marker_radius), (x + marker_radius, y + marker_radius)],
            fill=(255, 80, 0, 255),
            outline=(0, 0, 0, 255),
        )
        label = f"{name} {celsius:.0f}°C"
        text_x, text_y = x + marker_radius + 3, y - marker_radius - 3
        # Cheap 1px black halo so the label stays legible over any colormap.
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            draw.text((text_x + dx, text_y + dy), label, fill=(0, 0, 0, 255), font=font)
        draw.text((text_x, text_y), label, fill=(255, 255, 255, 255), font=font)

    return np.asarray(image)


def _overlay_country_borders(
    frame: np.ndarray, resolved_border_pixels: list[list[tuple[int, int]]]
) -> np.ndarray:
    try:
        from PIL import Image, ImageDraw
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional runtime deps
        raise RuntimeError(
            "Pillow is required to render country-border overlays. Install pillow to enable overlays."
        ) from exc

    image = Image.fromarray(frame, mode="RGB")
    draw = ImageDraw.Draw(image, mode="RGBA")

    for segment in resolved_border_pixels:
        points = [(col, row) for row, col in segment]  # PIL expects (x, y) = (col, row)
        draw.line(points, fill=(220, 220, 220, 160), width=1)

    return np.asarray(image)


def open_s3_zarr_dataset(
    *,
    bucket_name: str,
    prefix: str,
    endpoint_url: str,
    access_key_id: str,
    secret_access_key: str,
):
    import s3fs
    import xarray as xr

    normalized_prefix = prefix.strip("/")
    root = f"{bucket_name}/{normalized_prefix}" if normalized_prefix else bucket_name

    fs = s3fs.S3FileSystem(
        key=access_key_id,
        secret=secret_access_key,
        client_kwargs={"endpoint_url": endpoint_url},
    )
    store = s3fs.S3Map(root=root, s3=fs, check=False)
    return xr.open_zarr(store, consolidated=True)


def resolve_data_variable(dataset, preferred_name: str = "ch9"):
    if preferred_name in dataset.data_vars:
        return dataset[preferred_name]

    data_var_names = list(dataset.data_vars)
    if not data_var_names:
        raise ValueError("No data variables found in dataset")

    return dataset[data_var_names[0]]


def _lonlat_deg_to_unit_vectors(lon_deg: np.ndarray, lat_deg: np.ndarray) -> np.ndarray:
    """
    Convert lon/lat (degrees) to unit vectors on the sphere, so nearest-
    neighbour lookups use great-circle distance instead of raw degree-space
    distance (which breaks down across the antimeridian and near the poles).
    """
    lon_rad = np.radians(lon_deg)
    lat_rad = np.radians(lat_deg)
    cos_lat = np.cos(lat_rad)
    return np.stack(
        [cos_lat * np.cos(lon_rad), cos_lat * np.sin(lon_rad), np.sin(lat_rad)],
        axis=-1,
    )


def _nearest_healpix_pixel_grid(
    healpix_lon_deg: np.ndarray,
    healpix_lat_deg: np.ndarray,
    lon_axis: np.ndarray,
    lat_axis: np.ndarray,
) -> np.ndarray:
    """
    For every cell of a regular (lat_axis x lon_axis) display grid, find the
    index into the HEALPix pixel arrays (healpix_lon_deg/healpix_lat_deg,
    i.e. the "healpix_index" dim) of the nearest HEALPix pixel centre.

    Returns an array of shape (len(lat_axis), len(lon_axis)) of indices.
    """
    from scipy.spatial import cKDTree

    tree = cKDTree(_lonlat_deg_to_unit_vectors(healpix_lon_deg, healpix_lat_deg))

    lon_grid, lat_grid = np.meshgrid(lon_axis, lat_axis, indexing="xy")
    grid_xyz = _lonlat_deg_to_unit_vectors(lon_grid.ravel(), lat_grid.ravel())

    _, nearest_indices = tree.query(grid_xyz)
    return nearest_indices.reshape(lat_grid.shape)


def reproject_healpix_dataarray_to_raster(
    data_array,
    *,
    bounds: tuple[float, float, float, float],
    resolution_degrees: float | None = None,
):
    """
    Scatter a HEALPix-indexed DataArray onto a regular lat/lon display
    raster, via nearest-HEALPix-pixel lookup.

    HEALPix cells are unstructured (no inherent row/col layout), but
    create_mp4_from_dataarray needs a 2-D raster to draw frames from. Each
    output grid cell is assigned the value of its nearest HEALPix pixel
    centre (nearest on the sphere — see _nearest_healpix_pixel_grid). The
    lon/lat grid step defaults to the HEALPix grid's own native angular
    resolution (derived from nside), so the raster neither over- nor
    under-samples the source data.

    AstropyHealpixBackend's "lat" coordinate is *authalic* latitude (the
    equal-area latitude HEALPix requires on an ellipsoid — CF-1.13), not
    ordinary geodetic latitude. The display grid built from `bounds` (and
    everything overlaid on top of it, e.g. Natural Earth country borders
    and city markers) is geodetic, so the HEALPix pixel latitudes are
    converted to geodetic before the nearest-pixel match below. Without
    this, imagery is shifted north/south by up to ~0.2 degrees relative to
    its own coordinate labels, while borders/markers — placed by trusting
    those labels — stay put, producing a visible misalignment.

    Args:
        data_array: DataArray with a "healpix_index" dim and lon/lat
            coordinates on that dim (as produced by
            defair_ops's AstropyHealpixBackend reprojection).
        bounds: Display grid extent (lon_min, lat_min, lon_max, lat_max) —
            typically the same AOI bounds used for the upstream reprojection.
        resolution_degrees: Output grid spacing in degrees. Defaults to the
            HEALPix grid's native pixel resolution when not given.

    Returns:
        DataArray with "healpix_index" replaced by ("y", "x") dims and
        regular 1-D "lon"/"lat" coordinates on "x"/"y" respectively.
    """
    if "healpix_index" not in data_array.dims:
        raise ValueError(
            "reproject_healpix_dataarray_to_raster requires a 'healpix_index' "
            f"dim, got dims={data_array.dims!r}"
        )

    coord_names = _resolve_spatial_coord_names(data_array)
    if coord_names is None:
        raise ValueError(
            "HEALPix DataArray is missing lon/lat coordinates on 'healpix_index'"
        )
    lon_name, lat_name = coord_names

    npix = int(data_array.sizes["healpix_index"])
    nside = round(math.sqrt(npix / 12))
    if nside <= 0 or 12 * nside * nside != npix:
        raise ValueError(
            f"'healpix_index' size {npix} is not a valid HEALPix pixel count (12 * nside^2)"
        )

    if resolution_degrees is None:
        # Native HEALPix angular resolution: sqrt(pixel solid angle).
        resolution_degrees = math.degrees(math.sqrt(4 * math.pi / npix))

    lon_min, lat_min, lon_max, lat_max = bounds
    n_lon = max(2, round((lon_max - lon_min) / resolution_degrees) + 1)
    n_lat = max(2, round((lat_max - lat_min) / resolution_degrees) + 1)
    lon_axis = np.linspace(lon_min, lon_max, n_lon)
    lat_axis = np.linspace(lat_max, lat_min, n_lat)  # north-to-south, so row 0 is the top of the image

    # defair_ops has no public geodetic<->authalic conversion; this reaches
    # into its private backend module to reuse the exact Karney series that
    # produced the authalic values, guaranteeing an exact round-trip.
    from defair_ops.transformations.reprojection.backends._authalic import (
        geodetic_to_authalic,
    )

    healpix_lat_geodetic = geodetic_to_authalic(
        np.asarray(data_array[lat_name].values), inverse=True
    )

    nearest_pixel_grid = _nearest_healpix_pixel_grid(
        np.asarray(data_array[lon_name].values),
        healpix_lat_geodetic,
        lon_axis,
        lat_axis,
    )

    import xarray as xr

    index_da = xr.DataArray(nearest_pixel_grid, dims=("y", "x"))
    raster = data_array.isel({"healpix_index": index_da})
    raster = raster.drop_vars(
        [name for name in (lon_name, lat_name, "healpix_index") if name in raster.coords]
    )
    return raster.assign_coords(lon=("x", lon_axis), lat=("y", lat_axis))


def compute_display_range(values: np.ndarray, low_percentile: float = 2.0, high_percentile: float = 98.0) -> tuple[float, float]:
    finite_values = values[np.isfinite(values)]
    if finite_values.size == 0:
        raise ValueError("Cannot compute display range from only NaN/inf values")

    vmin, vmax = np.percentile(finite_values, [low_percentile, high_percentile]).astype(float)
    if not np.isfinite(vmin) or not np.isfinite(vmax):
        raise ValueError("Computed non-finite display range")

    if vmin == vmax:
        epsilon = 1e-6 if vmin == 0 else abs(vmin) * 1e-6
        return float(vmin - epsilon), float(vmax + epsilon)

    return float(vmin), float(vmax)


def _to_uint8_rgb_frame(values: np.ndarray, vmin: float, vmax: float, colormap_name: str) -> np.ndarray:
    from matplotlib import colormaps

    clipped = np.clip(values, vmin, vmax)
    normalized = (clipped - vmin) / (vmax - vmin)
    normalized = np.nan_to_num(normalized, nan=0.0, posinf=1.0, neginf=0.0)

    rgba = colormaps[colormap_name](normalized)
    rgb = (rgba[..., :3] * 255.0).astype(np.uint8)
    return rgb


def create_mp4_from_dataarray(
    data_array,
    output_file_path: str,
    *,
    fps: int = 4,
    frame_stride: int = 1,
    max_frames: int | None = None,
    colormap_name: str = "inferno",
    low_percentile: float = 2.0,
    high_percentile: float = 98.0,
    annotation_metadata: dict[str, Any] | None = None,
    city_temperature_overlay: Sequence[CityCoordinate] | None = None,
    country_border_lines: Sequence[Sequence[tuple[float, float]]] | None = None,
) -> dict:
    if "time" not in data_array.dims:
        raise ValueError(f"DataArray must contain a 'time' dimension, got dims={data_array.dims}")
    spatial_dims = [dim for dim in data_array.dims if dim != "time"]
    if len(spatial_dims) != 2:
        raise ValueError(
            "create_mp4_from_dataarray renders a 2-D raster per frame, but got "
            f"non-time dims={spatial_dims!r} (from data_array.dims={data_array.dims!r}). "
            "Unstructured/cell-indexed data (e.g. a HEALPix grid) has no (row, col) "
            "raster to draw — reproject it onto a 2-D display grid before calling "
            "this function."
        )
    if frame_stride < 1:
        raise ValueError("frame_stride must be >= 1")

    total_timesteps = int(data_array.sizes["time"])
    time_indexes = list(range(0, total_timesteps, frame_stride))
    if max_frames is not None:
        time_indexes = time_indexes[:max_frames]

    if not time_indexes:
        raise ValueError("No frames selected for video generation")

    sample_count = min(len(time_indexes), 16)
    sample_values = data_array.isel(time=time_indexes[:sample_count]).load().values
    vmin, vmax = compute_display_range(
        sample_values,
        low_percentile=low_percentile,
        high_percentile=high_percentile,
    )

    output_file = Path(output_file_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if imageio is None:
        raise RuntimeError(
            "imageio is required to create MP4 output. Install imageio and imageio-ffmpeg."
        )

    resolved_city_pixels: list[_ResolvedCityPixel] = []
    resolved_border_pixels: list[list[tuple[int, int]]] = []
    if city_temperature_overlay or country_border_lines:
        coord_names = _resolve_spatial_coord_names(data_array)
        if coord_names is not None:
            lon_name, lat_name = coord_names
            if city_temperature_overlay:
                resolved_city_pixels = _resolve_city_pixels(
                    data_array[lon_name].values, data_array[lat_name].values, city_temperature_overlay
                )
            if country_border_lines:
                resolved_border_pixels = _resolve_border_line_pixels(
                    data_array[lon_name].values, data_array[lat_name].values, country_border_lines
                )

    try:
        with imageio.get_writer(str(output_file), fps=fps, codec="libx264", format="FFMPEG") as writer:
            for idx in time_indexes:
                values = data_array.isel(time=idx).load().values
                frame = _to_uint8_rgb_frame(values, vmin=vmin, vmax=vmax, colormap_name=colormap_name)
                if resolved_border_pixels:
                    frame = _overlay_country_borders(frame, resolved_border_pixels)
                if resolved_city_pixels:
                    frame = _overlay_city_temperatures(
                        frame, _sample_city_temperatures_celsius(values, resolved_city_pixels)
                    )
                if annotation_metadata is not None:
                    frame = _overlay_annotation_banner(
                        frame,
                        _build_annotation_lines(
                            time_value=data_array["time"].values[idx],
                            annotation_metadata=annotation_metadata,
                        ),
                    )
                writer.append_data(frame)
    except Exception as exc:  # pragma: no cover - depends on system ffmpeg support
        raise RuntimeError(
            "Failed to encode MP4. Ensure ffmpeg is available or install imageio-ffmpeg."
        ) from exc

    return {
        "video_path": str(output_file),
        "frame_count": len(time_indexes),
        "fps": fps,
        "vmin": vmin,
        "vmax": vmax,
    }
