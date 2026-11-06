#!/usr/bin/env python3
"""
Prepare 3-hourly MTG FCI Cloud Mask background data for the Extremes DT notebook.

The script:
1. Authenticates with DestinE HDA.
2. Searches the MTG FCI Cloud Mask collection for the forecast period.
3. Selects the MTG granule starting exactly at each 3-hour forecast valid time.
4. Downloads the complete HDA product as a ZIP archive.
5. Extracts the product using the same approach as Notebook 1.
6. Reads cloud_state with Satpy.
7. Resamples each scene onto the same geographic grid used by Notebook 2.
8. Writes one compact NetCDF background dataset for use in Notebook 2.
"""

import json
from datetime import datetime, timedelta, timezone
from getpass import getpass
from pathlib import Path
import zipfile

import destinelab as deauth
import numpy as np
import requests
import xarray as xr
from pyresample.geometry import AreaDefinition
from satpy import Scene


HDA_API_URL = "https://hda.data.destination-earth.eu"
STAC_API_URL = f"{HDA_API_URL}/stac/v2"
COLLECTION_ID = "EO.EUM.DAT.MTG.FCI-CLM"

FORECAST_DATE = "2026-09-18"
FORECAST_HOURS = 48
STEPS = list(range(0, FORECAST_HOURS + 1, 3))
BBOX = [12.5, 42.6, 14.5, 44.6]

FORECAST_START = datetime.fromisoformat(FORECAST_DATE).replace(tzinfo=timezone.utc)
TARGET_TIMES = [
    FORECAST_START + timedelta(hours=step)
    for step in STEPS
]

OUTPUT_PATH = Path(f"mtg_cloud_mask_{FORECAST_DATE}_48h_3hourly.nc")
WORK_DIR = Path("mtg_cloud_mask_downloads")


def get_auth_headers():
    credentials_file = Path.home() / ".dedl" / "credentials"

    if credentials_file.exists():
        with open(credentials_file) as f:
            config = json.load(f)
        username = config["username"]
        password = config["desp_password"]
    else:
        username = input("Please input your DESP username or email: ")
        password = getpass("Please input your DESP password: ")

    auth = deauth.AuthHandler(username, password)
    access_token = auth.get_token()

    if access_token is None:
        raise RuntimeError("Failed to obtain a DEDL/DESP access token.")

    return {"Authorization": f"Bearer {access_token}"}


def search_mtg_products(auth_headers):
    start = TARGET_TIMES[0].strftime("%Y-%m-%dT%H:%M:%SZ")
    end = TARGET_TIMES[-1].strftime("%Y-%m-%dT%H:%M:%SZ")

    search_body = {
        "collections": [COLLECTION_ID],
        "datetime": f"{start}/{end}",
        "bbox": BBOX,
        "limit": 100,
    }

    products = []

    while True:
        response = requests.post(
            f"{STAC_API_URL}/search",
            headers={**auth_headers, "Content-Type": "application/json"},
            json=search_body,
        )
        response.raise_for_status()
        result = response.json()
        products.extend(result.get("features", []))

        next_link = next(
            (link for link in result.get("links", []) if link.get("rel") == "next"),
            None,
        )

        if next_link is None:
            break

        search_body = next_link["body"]

    return products


def select_forecast_products(products):
    selected = {}

    for product in products:
        start_time = product["properties"].get("start_datetime")
        if not start_time:
            continue

        dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

        if dt.minute == 0 and dt.second == 0:
            selected[dt] = product

    current_hour = datetime.now(timezone.utc).replace(
        minute=0, second=0, microsecond=0
    )

    available_times = [time for time in TARGET_TIMES if time <= current_hour]

    missing = [time for time in available_times if time not in selected]
    if missing:
        missing_text = ", ".join(time.isoformat() for time in missing)
        raise RuntimeError(
            f"Missing MTG products for already elapsed forecast times: {missing_text}"
        )

    future_times = [time for time in TARGET_TIMES if time > current_hour]
    if future_times:
        print(
            f"Skipping {len(future_times)} future forecast observation(s) "
            f"after {current_hour.isoformat()}."
        )

    return [selected[time] for time in available_times]


def download_product(product, auth_headers):
    """Download and extract a complete HDA product using the Notebook 1 workflow."""

    item_id = product["id"]
    download_url = product["assets"]["downloadLink"]["href"]

    output_path = WORK_DIR / f"{item_id}.zip"
    extract_path = WORK_DIR / item_id

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Product: {item_id}")
    print(f"Downloading -> {output_path}")

    with requests.get(download_url, headers=auth_headers, stream=True) as response:
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    print(f"Downloaded: {output_path}")

    with zipfile.ZipFile(output_path, "r") as z:
        z.extractall(extract_path)

    output_path.unlink()

    print(f"Extracted: {extract_path}")

    return extract_path


def find_netcdf(extract_path):
    nc_files = list(extract_path.rglob("*.nc"))

    if not nc_files:
        raise RuntimeError(f"No NetCDF file found in {extract_path}")

    return nc_files[0]


def process_product(nc_path, target_area):
    scene = Scene(
        filenames=[str(nc_path)],
        reader="fci_l2_nc",
    )

    scene.load(["cloud_state"])

    resampled = scene.resample(
        target_area,
        resampler="nearest",
    )

    return np.asarray(
        resampled["cloud_state"].values,
        dtype=np.uint8,
    )


def main():
    auth_headers = get_auth_headers()

    print("Searching HDA for MTG FCI Cloud Mask products...")
    products = search_mtg_products(auth_headers)
    print(f"Products returned by HDA: {len(products)}")

    selected = select_forecast_products(products)
    print(f"3-hourly products selected: {len(selected)}")

    target_area = AreaDefinition(
        "roi",
        "ROI",
        "roi",
        {"proj": "longlat", "datum": "WGS84"},
        1000,
        1000,
        tuple(BBOX),
    )

    cloud_states = []
    valid_times = []

    for index, product in enumerate(selected, start=1):
        valid_time = datetime.fromisoformat(
            product["properties"]["start_datetime"].replace("Z", "+00:00")
        )

        print(f"\n[{index:02d}/{len(selected)}] {valid_time.isoformat()}")

        extract_path = download_product(product, auth_headers)
        nc_path = find_netcdf(extract_path)

        print(f"Reading: {nc_path}")

        cloud_states.append(
            process_product(nc_path, target_area)
        )

        valid_times.append(valid_time.replace(tzinfo=None))

    dataset = xr.Dataset(
        {
            "cloud_state": (
                ("time", "y", "x"),
                np.stack(cloud_states),
            )
        },
        coords={
            "time": np.asarray(valid_times, dtype="datetime64[ns]"),
            "latitude": (("y", "x"), target_area.lats),
            "longitude": (("y", "x"), target_area.lons),
        },
        attrs={
            "source": "MTG FCI Cloud Mask via DestinE HDA",
            "collection": COLLECTION_ID,
            "bbox": BBOX,
            "grid": "1000 x 1000 regular latitude/longitude",
            "resampling": "nearest neighbour",
        },
    )

    dataset.to_netcdf(OUTPUT_PATH)

    print()
    print(f"Saved: {OUTPUT_PATH}")
    print(dataset)


if __name__ == "__main__":
    main()
