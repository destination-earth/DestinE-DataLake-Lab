from __future__ import annotations

from datetime import date, datetime, timedelta
from collections.abc import Mapping
import re
from typing import Any

from eodag import EODataAccessGateway


def _normalize_collection_id(value: str) -> str:
    """Normalize collection IDs for stable case-insensitive matching."""
    return value.strip().upper()


def _get_provider_products_config(
    dag: EODataAccessGateway,
    provider: str,
) -> dict[str, dict[str, Any]]:
    """Return provider products mapping from EODAG configuration."""
    provider_obj = dag.providers.get(provider)
    if provider_obj is None:
        raise ValueError(
            f"Provider '{provider}' is not available in EODataAccessGateway."
        )

    config = getattr(provider_obj, "config", None)
    products = getattr(config, "products", None)
    if not isinstance(products, dict):
        raise ValueError(f"Provider '{provider}' has no products configuration.")

    return products


def _iter_provider_collection_ids(product_config: dict[str, Any]) -> list[str]:
    """Extract provider-specific collection ids from one product config entry."""
    provider_collection = product_config.get("_collection")
    if isinstance(provider_collection, str):
        return [provider_collection]
    if isinstance(provider_collection, list):
        return [value for value in provider_collection if isinstance(value, str)]
    return []


def _build_provider_to_normalized_map(
    products: dict[str, dict[str, Any]],
) -> dict[str, set[str]]:
    """Build reverse map: provider collection id -> normalized EODAG collection ids."""
    reverse_map: dict[str, set[str]] = {}

    for normalized_collection_id, product_config in products.items():
        if not isinstance(product_config, dict):
            continue
        provider_collection_ids = _iter_provider_collection_ids(product_config)
        for provider_collection_id in provider_collection_ids:
            key = _normalize_collection_id(provider_collection_id)
            reverse_map.setdefault(key, set()).add(normalized_collection_id)

    return reverse_map


def _build_suggestions(
    needle: str, haystack: list[str], max_items: int = 5
) -> list[str]:
    """Return lightweight suggestions for unknown provider collection ids."""
    suggestions: list[str] = []
    needle_upper = _normalize_collection_id(needle)

    for candidate in haystack:
        candidate_upper = _normalize_collection_id(candidate)
        if needle_upper in candidate_upper or candidate_upper in needle_upper:
            suggestions.append(candidate)

    if not suggestions:
        suggestions = haystack[:max_items]

    return suggestions[:max_items]


def find_eodag_collection_id_by_dedl_id(
    dedl_collection_id: str,
    dag: EODataAccessGateway | None = None,
    provider: str = "dedl",
) -> str:
    """
    Resolve a provider collection id to the normalized EODAG collection id.

    Example:
    EO.ESA.DAT.SENTINEL-2.MSI.L2A -> S2_MSI_L2A
    """
    if not isinstance(dedl_collection_id, str) or not dedl_collection_id.strip():
        raise ValueError("dedl_collection_id must be a non-empty string.")

    eodag_dag = dag or EODataAccessGateway()
    products = _get_provider_products_config(eodag_dag, provider)
    reverse_map = _build_provider_to_normalized_map(products)

    lookup_key = _normalize_collection_id(dedl_collection_id)
    matches = sorted(reverse_map.get(lookup_key, set()))

    if len(matches) == 1:
        return matches[0]

    if len(matches) > 1:
        raise ValueError(
            "Ambiguous mapping for provider collection id "
            f"'{dedl_collection_id}'. Matches: {matches}"
        )

    suggestions = _build_suggestions(dedl_collection_id, sorted(reverse_map.keys()))
    raise ValueError(
        "No normalized EODAG collection id found for provider collection id "
        f"'{dedl_collection_id}'. Suggestions: {suggestions}"
    )


def find_dedl_collection_by_eodag_id(
    eodag_id: str,
    dag: EODataAccessGateway | None = None,
    provider: str = "dedl",
) -> list[dict[str, str]]:
    """
    Find provider collection ids associated with an EODAG collection id.

    Returns a list of dictionaries for easy DAG logging/serialization.
    """
    if not isinstance(eodag_id, str) or not eodag_id.strip():
        raise ValueError("eodag_id must be a non-empty string.")

    query = eodag_id.strip().lower()
    eodag_dag = dag or EODataAccessGateway()
    products = _get_provider_products_config(eodag_dag, provider)

    results: list[dict[str, str]] = []
    for normalized_collection_id, product_config in products.items():
        if query not in normalized_collection_id.lower():
            continue

        if not isinstance(product_config, dict):
            continue

        provider_collection_ids = _iter_provider_collection_ids(product_config)
        if not provider_collection_ids:
            continue

        for provider_collection_id in provider_collection_ids:
            results.append(
                {
                    "eodag_collection_id": normalized_collection_id,
                    "provider_collection_id": provider_collection_id,
                }
            )

    return results


def get_dedl_collection_info(
    collection_id: str,
    dag: EODataAccessGateway | None = None,
    provider: str = "dedl",
) -> dict[str, str]:
    """Return one resolved DEDL collection mapping enriched with normalized id."""
    normalized_id = find_eodag_collection_id_by_dedl_id(
        collection_id,
        dag=dag,
        provider=provider,
    )
    return {
        "provider_collection_id": collection_id,
        "eodag_collection_id": normalized_id,
    }


def _collection_to_dict(collection_obj: Any) -> dict[str, Any]:
    """Serialize an EODAG collection model to a plain dictionary."""
    model_dump = getattr(collection_obj, "model_dump", None)
    if callable(model_dump):
        serialized = model_dump()
        if isinstance(serialized, dict):
            return serialized

    if isinstance(collection_obj, dict):
        return collection_obj

    for attr in ("__dict__",):
        value = getattr(collection_obj, attr, None)
        if isinstance(value, dict):
            return value

    raise ValueError("Collection object cannot be serialized to a dictionary.")


def get_eodag_collection_info(
    eodag_collection_id: str,
    dag: EODataAccessGateway | None = None,
    provider: str = "dedl",
) -> dict[str, Any]:
    """Return collection metadata for one normalized EODAG collection id."""
    if not isinstance(eodag_collection_id, str) or not eodag_collection_id.strip():
        raise ValueError("eodag_collection_id must be a non-empty string.")

    eodag_dag = dag or EODataAccessGateway()
    collections = eodag_dag.list_collections(provider=provider)
    lookup_id = _normalize_collection_id(eodag_collection_id)

    collection_obj = next(
        (
            collection
            for collection in collections
            if _normalize_collection_id(str(getattr(collection, "id", ""))) == lookup_id
        ),
        None,
    )

    if collection_obj is None:
        raise ValueError(
            f"Collection not found in provider '{provider}': {eodag_collection_id}"
        )

    return _collection_to_dict(collection_obj)


def _to_iso_date(value: Any) -> str:
    """Normalize datetime/date-like values to YYYY-MM-DD."""
    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()
    if not text or text.lower() in {"none", "null"}:
        raise ValueError("Start date is empty in collection metadata.")

    if len(text) >= 10:
        prefix = text[:10]
        try:
            return date.fromisoformat(prefix).isoformat()
        except ValueError:
            pass

    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.date().isoformat()
    except ValueError as exc:
        raise ValueError(f"Invalid collection start date format: {value}") from exc


def _normalize_optional_iso_date(value: Any) -> str | None:
    """Return normalized ISO date when value is present, else None."""
    if value is None:
        return None

    try:
        return _to_iso_date(value)
    except ValueError:
        return None


def shift_iso_date(value: Any, days: int) -> str:
    """Return an ISO date offset by the requested number of days."""
    normalized_date = _to_iso_date(value)
    return (date.fromisoformat(normalized_date) + timedelta(days=days)).isoformat()


def _is_sequence(value: Any) -> bool:
    """Return True for list/tuple values used as JSON-like arrays."""
    return isinstance(value, (list, tuple))


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    """Return a mapping view for dict-like or model-like values."""
    if isinstance(value, Mapping):
        return value

    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        serialized = model_dump()
        if isinstance(serialized, Mapping):
            return serialized

    value_dict = getattr(value, "__dict__", None)
    if isinstance(value_dict, Mapping):
        return value_dict

    return None


def _extract_collection_start_date(collection_info: dict[str, Any]) -> str:
    """Extract the collection start date from common STAC-like metadata paths."""
    for extent_key in ("extent", "extents"):
        extent = _as_mapping(collection_info.get(extent_key))
        if extent is None:
            continue

        temporal = _as_mapping(extent.get("temporal"))
        if temporal is not None:
            intervals = temporal.get("interval")
            if _is_sequence(intervals) and intervals:
                first_interval = intervals[0]
                if _is_sequence(first_interval) and first_interval:
                    start_value = _normalize_optional_iso_date(first_interval[0])
                    if start_value is not None:
                        return start_value

    temporal_extents = collection_info.get("temporal_extents")
    if _is_sequence(temporal_extents) and temporal_extents:
        first_interval = temporal_extents[0]
        if _is_sequence(first_interval) and first_interval:
            start_value = _normalize_optional_iso_date(first_interval[0])
            if start_value is not None:
                return start_value

    start_datetime = collection_info.get("start_datetime")
    start_value = _normalize_optional_iso_date(start_datetime)
    if start_value is not None:
        return start_value

    raise ValueError("Collection start date not found in metadata.")


def _extract_collection_bbox(
    collection_info: dict[str, Any],
) -> tuple[float, float, float, float]:
    """Extract [minx, miny, maxx, maxy] bbox from common collection metadata paths."""
    bbox_candidate: Any = None

    for extent_key in ("extent", "extents"):
        extent = _as_mapping(collection_info.get(extent_key))
        if extent is None:
            continue

        spatial = _as_mapping(extent.get("spatial"))
        if spatial is None:
            continue

        bbox = spatial.get("bbox")
        if _is_sequence(bbox) and bbox:
            if _is_sequence(bbox[0]):
                bbox_candidate = bbox[0]
            else:
                bbox_candidate = bbox
            break

    if bbox_candidate is None:
        root_bbox = collection_info.get("bbox")
        if _is_sequence(root_bbox) and root_bbox:
            if _is_sequence(root_bbox[0]):
                bbox_candidate = root_bbox[0]
            else:
                bbox_candidate = root_bbox

    if not _is_sequence(bbox_candidate) or len(bbox_candidate) != 4:
        raise ValueError("Collection bbox not found in metadata.")

    try:
        minx = float(bbox_candidate[0])
        miny = float(bbox_candidate[1])
        maxx = float(bbox_candidate[2])
        maxy = float(bbox_candidate[3])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Collection bbox is invalid: {bbox_candidate}") from exc

    return (minx, miny, maxx, maxy)


def _extract_collection_end_date(collection_info: dict[str, Any]) -> str:
    """Extract collection end date from STAC temporal interval, or default to today."""
    for extent_key in ("extent", "extents"):
        extent = _as_mapping(collection_info.get(extent_key))
        if extent is None:
            continue

        temporal = _as_mapping(extent.get("temporal"))
        if temporal is None:
            continue

        intervals = temporal.get("interval")
        if not (_is_sequence(intervals) and intervals):
            continue

        first_interval = intervals[0]
        if not (_is_sequence(first_interval) and len(first_interval) >= 2):
            continue

        end_value = _normalize_optional_iso_date(first_interval[1])
        if end_value is not None:
            return end_value

    end_datetime = collection_info.get("end_datetime")
    end_value = _normalize_optional_iso_date(end_datetime)
    if end_value is not None:
        return end_value

    return date.today().isoformat()


def get_collection_search_params(collection_info: dict[str, Any]) -> dict[str, Any]:
    """Build search parameters from collection metadata.

    - start: collection start date
    - end: interval end date (or today if open-ended)
    - bbox: [minx, miny, maxx, maxy]
    - geom: polygon WKT derived from bbox
    """
    start_date = _extract_collection_start_date(collection_info)
    end_date = _extract_collection_end_date(collection_info)

    minx, miny, maxx, maxy = _extract_collection_bbox(collection_info)
    bbox = [minx, miny, maxx, maxy]
    geom = (
        f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, "
        f"{minx} {maxy}, {minx} {miny}))"
    )

    return {
        "start": start_date,
        "end": end_date,
        "bbox": bbox,
        "geom": geom,
    }


from pathlib import Path
import zipfile
from pathlib import Path
import zipfile


def clean_directory(dir_path: str) -> list[Path]:
    """
    Renames malformed EODAG file names (stray '", attachment' / quotes left
    over from a Content-Disposition header) so the files can be unzipped correctly.

    Returns only the files that were actually renamed.
    """
    dir_path = Path(dir_path)
    renamed_files = []

    for p in sorted(dir_path.iterdir()):
        if not p.is_file():
            continue

        new_name = p.name
        if '", attachment' in new_name:
            new_name = new_name.replace('", attachment', "")
        new_name = new_name.strip('"')

        if new_name == p.name:
            continue

        new_path = p.with_name(new_name)
        p.rename(new_path)
        renamed_files.append(new_path)

    return renamed_files


def extract_zip_files(paths: list[Path], overwrite: bool = True) -> list[Path]:
    """
    Extracts each given .zip file into a sibling folder named after its stem.
    Non-.zip paths are ignored.

    Returns the list of extraction target folders.
    """
    extracted_folders = []

    for p in paths:
        p = Path(p)
        if p.suffix != ".zip":
            continue

        extract_dir = p.with_name(p.stem)
        extract_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(p, "r") as z:
            if overwrite:
                z.extractall(extract_dir)
            else:
                for member in z.namelist():
                    target = extract_dir / member
                    if not target.exists():
                        z.extract(member, extract_dir)

        extracted_folders.append(extract_dir)

    return extracted_folders


from pathlib import Path
from typing import List


def get_files_with_extension(
    folder_paths: List[str], extension: str, recursive: bool = False
):
    """
    Collect all files with a given extension from multiple folders.

    Args:
        folder_paths: list of folder paths
        extension: file extension (e.g. '.zip', '.tif', 'tif' also allowed)
        recursive: if True, search subfolders too

    Returns:
        List[Path]: matching file paths
    """

    # normalize extension
    if not extension.startswith("."):
        extension = "." + extension

    results = []

    for folder in folder_paths:
        path = Path(folder)

        if not path.exists():
            continue

        if recursive:
            files = path.rglob(f"*{extension}")
        else:
            files = path.glob(f"*{extension}")

        results.extend([f for f in files if f.is_file()])

    return sorted(results)


_FILENAME_TIMESTAMP_PATTERNS = (
    re.compile(r"(20\d{2})(\d{2})(\d{2})[T_-]?(\d{2})(\d{2})(\d{2})"),
    re.compile(r"(20\d{2})-(\d{2})-(\d{2})[T_-]?(\d{2})(\d{2})(\d{2})"),
    re.compile(r"(20\d{2})(\d{2})(\d{2})"),
    re.compile(r"(20\d{2})-(\d{2})-(\d{2})"),
)


def _extract_timestamp_sort_token(file_name: str) -> str | None:
    """Extract a sortable timestamp token from a file name when possible."""
    for pattern in _FILENAME_TIMESTAMP_PATTERNS:
        match = pattern.search(file_name)
        if match is None:
            continue

        groups = match.groups()
        if len(groups) >= 6:
            return "".join(groups[:6])
        if len(groups) >= 3:
            return "".join(groups[:3]) + "000000"

    return None


def filename_timestamp_sort_key(file_path: str | Path) -> tuple[int, str, str]:
    """Return deterministic sort key using timestamp in filename, then lexical fallback."""
    path = Path(file_path)
    file_name = path.name
    token = _extract_timestamp_sort_token(file_name)
    if token is not None:
        return (0, token, file_name)
    return (1, "", file_name)


def filter_and_sort_nat_files(file_paths: list[str | Path]) -> list[Path]:
    """Keep only .nat files and sort deterministically by timestamp-like filename token."""
    nat_files = [Path(file_path) for file_path in file_paths if Path(file_path).suffix.lower() == ".nat"]
    return sorted(nat_files, key=filename_timestamp_sort_key)


from pathlib import Path
from typing import Union

def change_extension(file_path: Union[str, Path], new_extension: str) -> Path:
    """
    Change the extension of a single file path.

    Args:
        file_path: absolute or relative path
        new_extension: e.g. '.zarr' or 'zarr'

    Returns:
        Path: updated path
    """
    if not new_extension.startswith("."):
        new_extension = "." + new_extension

    return Path(file_path).with_suffix(new_extension)