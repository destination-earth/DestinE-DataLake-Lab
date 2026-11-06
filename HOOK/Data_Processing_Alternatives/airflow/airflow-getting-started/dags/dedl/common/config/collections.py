# collections.py

from typing import List

import requests


def fetch_collection_ids() -> List[str]:
    url = "https://hda.data.destination-earth.eu/stac/v2/collections"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    return [c["id"] for c in data.get("collections", []) if "id" in c]
