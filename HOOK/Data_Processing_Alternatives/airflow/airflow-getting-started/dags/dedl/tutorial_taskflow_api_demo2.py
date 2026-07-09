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
from typing import Any

import pendulum
from airflow.sdk import dag, get_current_context, task
from airflow.sdk.definitions.param import DagParam
from dedl.tasks.common import show_params

# [END import_module]


def _resolve_runtime_param(value: Any) -> Any:
    if isinstance(value, DagParam):
        return value.resolve(get_current_context())
    return value


def _normalize_channel(value: str | DagParam) -> str:
    channel = str(_resolve_runtime_param(value)).strip()
    if not channel:
        raise ValueError("channel must be a non-empty string")
    if "/" in channel or "\\" in channel:
        raise ValueError("channel must not contain path separators")
    return channel


def _normalize_channels(value: list[str] | DagParam) -> list[str]:
    resolved_value = _resolve_runtime_param(value)

    if isinstance(resolved_value, list):
        raw_channels = [_normalize_channel(channel) for channel in resolved_value]
    else:
        raise TypeError("channels must be a list of strings")

    if not raw_channels:
        raise ValueError("channels must contain at least one channel")

    deduplicated_channels: list[str] = []
    seen: set[str] = set()
    for channel in raw_channels:
        normalized_channel = _normalize_channel(channel)
        if normalized_channel in seen:
            continue
        seen.add(normalized_channel)
        deduplicated_channels.append(normalized_channel)

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
)
def tutorial_taskflow_api_demo2(
    search_limit: int = 10,
    channels: list[str] = ["ch9"],
):
    """
    ### TaskFlow API Tutorial Documentation
    This is a simple data pipeline example which demonstrates the use of
    the TaskFlow API using three simple tasks for Extract, Transform, and Load.
    Documentation that goes along with the Airflow TaskFlow API tutorial is
    located
    [here](https://airflow.apache.org/docs/apache-airflow/stable/tutorial_taskflow_api.html)
    """
    if isinstance(channels, list):
        _normalize_channels(channels)

    reprojection_crs = "EPSG:4326"
    reprojection_resampling = "bilinear"
    reprojection_resolution = 0.05
    reprojection_resolution_unit = "degrees"
    reprojection_bounds = (-25.0, 34.0, 45.0, 72.0)

    # [END instantiate_dag]

    # [START extract]
    @task()
    def extract(search_limit: int):
        """
        #### Extract task
        Here we demonstrate how to use the EODAG library to search for and download products from the DestinE Data Lake (DEDL) using the EODAG API. We also demonstrate how to retrieve credentials from an Airflow connection.
        """
        from dedl.eodag.eodag_helper import (
            clean_directory,
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
        dedl_collection_id = "EO.EUM.DAT.MSG.HRSEVIRI"

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

        print("Search start date:", search_params["start"])
        print("Search bbox:", search_params["bbox"])

        is_custom_end_date = True  # Set to True if you want to use the end date from the collection metadata
        if is_custom_end_date:
            shift_by = 2  # Number of days to shift the start date to get the end date
            search_params["end"] = shift_iso_date(search_params["start"], days=shift_by)
            print(
                f"Using custom end date start '{search_params['start']}' shift_by '{shift_by}' gives end {search_params['end']}"
            )

        print("Search end date:", search_params["end"])

        search_limit = _normalize_search_limit(search_limit)

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

            for product in search_results:
                props = product.properties
                print("Product metadata:", json.dumps(props, indent=2, default=str))

                # download the product
                # downloaded_file = dag.download(product, extract=True, delete_archive=False)
                # downloaded_file = product.download()
                # print(f"Downloaded product to: {downloaded_file}")

            print(f"Downloading all {len(search_results)} products...")
            # Assure output directory is set. e.g. in env file: EODAG__DEDL__DOWNLOAD__OUTPUT_DIR=/home/eouser/eodag_downloads
            dag.download_all(search_results, extract=True, delete_archive=False)
            print(f"Downloaded all {len(search_results)} products.")

            cleaned_files, extracted_folders = clean_directory(
                "/home/eouser/eodag_downloads/msg_hrseviri", unzip=True, overwrite=True
            )

            current_run_nat_files = [
                path for path in cleaned_files if path.suffix.lower() == ".nat"
            ]
            if extracted_folders:
                extracted_nat_files = get_files_with_extension(
                    [str(path) for path in extracted_folders],
                    "nat",
                    recursive=True,
                )
                current_run_nat_files.extend(extracted_nat_files)

            ordered_nat_files = filter_and_sort_nat_files(
                [str(path) for path in current_run_nat_files]
            )

            return {
                "search_results": len(search_results),
                "downloaded_nat_files": [str(path) for path in ordered_nat_files],
                "collection_id": dedl_collection_id,
                "bbox": search_params["bbox"],
            }

        else:
            print(
                f"No search results found for collection '{eodag_collection_id}' in {search_params['start']} to {search_params['end']}."
            )

        return {
            "search_results": 0,
            "downloaded_nat_files": [],
            "collection_id": dedl_collection_id,
            "bbox": search_params["bbox"],
        }

    # [END extract]

    # [START transform]
    @task(multiple_outputs=True)
    def transform(search_results_dict: dict, channels: list[str]):
        """
        #### Transform task
        Transformation Task based on Defair Python Library.
        """
        from dedl.eodag.eodag_helper import (
            change_extension,
            filename_timestamp_sort_key,
            filter_and_sort_nat_files,
        )

        channels = _normalize_channels(channels)

        print(f"Transforming data with previous results: {search_results_dict}")
        print(f"Transforming data for channels: {channels}")
        # Reference: https://cloudferro-dedl-staging.readthedocs-hosted.com/en/latest/working_with_ai_in_the_data_lake/ai_ready_data_preparation/demos/01_msg_local_to_zarr_code.html

        # -----------------------------------------------------
        # Step 1 : Defair Setup and import : Show readers and writers
        # -----------------------------------------------------

        import sys
        from pathlib import Path

        import xarray as xr
        from defair_data.core import Dataset
        from defair_data.readers import list_readers
        from defair_data.writers import list_writers
        from defair.logging import setup_logging
        from defair_data.dask_manager import close_dask_client

        setup_logging(log_level="INFO")

        print("Available readers:", list_readers())
        print("Available writers:", list_writers())

        # -----------------------------------------------------
        # Step 2 : Configuration : getting input files
        # -----------------------------------------------------

        nat_files = filter_and_sort_nat_files(
            search_results_dict.get("downloaded_nat_files", [])
        )

        print(f"Current run .nat files selected for transform: {len(nat_files)}")

        # We will use this list of treated zarr files to generate Just a singe zarr file with concat_dim="time"
        zarr_files = []

        for nat_file in nat_files:
            print(f"Processing file: {nat_file}")

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
                lat_min=34.0,
                lat_max=72.0,
                lon_min=-25.0,
                lon_max=45.0,
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
                bounds=reprojection_bounds,  # (minlon, minlat, maxlon, maxlat)
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

            # we will use this list of treated zarr files to generate Just a singe zarr file with concat_dim="time"
            zarr_files.append(zarr_file)

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

        # -----------------------------------------------------
        # Step 10 : Concatenate all Zarr files along the time dimension to create a single Zarr dataset using Defair.from_source with concat_dim="time"
        # -----------------------------------------------------

        if zarr_files:

            zarr_files = sorted(
                zarr_files,
                key=lambda path: filename_timestamp_sort_key(Path(path).with_suffix(".nat")),
            )

            xr_dsets = [xr.open_zarr(str(p), consolidated=True) for p in zarr_files]

            combined = xr.concat(xr_dsets, dim="time")

            ds = Dataset(combined)

            ds.to_file(
                "/home/eouser/eodag_downloads/msg_hrseviri/concatenated.zarr",
                writer="zarrv2",
                mode="w",
                consolidated=True,
            )

            # print size of the concatenated dataset
            concatenated_size = get_dir_size(
                "/home/eouser/eodag_downloads/msg_hrseviri/concatenated.zarr"
            )
            print(
                f"Concatenated Zarr dataset size: {concatenated_size / 1024 / 1024:.2f} MB"
            )

            return {
                "total_num_zarr_files": len(zarr_files),
                "concatenated_zarr_path": "/home/eouser/eodag_downloads/msg_hrseviri/concatenated.zarr",
                "channels": channels,
                "reprojection_bounds": reprojection_bounds,
                "reprojection_crs": reprojection_crs,
                "resampling": reprojection_resampling,
                "resolution": reprojection_resolution,
                "resolution_unit": reprojection_resolution_unit,
            }

        return {
            "total_num_zarr_files": 0,
            "concatenated_zarr_path": "/home/eouser/eodag_downloads/msg_hrseviri/concatenated.zarr",
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
    def load(transform_results_dict: dict, channels: list[str]):
        """
        #### Load task
        This load task could be used to upload the zarr files to e.g. S3 storage.
        """
        import os

        from dedl.s3.s3_helper import upload_directory_to_s3

        channels = _normalize_channels(channels)
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
        upload_result["reprojection_bounds"] = transform_results_dict["reprojection_bounds"]
        upload_result["reprojection_crs"] = transform_results_dict["reprojection_crs"]
        upload_result["resampling"] = transform_results_dict["resampling"]
        upload_result["resolution"] = transform_results_dict["resolution"]
        upload_result["resolution_unit"] = transform_results_dict["resolution_unit"]
        return upload_result
    # [END load]

    # [START visualise]
    @task()
    def visualise(load_result_dict: dict, search_results_dict: dict, channels: list[str]):
        """
        #### Visualise task
        Build an MP4 time-lapse from the selected channel in the uploaded S3-backed Zarr.
        """
        import os

        from dedl.s3.s3_helper import upload_file_to_s3
        from dedl.visualization.visualization_helper import (
            create_mp4_from_dataarray,
            open_s3_zarr_dataset,
            resolve_data_variable,
        )

        channels = _normalize_channels(channels)
        endpoint_url = os.environ["S3_ENDPOINT_URL"]
        bucket_name = os.environ["MY_S3_BUCKET_NAME"]
        access_key_id = os.environ["MY_S3_ACCESS_KEY_ID"]
        secret_access_key = os.environ["MY_S3_SECRET_ACCESS_KEY"]

        source_prefix = load_result_dict["destination_prefix"]
        source_s3_uri = load_result_dict["s3_uri"]

        dataset = open_s3_zarr_dataset(
            bucket_name=bucket_name,
            prefix=source_prefix,
            endpoint_url=endpoint_url,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )

        available_channels = list(dataset.data_vars)
        missing_channels = [ch for ch in channels if ch not in available_channels]
        if missing_channels:
            raise ValueError(
                f"Requested channels {missing_channels} not found in uploaded dataset. "
                f"Available channels: {available_channels}"
            )

        videos: list[dict[str, Any]] = []
        for channel_name in channels:
            selected_channel = resolve_data_variable(dataset, preferred_name=channel_name)
            output_mp4_path = (
                f"/home/eouser/eodag_downloads/msg_hrseviri/{channel_name}_timelapse.mp4"
            )
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

            videos.append(
                {
                    "channel": channel_name,
                    "video_path": video_result["video_path"],
                    "frame_count": video_result["frame_count"],
                    "fps": video_result["fps"],
                    "video_s3_uri": upload_result["s3_uri"],
                }
            )

        return {
            "source_s3_uri": source_s3_uri,
            "videos": videos,
        }
    # [END visualise]



    # [START main_flow]
    show_params()  # Example of a function call within a DAG context
    search_results_dict = extract(search_limit=search_limit)
    transform_results_dict = transform(search_results_dict, channels=channels)
    load_result_dict = load(transform_results_dict, channels=channels)
    visualise(load_result_dict, search_results_dict, channels=channels)
    # [END main_flow]


# [START dag_invocation]
dag = tutorial_taskflow_api_demo2()
# [END dag_invocation]

# [END tutorial]
if __name__ == "__main__":

    dag.test(run_conf={"search_limit": 30, "channels": ["ch1", "ch2", "ch3", "ch4", "ch9"]})
