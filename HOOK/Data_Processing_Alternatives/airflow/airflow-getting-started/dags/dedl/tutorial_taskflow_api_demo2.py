#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

# [START tutorial]
# [START import_module]
import json
from datetime import timedelta
from typing import Any

import pendulum
from airflow.sdk import dag, get_current_context, task, Param
from airflow.sdk.definitions.param import DagParam
from dedl.tasks.common import show_params
from dedl.tasks.reporting import generate_run_report

# [END import_module]

from typing import Literal, TypedDict


class DownloadRecordDict(TypedDict):
    """Data contract: outcome of a single per-product download attempt"""
    product_id: str
    title: str
    status: Literal["success", "failed"]
    duration_seconds: float
    error: str | None
    downloaded_path: str | None


class SearchResultsDict(TypedDict):
    """Data contract: extract task output"""
    num_search_results: int
    downloaded_nat_files: list[str]
    collection_id: str
    bbox: tuple[float, float, float, float]
    download_records: list[DownloadRecordDict]
    num_downloads_succeeded: int
    num_downloads_failed: int


class TransformOneResultDict(TypedDict):
    """Data contract: transform_one task output (single .nat file)"""
    zarr_path: str
    nat_file: str
    duration_seconds: float


class TransformResultsDict(TypedDict):
    """Data contract: concatenate_zarr_files task output"""
    total_num_zarr_files: int
    concatenated_zarr_path: str
    channels: list[str]
    reprojection_bounds: tuple[float, float, float, float]
    reprojection_crs: str
    resampling: str
    resolution: float
    resolution_unit: str


class VisualiseOneResultDict(TypedDict):
    """Data contract: visualise_one task output (single channel)"""
    channel: str
    video_path: str
    frame_count: int
    fps: int
    video_s3_uri: str
    duration_seconds: float


class LoadResultDict(TypedDict):
    """Data contract: load task output (extends S3 upload result)"""
    success: bool
    s3_uri: str
    destination_prefix: str
    channels: list[str]
    reprojection_bounds: tuple[float, float, float, float]
    reprojection_crs: str
    resampling: str
    resolution: float
    resolution_unit: str


def _resolve_runtime_param(value: Any) -> Any:
    if isinstance(value, DagParam):
        return value.resolve(get_current_context())
    return value


def _get_output_base_dir() -> str:
    """
    Retrieve the base output directory for EODAG downloads.

    Reads from EODAG__DEDL__DOWNLOAD__OUTPUT_DIR environment variable.
    Raises ValueError if not set or empty.

    Note (portability): every task in this DAG run reads/writes this same path
    to hand off .nat/.zarr/.mp4 files between tasks. That only works if the
    value resolves to identical, shared, writable storage across every task
    instance of the run. True today under LocalExecutor on a single VM. Under
    CeleryExecutor/KubernetesExecutor this requires a shared ReadWriteMany PVC
    mounted at this same path on every worker/task pod (see
    airflow-kubernetes/helm/pvc-role.yml for the RBAC scaffolding for that). The
    fully portable alternative is routing every intermediate artifact through S3
    between tasks and running tasks via @task.kubernetes (see
    airflow-kubernetes-dags/README.md) — a larger follow-up change, not required
    for LocalExecutor/single-VM deployments.

    Returns:
        str: The base directory path (e.g., /home/eouser/eodag_downloads/msg_hrseviri)
    """
    import os
    base_dir = os.environ.get("EODAG__DEDL__DOWNLOAD__OUTPUT_DIR", "").strip()
    if not base_dir:
        raise ValueError(
            "EODAG__DEDL__DOWNLOAD__OUTPUT_DIR environment variable not set. "
            "Please set it to the output directory for EODAG downloads."
        )
    return base_dir


def _build_concatenated_zarr_path() -> str:
    """Build the path for the concatenated Zarr file."""
    base_dir = _get_output_base_dir()
    return f"{base_dir}/concatenated.zarr"


def _build_video_output_path(channel_name: str) -> str:
    """Build the local path for an MP4 output file for a given channel."""
    base_dir = _get_output_base_dir()
    return f"{base_dir}/{channel_name}_timelapse.mp4"


def _normalize_channel(value: str | DagParam) -> str:
    channel = str(_resolve_runtime_param(value)).strip()
    if not channel:
        raise ValueError("channel must be a non-empty string")
    if "/" in channel or "\\" in channel:
        raise ValueError("channel must not contain path separators")
    return channel


def _normalize_channels(value: list[str] | DagParam) -> list[str]:
    """
    Normalize and deduplicate a list of channel names.

    1. Resolves runtime DagParam if needed
    2. Validates each channel (no path separators, non-empty after strip)
    3. Deduplicates while preserving order of first occurrence

    Args:
        value: List of channel names or a DagParam that resolves to a list

    Returns:
        Deduplicated, normalized list of channel names

    Raises:
        TypeError: If value is not a list
        ValueError: If list is empty or any channel is invalid
    """
    resolved_value = _resolve_runtime_param(value)

    if isinstance(resolved_value, list):
        normalized_channels = [_normalize_channel(channel) for channel in resolved_value]
    else:
        raise TypeError("channels must be a list of strings")

    if not normalized_channels:
        raise ValueError("channels must contain at least one channel")

    deduplicated_channels: list[str] = []
    seen: set[str] = set()
    for channel in normalized_channels:
        if channel in seen:
            continue
        seen.add(channel)
        deduplicated_channels.append(channel)

    return deduplicated_channels


def _normalize_search_limit(value: int | DagParam) -> int:
    search_limit = int(_resolve_runtime_param(value))
    if search_limit <= 0:
        raise ValueError("search_limit must be greater than 0")
    return search_limit


def _build_visualization_annotation_metadata(
    search_results_dict: dict[str, Any],
    transform_results_dict: dict[str, Any],
    channel_name: str,
    channel_attrs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build metadata dictionary for annotating a visualization (MP4 time-lapse).

    Combines extraction metadata (collection_id, search bbox) with transformation
    metadata (reprojection CRS, resolution, resampling). Falls back to search bbox
    if reprojection bounds not available; defaults grid_mapping to 'spatial_ref'.

    Args:
        search_results_dict: From extract(); provides collection_id and search bbox
        transform_results_dict: From transform(); provides reprojection metadata
        channel_name: Channel identifier to annotate (e.g., 'ch9')
        channel_attrs: Optional per-channel xarray attributes (start_time, long_name, grid_mapping)

    Returns:
        dict: Annotation metadata with keys: collection_id, bbox (reprojection or search),
              channel_name, reprojection_crs, resampling, resolution, resolution_unit,
              and optionally channel_attrs fields (start_time, long_name, grid_mapping)
    """
    annotation_metadata = {
        "collection_id": search_results_dict["collection_id"],
        "bbox": transform_results_dict.get(
            "reprojection_bounds",
            search_results_dict["bbox"],
        ),
        "channel_name": channel_name,
        "reprojection_crs": transform_results_dict["reprojection_crs"],
        "resampling": transform_results_dict["resampling"],
        "resolution": transform_results_dict["resolution"],
        "resolution_unit": transform_results_dict["resolution_unit"],
    }

    if channel_attrs is not None:
        for key in ["start_time", "long_name", "grid_mapping"]:
            if key in channel_attrs:
                annotation_metadata[key] = channel_attrs[key]

    annotation_metadata.setdefault("grid_mapping", "spatial_ref")

    return annotation_metadata


# [START instantiate_dag]
@dag(
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["example"],
    default_args={
        # Covers transient eodag/S3 network failures. execution_timeout is
        # intentionally left unset: durations vary too widely with
        # search_limit/channels to pick a safe default across deployments.
        "retries": 2,
        "retry_delay": timedelta(minutes=2),
    },
    # Use Param to define DAG-level parameters with type hints and descriptions for UI and validation.
    params={
        "search_limit": Param(
            5,
            type="integer",
            title="Search Limit",
            description="Maximum number of products to search/download from DEDL",
        ),
        "channels": Param(
            ["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8", "ch9"],
            type="array",
            items={"type": "string"},
            title="Channels",
            description="List of channel names to extract from the downloaded products",
        ),
        "search_start": Param(
            None,
            type=["string", "null"],
            format="date-time",
            title="Search Start Date-Time",
            description="Start date-time for product search (ISO 8601 format, e.g., '2026-05-17T00:00:00Z'). Leave empty to use the collection's default search range.",
        ),
        "search_end": Param(
            None,
            type=["string", "null"],
            format="date-time",
            title="Search End Date-Time",
            description="End date-time for product search (ISO 8601 format, e.g., '2026-05-18T00:00:00Z'). Leave empty to use the collection's default search range.",
        ),
        "dedl_collection_id": Param(
            "EO.EUM.DAT.MSG.HRSEVIRI",
            type="string",
            title="DEDL Collection ID",
            description="Collection ID to search in the DestinE Data Lake (DEDL)",
        ),
    },

)
def tutorial_taskflow_api_demo2(
    search_limit: int = 5,
    channels: list[str] = ["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8", "ch9"],
    search_start: str = "2026-07-12T12:00:00Z",  # e.g., "2026-05-17T00:00:00Z",
    search_end: str = "2026-07-12T17:00:00Z",  # e.g., "2026-05-18T00:00:00Z",
    dedl_collection_id: str = "EO.EUM.DAT.MSG.HRSEVIRI"
):
    """
    ### TaskFlow API Tutorial Documentation
    This is a simple data pipeline example which demonstrates the use of
    the TaskFlow API using three simple tasks for Extract, Transform, and Load.
    Documentation that goes along with the Airflow TaskFlow API tutorial is
    located
    [here](https://airflow.apache.org/docs/apache-airflow/stable/tutorial_taskflow_api.html)
    """
    # Define the bounding box for Europe
    lat_min=34.0
    lat_max=72.0
    lon_min=-25.0
    lon_max=45.0

    # Define the reprojection parameters for France
    # lat_min = 41.33
    # lat_max = 51.09
    # lon_min = -5.14
    # lon_max = 9.56

    reprojection_crs = "EPSG:4326"
    reprojection_resampling = "bilinear"
    reprojection_resolution = 0.05
    reprojection_resolution_unit = "degrees"
    reprojection_bounds = (
        lon_min,
        lat_min,
        lon_max,
        lat_max,
    )  # (minlon, minlat, maxlon, maxlat)

    # [END instantiate_dag]

    # [START normalize_inputs]
    @task()
    def normalize_search_limit(search_limit: int) -> int:
        """
        #### Normalize task: validate/coerce search_limit once

        Was being validated independently inside extract() on every run; do it
        once here instead. Returned as a plain int (not wrapped in a dict) so
        it stays a task return_value XCom, which dynamic task mapping requires
        for values used as .partial()/.expand() inputs downstream.
        """
        return _normalize_search_limit(search_limit)

    @task()
    def normalize_channels(channels: list[str]) -> list[str]:
        """
        #### Normalize task: validate/dedupe channels once

        Was being validated independently inside transform/load/visualise (same
        work repeated per task). Do it once here; downstream tasks map over or
        pass through this single normalized list.
        """
        return _normalize_channels(channels)

    # [END normalize_inputs]

    # [START extract]
    @task()
    def extract(search_limit: int, search_start: str = None, search_end: str = None, dedl_collection_id: str = "EO.EUM.DAT.MSG.HRSEVIRI") -> SearchResultsDict:
        """
        #### Extract task: Search and download MSG/SEVIRI products

        Uses EODAG library to search for and download products from the DestinE Data Lake (DEDL).
        Credentials retrieved from Airflow connection 'hda_api'.
        Downloads to EODAG__DEDL__DOWNLOAD__OUTPUT_DIR and returns ordered .nat file list.

        Returns:
            SearchResultsDict: Contains num_search_results, downloaded_nat_files list,
                              collection_id, and spatial bbox
        """
        from dedl.eodag.eodag_helper import (
            clean_directory,
            extract_zip_files,
            filter_and_sort_nat_files,
            find_dedl_collection_by_eodag_id,
            find_eodag_collection_id_by_dedl_id,
            get_files_with_extension,
            get_collection_search_params,
            get_eodag_collection_info,
            shift_iso_date,
        )

        # ----------------------------------------------------
        # Example getting credentials from Airflow connection
        # ----------------------------------------------------
        from airflow.sdk import BaseHook

        conn = BaseHook.get_connection("hda_api")
        username = conn.login
        password = conn.password

        print(f"Retrieved credentials from Airflow connection: {username}, XXXX")

        # ----------------------------------------------------
        # Example initializing EODAG - assuming dedl provider is set up using environment variables
        # ----------------------------------------------------

        from eodag import EODataAccessGateway
        import eodag

        # Print EODAG version
        print(f"EODAG version: {eodag.__version__}")

        # Initialize EODAG with DestinE provider
        dag = EODataAccessGateway()
        print(dag.available_providers())

        dedl_provider = "dedl"
        dag.set_preferred_provider(dedl_provider)

        print("EODAG configured for DestinE!")

        # ----------------------------------------------------
        # Show eodag collections for the provier "dedl"
        # ----------------------------------------------------

        collections = dag.list_collections(provider=dedl_provider)
        print(collections)

        # ----------------------------------------------------
        # Demonstrate getting normalized EODAG collection id from DEDL collection id
        # ----------------------------------------------------

        # See https://data.destination-earth.eu/data-portfolio/EO.EUM.DAT.MSG.HRSEVIRI
        # dedl_collection_id = "EO.EUM.DAT.MSG.HRSEVIRI" by default
        eodag_collection_id = find_eodag_collection_id_by_dedl_id(
            dedl_collection_id,
            dag=dag,
        )

        print(
            f"Normalized EODAG collection id for DEDL collection id '{dedl_collection_id}': {eodag_collection_id}"
        )

        # ----------------------------------------------------
        # Demonstrate getting DEDL collection id from normalized EODAG collection id
        # ----------------------------------------------------

        retrieved_dedl_collection_id = find_dedl_collection_by_eodag_id(
            eodag_collection_id, dag=dag
        )

        print(
            f"DEDL collection id(s) for normalized EODAG collection id '{eodag_collection_id}': {retrieved_dedl_collection_id}"
        )

        # ----------------------------------------------------
        # Demonstrate getting information about the eodag collection id
        # ----------------------------------------------------

        collection_info = get_eodag_collection_info(eodag_collection_id, dag=dag)

        print("Collection metadata:")
        print(json.dumps(collection_info, indent=2, default=str))

        # ----------------------------------------------------
        # Demonstrate searching for products using EODAG collection id and DEDL provider
        # ----------------------------------------------------

        search_params = get_collection_search_params(collection_info)

        print("Search start date from collection:", search_params["start"])
        print("Search end date from collection:", search_params["end"])
        print("Search bbox from collection:", search_params["bbox"])

        # By default, we will use the collection metadata start and end dates for the search. However, you can override them with user-specified values if provided.
        shift_by = 2  # Number of days to shift the start date to get the end date
        search_params["end"] = shift_iso_date(search_params["start"], days=shift_by)

        # If the user has provided search_start and search_end parameters, we will use those instead of the collection metadata values.
        if search_start is not None and search_end is not None:
            search_params["start"] = search_start
            search_params["end"] = search_end
            print(
                f"Using user-specified search start '{search_start}' and end '{search_end}'"
            )
        else:
            print(
                f"Using collection metadata search start '{search_params['start']}' and end '{search_params['end']}'"
            )

        search_kwargs = {
            "collection": eodag_collection_id,
            "start": search_params["start"],
            "end": search_params["end"],
            "provider": dedl_provider,
            "limit": search_limit,
        }

        is_use_bbox = True
        if is_use_bbox:
            search_kwargs["bbox"] = search_params["bbox"]
            print("Search spatial filter mode: bbox")
        else:
            search_kwargs["geom"] = search_params["geom"]
            print("Search spatial filter mode: geom")

        search_results = dag.search(**search_kwargs)

        if search_results:
            print(
                f"Found {len(search_results)} search results for collection '{eodag_collection_id}' in {search_params['start']} to {search_params['end']}."
            )

            print(
                f"Product ids: {[product.properties.get('id', product.properties.get('title')) for product in search_results]}"
            )

            print(f"Downloading {len(search_results)} products individually (parallel)...")
            # Assure output directory is set. e.g. in env file: EODAG__DEDL__DOWNLOAD__OUTPUT_DIR=/home/eouser/eodag_downloads
            import time
            from concurrent.futures import ThreadPoolExecutor, as_completed

            # Download products one at a time (rather than dag.download_all) so that
            # a single product's failure doesn't abort the whole batch and so each
            # download's outcome/duration can be reported individually. eodag's
            # download_all() swallows ordinary per-product errors and returns only
            # a shorter list of successful paths, with no per-product identity or
            # timing — dag.download() raises per-product instead, which we can catch.
            def _download_one(product: Any) -> DownloadRecordDict:
                product_id = str(
                    product.properties.get("id", product.properties.get("title"))
                )
                start = time.perf_counter()
                try:
                    downloaded_path = dag.download(
                        product,
                        extract=True,
                        delete_archive=False,
                        progress_callback=None,
                    )
                    return {
                        "product_id": product_id,
                        "title": product_id,
                        "status": "success",
                        "duration_seconds": time.perf_counter() - start,
                        "error": None,
                        "downloaded_path": str(downloaded_path),
                    }
                except Exception as exc:
                    return {
                        "product_id": product_id,
                        "title": product_id,
                        "status": "failed",
                        "duration_seconds": time.perf_counter() - start,
                        "error": str(exc),
                        "downloaded_path": None,
                    }

            download_records: list[DownloadRecordDict] = []
            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = [
                    executor.submit(_download_one, product) for product in search_results
                ]
                for future in as_completed(futures):
                    download_records.append(future.result())

            num_downloads_succeeded = sum(
                1 for record in download_records if record["status"] == "success"
            )
            num_downloads_failed = len(download_records) - num_downloads_succeeded

            for record in download_records:
                if record["status"] == "success":
                    print(
                        f"Downloaded product '{record['product_id']}' to: "
                        f"{record['downloaded_path']} ({record['duration_seconds']:.2f}s)"
                    )
                else:
                    print(
                        f"Failed to download product '{record['product_id']}' after "
                        f"{record['duration_seconds']:.2f}s: {record['error']}"
                    )

            downloaded_folder_list = [
                record["downloaded_path"]
                for record in download_records
                if record["status"] == "success"
            ]
            print(
                f"Downloaded {num_downloads_succeeded}/{len(search_results)} products "
                f"({num_downloads_failed} failed)."
            )

            print("starting to clean the output directory to ensure extracted files are in the correct location...")
            # Note: workaround for an eodag extract issue — some downloaded filenames arrive
            # with malformed Content-Disposition artifacts that break eodag's own extraction.
            # Rename those files, then re-extract only the ones that needed renaming (files
            # already correctly named/extracted by eodag, or renamed in a prior run, are skipped).
            renamed_files = clean_directory(_get_output_base_dir())
            extract_zip_files(renamed_files, overwrite=True)
            print("Cleaned the output directory.")

            # Get the list of .nat files from the downloaded folders
            current_run_nat_files = get_files_with_extension(downloaded_folder_list, ".nat")

            ordered_nat_files = filter_and_sort_nat_files(
                [str(path) for path in current_run_nat_files]
            )

            return {
                "num_search_results": len(search_results),
                "downloaded_nat_files": [str(path) for path in ordered_nat_files],
                "collection_id": dedl_collection_id,
                "bbox": search_params["bbox"],
                "download_records": download_records,
                "num_downloads_succeeded": num_downloads_succeeded,
                "num_downloads_failed": num_downloads_failed,
            }

        else:
            print(
                f"No search results found for collection '{eodag_collection_id}' in {search_params['start']} to {search_params['end']}."
            )

        return {
            "num_search_results": 0,
            "downloaded_nat_files": [],
            "collection_id": dedl_collection_id,
            "bbox": search_params["bbox"],
            "download_records": [],
            "num_downloads_succeeded": 0,
            "num_downloads_failed": 0,
        }

    # [END extract]

    @task()
    def get_downloaded_nat_files(search_results_dict: SearchResultsDict) -> list[str]:
        """
        #### Bridge task: expose the downloaded .nat file list as a plain return_value

        Airflow's dynamic task mapping (.expand()) only accepts a task's raw
        return_value XCom, not a subscript/derived key from a dict-returning
        task. This task exists purely so transform_one can .expand() over the
        .nat files extract() downloaded.
        """
        return search_results_dict["downloaded_nat_files"]

    # [START transform]
    @task()
    def transform_one(nat_file: str, channels: list[str]) -> TransformOneResultDict:
        """
        #### Transform task (mapped): spatially filter, reproject, and zarr-encode one .nat file

        Runs once per downloaded .nat file via dynamic task mapping (see main_flow),
        so files are processed in parallel instead of one after another:
        1. Crop to Europe (spatial_filter)
        2. Reproject to EPSG:4326 at 0.05° resolution
        3. Extract selected channels
        4. Write cloud-optimized Zarr

        Args:
            nat_file: Path to a single downloaded .nat file
            channels: List of channel names to extract (already normalized upstream)

        Returns:
            TransformOneResultDict: Path to the per-file Zarr output
        """
        import time

        from dedl.eodag.eodag_helper import change_extension

        transform_start = time.perf_counter()

        print(f"Transforming file: {nat_file} for channels: {channels}")
        # Reference: https://cloudferro-dedl-staging.readthedocs-hosted.com/en/latest/working_with_ai_in_the_data_lake/ai_ready_data_preparation/demos/01_msg_local_to_zarr_code.html

        # -----------------------------------------------------
        # Step 1 : Defair Setup and import : Show readers and writers
        # -----------------------------------------------------

        from pathlib import Path

        import xarray as xr
        from defair_data.core import Dataset
        from defair_data.readers import list_readers
        from defair_data.writers import list_writers
        from defair.logging import setup_logging

        setup_logging(log_level="INFO")

        print("Available readers:", list_readers())
        print("Available writers:", list_writers())

        # -----------------------------------------------------
        # Step 3 : Read MSG data with automatic reader detection
        # -----------------------------------------------------

        # Automatically detect the reader based on the file extension and content
        dataset = Dataset.from_source(nat_file)

        print(f"Dataset loaded: {dataset}")
        print(f"\nData variables: {list(dataset.data.data_vars)}")
        print(f"Coordinates: {list(dataset.data.coords)}")

        # -----------------------------------------------------
        # Step 4 : Inspect Dataset Structure
        # -----------------------------------------------------

        available_channels = list(dataset.data.data_vars)
        missing_channels = [ch for ch in channels if ch not in available_channels]
        if missing_channels:
            raise ValueError(
                f"Requested channels {missing_channels} not found in dataset. "
                f"Available channels: {available_channels}"
            )

        # Inspect each selected channel
        for channel_name in channels:
            selected_channel = dataset.data[channel_name]
            print(f"Channel: {channel_name}")
            print(f"Shape: {selected_channel.shape}")
            print(f"Dtype: {selected_channel.dtype}")
            print(f"Chunks: {selected_channel.chunks}")
            print("\nAttributes:")
            for key, value in selected_channel.attrs.items():
                print(f"  {key}: {value}")

        # -----------------------------------------------------
        # Step 5 : Check CF 1.8 Compliance
        # -----------------------------------------------------
        print("Global Attributes:")
        for key in ["Conventions", "title", "institution", "source", "history"]:
            if key in dataset.data.attrs:
                value = dataset.data.attrs[key]
                # Truncate long values
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                print(f"  {key}: {value}")

        print("\nCoordinate Reference System:")
        if "spatial_ref" in dataset.data.coords:
            crs = dataset.data.coords["spatial_ref"]
            print(f"  CRS WKT: {crs.attrs.get('crs_wkt', 'N/A')[:200]}...")

        reference_channel = dataset.data[channels[0]]
        if "grid_mapping" in reference_channel.attrs:
            print(f"  Grid mapping: {reference_channel.attrs['grid_mapping']}")

        # -----------------------------------------------------
        # Step X1a : Apply Spatial Filtering to Crop to Europe
        # -----------------------------------------------------

        # Crop to Europe (fast, no reprojection) — use spatial_filter
        #     Good when you only want an AOI crop and keep original grid.
        #     Example bounding box that covers most of continental Europe: lon ∈ [-25, 45], lat ∈ [34, 72].

        # The spatial_filter plugin accepts polygon inputs (GeoJSON/WKT/paths) if you want a precise European shape instead of a bbox.
        # If your product has multiple coordinate groups (swath products), spatial_filter will handle per-group masking; use coordinate_group=(lat_name, lon_name) to target a single group.

        # Crop to Europe using the spatial_filter transformation

        ds_europe = dataset.transform(
            "spatial_filter",
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
            drop=True,  # drop pixels outside AOI (shrinks dims)
            allow_partial=True,  # allow partial coverage without raising
        )

        # -----------------------------------------------------
        # Step X1b : Reproject and Resample to Europe
        # -----------------------------------------------------

        # Reproject to EPSG:4326 and spatially sample (resample) — use reprojection bounds+resolution
        #     Use when you want a regular lat/lon grid and a specific spatial resolution (degrees or km).
        #     Example: 0.05° resolution (~5 km at equator) and the same Europe bbox.

        # If you need conservative flux-preserving regridding (e.g., area-averaged variables), use the xarray_regrid backend via reproject(..., backend="xarray_regrid", resampling="conservative", resolution=...) — see the reprojection plugin docs.
        # Bounds format is (minx, miny, maxx, maxy) → for lon/lat that's (minlon, minlat, maxlon, maxlat).

        # Reproject + resample to a regular EPSG:4326 grid covering Europe : (reproject the cropped dataset to avoid reprojecting the full original)
        ds_europe_reproj = ds_europe.reproject(
            reprojection_crs,
            resampling=reprojection_resampling,  # or "nearest", "cubic"
            resolution=reprojection_resolution,  # in degrees (see resolution_unit)
            resolution_unit=reprojection_resolution_unit,
            bounds=reprojection_bounds,  # (lon_min, lat_min, lon_max, lat_max)
        )

        # -----------------------------------------------------
        # Step X2 : Focus on a subset of channels (bands) for further processing: Question on cdm here
        # -----------------------------------------------------

        # Select all configured channels from the transformed dataset.
        xr_channel = ds_europe_reproj.data[channels]
        ds_channel = Dataset(xr_channel)

        # Keep downstream logic unchanged by replacing dataset with the single-channel view.
        dataset = ds_channel

        # -----------------------------------------------------
        # Step 6 : Write a cloud-optimized Zarr file with consolidated metadata
        # -----------------------------------------------------

        zarr_file = change_extension(nat_file, ".zarr")

        dataset.to_file(
            zarr_file,
            writer="zarrv2",  # Use Zarr v2 format
            mode="w",  # Overwrite if exists
            consolidated=True,  # Create consolidated metadata for faster reads
        )

        print(f"✓ Data written to: {zarr_file}")

        # -----------------------------------------------------
        # Step 7 : Verify the Zarr file by reading it back and checking its structure
        # -----------------------------------------------------

        zarr_ds = xr.open_zarr(zarr_file, consolidated=True)

        print("Zarr Dataset:")
        print(zarr_ds)

        # Verify data integrity
        print("\n✓ Verification:")
        print(
            f"  Variables match: {set(dataset.data.data_vars) == set(zarr_ds.data_vars)}"
        )
        print(
            f"  Coordinates match: {set(dataset.data.coords) == set(zarr_ds.coords)}"
        )

        # Check Zarr storage details
        print("\nZarr Storage:")
        for var in zarr_ds.data_vars:
            zarr_array = zarr_ds[var]
            print(f"  {var}:")
            print(f"    Chunks: {zarr_array.chunks}")
            print(
                f"    Compressor: {zarr_array.encoding.get('compressor', 'default')}"
            )

        # -----------------------------------------------------
        # Step 8 : Check Provenance Tracking and Metadata
        # -----------------------------------------------------

        print("Provenance History:")
        print(zarr_ds.attrs["history"])

        print("\nCreation Metadata:")
        for key in ["date_created", "creator_name", "creator_url"]:
            if key in zarr_ds.attrs:
                print(f"  {key}: {zarr_ds.attrs[key]}")

        def get_dir_size(path):
            total = 0
            for entry in Path(path).rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
            return total

        # -----------------------------------------------------
        # Step 9 : Storage Efficiency Comparison: Compare the size of the original MSG .nat file and the resulting Zarr file
        # -----------------------------------------------------

        if Path(nat_file).exists() and Path(zarr_file).exists():
            input_size = Path(nat_file).stat().st_size
            output_size = get_dir_size(zarr_file)

            print("Storage Comparison:")
            print(f"  Input (MSG .nat):  {input_size / 1024 / 1024:.2f} MB")
            print(f"  Output (Zarr):     {output_size / 1024 / 1024:.2f} MB")
            print(f"  Compression ratio: {input_size / output_size:.2f}x")
            print(
                f"  Size change:       {(output_size - input_size) / input_size * 100:+.1f}%"
            )

        return {
            "zarr_path": str(zarr_file),
            "nat_file": nat_file,
            "duration_seconds": time.perf_counter() - transform_start,
        }

    @task(multiple_outputs=True)
    def concatenate_zarr_files(
        transform_results: list[TransformOneResultDict], channels: list[str]
    ) -> TransformResultsDict:
        """
        #### Concatenate task: merge per-file Zarr outputs into one time-indexed Zarr

        Consumes the outputs of the mapped transform_one task instances and
        concatenates them along the time dimension using Defair.from_source with
        concat_dim="time". No re-sort by timestamp is needed here: extract()
        already sorts .nat files chronologically before transform_one.expand(),
        and dynamic task mapping preserves that input order in the collected
        results.

        Args:
            transform_results: Outputs of the mapped transform_one task instances
            channels: List of channel names extracted (already normalized upstream)

        Returns:
            TransformResultsDict: Contains concatenated_zarr_path, channel list,
                                 and reprojection metadata
        """
        from pathlib import Path

        import xarray as xr
        from defair_data.core import Dataset

        def get_dir_size(path):
            total = 0
            for entry in Path(path).rglob("*"):
                if entry.is_file():
                    total += entry.stat().st_size
            return total

        zarr_files = [result["zarr_path"] for result in transform_results]

        if zarr_files:
            xr_dsets = [xr.open_zarr(str(p), consolidated=True) for p in zarr_files]

            combined = xr.concat(xr_dsets, dim="time")

            ds = Dataset(combined)

            concatenated_zarr_path = _build_concatenated_zarr_path()
            ds.to_file(
                concatenated_zarr_path,
                writer="zarrv2",
                mode="w",
                consolidated=True,
            )

            # print size of the concatenated dataset
            concatenated_size = get_dir_size(concatenated_zarr_path)
            print(
                f"Concatenated Zarr dataset size: {concatenated_size / 1024 / 1024:.2f} MB"
            )

            return {
                "total_num_zarr_files": len(zarr_files),
                "concatenated_zarr_path": concatenated_zarr_path,
                "channels": channels,
                "reprojection_bounds": reprojection_bounds,
                "reprojection_crs": reprojection_crs,
                "resampling": reprojection_resampling,
                "resolution": reprojection_resolution,
                "resolution_unit": reprojection_resolution_unit,
            }

        return {
            "total_num_zarr_files": 0,
            "concatenated_zarr_path": _build_concatenated_zarr_path(),
            "channels": channels,
            "reprojection_bounds": reprojection_bounds,
            "reprojection_crs": reprojection_crs,
            "resampling": reprojection_resampling,
            "resolution": reprojection_resolution,
            "resolution_unit": reprojection_resolution_unit,
        }

    # [END transform]

    # [START load]
    @task()
    def load(transform_results_dict: TransformResultsDict, channels: list[str]) -> LoadResultDict:
        """
        #### Load task: Upload transformed Zarr dataset to S3

        Uploads the concatenated Zarr directory to S3 under a channel-based prefix.
        S3 credentials (endpoint, bucket, keys) come from environment variables.

        Args:
            transform_results_dict: From concatenate_zarr_files(); contains
                                   concatenated_zarr_path and reprojection metadata
            channels: List of channels for S3 key naming (already normalized upstream)

        Returns:
            LoadResultDict: S3 upload result (success, s3_uri, destination_prefix)
                           plus reprojection metadata for downstream tasks
        """
        import os

        from dedl.s3.s3_helper import upload_directory_to_s3

        concatenated_zarr_path = transform_results_dict["concatenated_zarr_path"]
        endpoint_url = os.environ["S3_ENDPOINT_URL"]
        bucket_name = os.environ["MY_S3_BUCKET_NAME"]
        access_key_id = os.environ["MY_S3_ACCESS_KEY_ID"]
        secret_access_key = os.environ["MY_S3_SECRET_ACCESS_KEY"]

        print(f"Uploading Zarr directory to S3: {concatenated_zarr_path}")

        channels_slug = "_".join(channels)
        upload_result = upload_directory_to_s3(
            local_directory_path=concatenated_zarr_path,
            bucket_name=bucket_name,
            endpoint_url=endpoint_url,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            destination_prefix=f"my_{channels_slug}_zarr_data",  # Optional: specify a prefix in the S3 bucket
        )

        print(f"Uploaded to: {upload_result['s3_uri']}")
        upload_result["channels"] = channels
        upload_result["reprojection_bounds"] = transform_results_dict[
            "reprojection_bounds"
        ]
        upload_result["reprojection_crs"] = transform_results_dict["reprojection_crs"]
        upload_result["resampling"] = transform_results_dict["resampling"]
        upload_result["resolution"] = transform_results_dict["resolution"]
        upload_result["resolution_unit"] = transform_results_dict["resolution_unit"]
        return upload_result

    # [END load]

    # [START visualise]
    @task()
    def visualise_one(
        channel_name: str,
        load_result_dict: LoadResultDict,
        search_results_dict: SearchResultsDict,
    ) -> VisualiseOneResultDict:
        """
        #### Visualise task (mapped): render + upload an annotated MP4 for one channel

        Runs once per channel via dynamic task mapping (see main_flow), so channels
        render in parallel. Each mapped instance is fully self-contained: it reads
        the S3-backed Zarr dataset for its channel, renders an MP4 time-lapse with:
        - 4 FPS, max 120 frames
        - Inferno colormap
        - Metadata overlay: collection ID, bbox, CRS, resolution, channel attributes

        Uploads MP4 to S3 under 'visualization/{channel}/' prefix.

        Args:
            channel_name: Single channel to visualize (already normalized upstream)
            load_result_dict: From load(); contains S3 URI and reprojection metadata
            search_results_dict: From extract(); contains collection_id and search bbox

        Returns:
            VisualiseOneResultDict: Per-channel video metadata
        """
        import os
        import time

        from dedl.s3.s3_helper import upload_file_to_s3
        from dedl.visualization.visualization_helper import (
            create_mp4_from_dataarray,
            open_s3_zarr_dataset,
            resolve_data_variable,
        )

        visualise_start = time.perf_counter()

        endpoint_url = os.environ["S3_ENDPOINT_URL"]
        bucket_name = os.environ["MY_S3_BUCKET_NAME"]
        access_key_id = os.environ["MY_S3_ACCESS_KEY_ID"]
        secret_access_key = os.environ["MY_S3_SECRET_ACCESS_KEY"]

        source_prefix = load_result_dict["destination_prefix"]

        dataset = open_s3_zarr_dataset(
            bucket_name=bucket_name,
            prefix=source_prefix,
            endpoint_url=endpoint_url,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )

        if channel_name not in dataset.data_vars:
            raise ValueError(
                f"Requested channel '{channel_name}' not found in uploaded dataset. "
                f"Available channels: {list(dataset.data_vars)}"
            )

        selected_channel = resolve_data_variable(dataset, preferred_name=channel_name)
        output_mp4_path = _build_video_output_path(channel_name)
        annotation_metadata = _build_visualization_annotation_metadata(
            search_results_dict,
            load_result_dict,
            channel_name,
            channel_attrs=dict(selected_channel.attrs),
        )

        video_result = create_mp4_from_dataarray(
            selected_channel,
            output_mp4_path,
            fps=4,
            frame_stride=1,
            max_frames=120,
            colormap_name="inferno",
            annotation_metadata=annotation_metadata,
        )

        upload_result = upload_file_to_s3(
            local_file_path=output_mp4_path,
            bucket_name=bucket_name,
            endpoint_url=endpoint_url,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            destination_key=(
                f"visualization/{channel_name}/{channel_name}_timelapse.mp4"
            ),
        )

        return {
            "channel": channel_name,
            "video_path": video_result["video_path"],
            "frame_count": video_result["frame_count"],
            "fps": video_result["fps"],
            "video_s3_uri": upload_result["s3_uri"],
            "duration_seconds": time.perf_counter() - visualise_start,
        }

    # [END visualise]

    # [START main_flow]
    show_params()  # Display DAG run configuration

    # Normalize: validate/coerce search_limit and channels once, upfront
    normalized_search_limit: int = normalize_search_limit(search_limit)
    normalized_channels: list[str] = normalize_channels(channels)

    # Extract: search & download MSG products
    search_results_dict: SearchResultsDict = extract(
        search_limit=normalized_search_limit,
        search_start=search_start,
        search_end=search_end,
        dedl_collection_id=dedl_collection_id,
    )

    downloaded_nat_files: list[str] = get_downloaded_nat_files(search_results_dict)

    # Transform: crop, reproject, zarr-encode — one mapped task instance per
    # downloaded .nat file, processed in parallel, then concatenated
    transform_results = transform_one.partial(channels=normalized_channels).expand(
        nat_file=downloaded_nat_files
    )

    transform_results_dict: TransformResultsDict = concatenate_zarr_files(
        transform_results, channels=normalized_channels
    )

    # Load: upload Zarr to S3
    load_result_dict: LoadResultDict = load(
        transform_results_dict, channels=normalized_channels
    )

    # Visualise: render MP4 time-lapses — one mapped task instance per channel,
    # rendered in parallel
    visualise_results = visualise_one.partial(
        load_result_dict=load_result_dict, search_results_dict=search_results_dict
    ).expand(channel_name=normalized_channels)

    # Report: global run summary (criteria, download success/failure counts,
    # per-product/per-channel timings). trigger_rule="all_done" (set on the
    # task itself in dedl.tasks.reporting) so it still runs and reports
    # accurately even if load/visualise fail downstream of a successful
    # extract/transform.
    generate_run_report(
        criteria={
            "search_limit": normalized_search_limit,
            "channels": normalized_channels,
            "search_start": search_start,
            "search_end": search_end,
            "dedl_collection_id": dedl_collection_id,
            "reprojection_crs": reprojection_crs,
            "resampling": reprojection_resampling,
            "resolution": reprojection_resolution,
            "resolution_unit": reprojection_resolution_unit,
            "reprojection_bounds": reprojection_bounds,
        },
        search_results_dict=search_results_dict,
        transform_results=transform_results,
        visualise_results=visualise_results,
    )
    # [END main_flow]


# [START dag_invocation]
dag = tutorial_taskflow_api_demo2()
# [END dag_invocation]

# [END tutorial]
if __name__ == "__main__":

    dag.test(
        run_conf={"search_limit": 30, "channels": ["ch1", "ch2", "ch3", "ch4", "ch5", "ch6", "ch7", "ch8", "ch9"], "search_start": "2026-07-12T12:00:00Z", "search_end": "2026-07-12T17:00:00Z", "dedl_collection_id": "EO.EUM.DAT.MSG.HRSEVIRI"},
    )
