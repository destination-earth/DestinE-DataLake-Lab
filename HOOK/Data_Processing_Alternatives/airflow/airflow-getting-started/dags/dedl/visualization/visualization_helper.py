from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import imageio.v2 as imageio
except ModuleNotFoundError:  # pragma: no cover - depends on optional runtime deps
    imageio = None


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

    try:
        with imageio.get_writer(str(output_file), fps=fps, codec="libx264", format="FFMPEG") as writer:
            for idx in time_indexes:
                values = data_array.isel(time=idx).load().values
                frame = _to_uint8_rgb_frame(values, vmin=vmin, vmax=vmax, colormap_name=colormap_name)
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
