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

import pendulum
from airflow.sdk import dag, task
from dedl.tasks.common import show_params

# [END import_module]


# [START instantiate_dag]
@dag(
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["example"],
)
def tutorial_taskflow_api_demo2():
    """
    ### TaskFlow API Tutorial Documentation
    This is a simple data pipeline example which demonstrates the use of
    the TaskFlow API using three simple tasks for Extract, Transform, and Load.
    Documentation that goes along with the Airflow TaskFlow API tutorial is
    located
    [here](https://airflow.apache.org/docs/apache-airflow/stable/tutorial_taskflow_api.html)
    """
    # [END instantiate_dag]

    # [START extract]
    @task()
    def extract():
        """
        #### Extract task
        Here we demonstrate how to use the EODAG library to search for and download products from the DestinE Data Lake (DEDL) using the EODAG API. We also demonstrate how to retrieve credentials from an Airflow connection.
        """
        from dedl.eodag.eodag_helper import (
            clean_directory,
            find_dedl_collection_by_eodag_id,
            find_eodag_collection_id_by_dedl_id,
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

        # search limit
        search_limit = 2

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

            return {
                "search_results": len(search_results),
            }

        else:
            print(
                f"No search results found for collection '{eodag_collection_id}' in {search_params['start']} to {search_params['end']}."
            )

        return {
            "search_results": 0,
        }

    # [END extract]

    # [START transform]
    @task(multiple_outputs=True)
    def transform(search_results_dict: dict):
        """
        #### Transform task
        Transformation Task based on Defair Python Library.
        """
        from dedl.eodag.eodag_helper import change_extension, get_files_with_extension

        print(f"Transforming data with previous results: {search_results_dict}")
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

        nat_files = get_files_with_extension(
            ["/home/eouser/eodag_downloads/msg_hrseviri"], "nat", recursive=True
        )

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

            # Inspect a single channel
            ir_channel = dataset.data["ch9"]
            print("Channel: ir_10.8")
            print(f"Shape: {ir_channel.shape}")
            print(f"Dtype: {ir_channel.dtype}")
            print(f"Chunks: {ir_channel.chunks}")
            print("\nAttributes:")
            for key, value in ir_channel.attrs.items():
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

            if "grid_mapping" in dataset.data["ch9"].attrs:
                print(f"  Grid mapping: {dataset.data['ch9'].attrs['grid_mapping']}")

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
                "EPSG:4326",
                resampling="bilinear",  # or "nearest", "cubic"
                resolution=0.05,  # in degrees (see resolution_unit)
                resolution_unit="degrees",
                bounds=(-25.0, 34.0, 45.0, 72.0),  # (minlon, minlat, maxlon, maxlat)
            )

            # -----------------------------------------------------
            # Step X2 : Focus on a subset of channels (bands) for further processing: Question on cdm here
            # -----------------------------------------------------

            # 1) then select ch9 from the transformed dataset ()
            xr_ch9 = ds_europe_reproj.data[["ch9"]]
            ds_ch9 = Dataset(xr_ch9)

            # So we don't have to modify the following code, we can just assign the ch9-only dataset to the variable `dataset` for further processing.
            dataset = ds_ch9

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
            }

        return {
            "total_num_zarr_files": 0,
            "concatenated_zarr_path": "/home/eouser/eodag_downloads/msg_hrseviri/concatenated.zarr",
        }

    # [END transform]

    # [START load]
    @task()
    def load(transform_results_dict: dict):
        """
        #### Load task
        This load task could be used to upload the zarr files to e.g. S3 storage.
        """
        import os

        from dedl.s3.s3_helper import upload_directory_to_s3

        concatenated_zarr_path = transform_results_dict["concatenated_zarr_path"]
        endpoint_url = os.environ["S3_ENDPOINT_URL"]
        bucket_name = os.environ["MY_S3_BUCKET_NAME"]
        access_key_id = os.environ["MY_S3_ACCESS_KEY_ID"]
        secret_access_key = os.environ["MY_S3_SECRET_ACCESS_KEY"]

        print(f"Uploading Zarr directory to S3: {concatenated_zarr_path}")

        upload_result = upload_directory_to_s3(
            local_directory_path=concatenated_zarr_path,
            bucket_name=bucket_name,
            endpoint_url=endpoint_url,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            destination_prefix="my_ch9_zarr_data",  # Optional: specify a prefix in the S3 bucket
        )

        print(f"Uploaded to: {upload_result['s3_uri']}")
        return upload_result


    # [END load]

    # [START main_flow]
    show_params()  # Example of a function call within a DAG context
    search_results_dict = extract()
    transform_results_dict = transform(search_results_dict)
    load(transform_results_dict)
    # [END main_flow]


# [START dag_invocation]
dag = tutorial_taskflow_api_demo2()
# [END dag_invocation]

# [END tutorial]
if __name__ == "__main__":

    dag.test()
