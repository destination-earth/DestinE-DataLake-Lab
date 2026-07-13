from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np

from dedl.visualization.capital_cities import CityCoordinate

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


def _resolve_city_pixels(
    x_coords: np.ndarray,
    y_coords: np.ndarray,
    cities: Sequence[CityCoordinate],
) -> list[_ResolvedCityPixel]:
    """
    Resolve each city's nearest (row, col) grid index once, before the
    per-frame loop (the grid is static across frames). x_coords/y_coords are
    the DataArray's 1-D longitude/latitude coordinate arrays (named "lon"/
    "lat" or "x"/"y" depending on the reprojection target — see
    _resolve_spatial_coord_names); data dims are (y, x), so
    values[row, col] corresponds to (y_coords[row], x_coords[col]).

    A city is skipped if its nearest coordinate is farther than one grid
    step away in either axis — i.e. it falls outside this render's actual
    AOI extent (the reprojection bbox is a user-settable DAG param, so a
    city's nominal coverage isn't guaranteed to match any given render).
    """
    if x_coords.size == 0 or y_coords.size == 0:
        return []

    x_step = float(abs(x_coords[1] - x_coords[0])) if x_coords.size > 1 else float("inf")
    y_step = float(abs(y_coords[1] - y_coords[0])) if y_coords.size > 1 else float("inf")

    resolved: list[_ResolvedCityPixel] = []
    for city in cities:
        col = int(np.argmin(np.abs(x_coords - city.lon)))
        row = int(np.argmin(np.abs(y_coords - city.lat)))
        if abs(x_coords[col] - city.lon) > x_step or abs(y_coords[row] - city.lat) > y_step:
            continue
        resolved.append(_ResolvedCityPixel(name=city.name, row=row, col=col))
    return resolved


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
) -> dict:
    if "time" not in data_array.dims:
        raise ValueError(f"DataArray must contain a 'time' dimension, got dims={data_array.dims}")
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
    if city_temperature_overlay:
        coord_names = _resolve_spatial_coord_names(data_array)
        if coord_names is not None:
            lon_name, lat_name = coord_names
            resolved_city_pixels = _resolve_city_pixels(
                data_array[lon_name].values, data_array[lat_name].values, city_temperature_overlay
            )

    try:
        with imageio.get_writer(str(output_file), fps=fps, codec="libx264", format="FFMPEG") as writer:
            for idx in time_indexes:
                values = data_array.isel(time=idx).load().values
                frame = _to_uint8_rgb_frame(values, vmin=vmin, vmax=vmax, colormap_name=colormap_name)
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
