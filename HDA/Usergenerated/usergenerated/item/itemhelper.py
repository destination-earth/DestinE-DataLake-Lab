import pystac
import os
from pathlib import Path
import re
import magic
from datetime import datetime


def get_media_type(file_path):
    """
    Get the media type from a file path.
    This is inferred here from the file extension, but you can modify for more complex needs.

    Parameters:
    file_path (Path): The file path we are trying to get the media type (mime type) from

    Returns:
    The inferred commonly used MIME type

    """

    # guessed_mime_type = guess_mime_type_advanced(file_path)

    # Get the file extension
    _, ext = os.path.splitext(file_path)

    # Define a mapping from file extension to MediaType
    extension_to_media_type = {
        ".tif": pystac.MediaType.COG,
        ".png": pystac.MediaType.PNG,
        ".jpg": pystac.MediaType.JPEG,
        ".json": pystac.MediaType.JSON,
        ".html": pystac.MediaType.HTML,
        ".txt": pystac.MediaType.TEXT,
        ".xml": pystac.MediaType.XML,
        ".pdf": pystac.MediaType.PDF,
        # Add more mappings as needed
        ".nc": pystac.MediaType.NETCDF
    }

    # Get the media type based on the file extension
    media_type = extension_to_media_type.get(ext.lower())

    # Check if the media type is valid
    if media_type is None:
        raise ValueError(f"Unsupported MediaType for file extension: {ext}")

    return media_type


def get_asset_role(
    media_type: str,
    asset_href: Path,
    thumbnail_regex: str,
    overview_regex: str,
):
    """
    Here we give an example of using media_type to determine the role of the asset.
    This may be more complex however, according to your data.
    """

    # https://github.com/radiantearth/stac-spec/blob/master/commons/assets.md#asset-object

    data = [
        pystac.MediaType.COG,
        pystac.MediaType.FLATGEOBUF,
        pystac.MediaType.GEOPACKAGE,
        pystac.MediaType.GEOTIFF,
        pystac.MediaType.HDF,
        pystac.MediaType.HDF5,
        pystac.MediaType.JPEG,
        pystac.MediaType.JPEG2000,
        pystac.MediaType.PARQUET,
        pystac.MediaType.PNG,
        pystac.MediaType.TIFF,
        pystac.MediaType.KML,
        pystac.MediaType.ZARR,
        pystac.MediaType.NETCDF,
    ]
    metadata = [
        pystac.MediaType.GEOJSON,
        pystac.MediaType.HTML,
        pystac.MediaType.JSON,
        pystac.MediaType.TEXT,
        pystac.MediaType.XML,
        pystac.MediaType.PDF,
    ]

    if re.match(thumbnail_regex, asset_href.name):
        return ["thumbnail"]
    if re.match(overview_regex, asset_href.name):
        return ["overview"]
    elif media_type in data:
        return ["data"]
    elif media_type in metadata:
        return ["metadata"]
    else:
        raise ValueError(
            f"Could not determine asset role for asset '{asset_href.name}'."
        )


def get_item_properties(item_id: str, collection_id: str):
    """
    item_id expected in form EO.XXX.YYY.ZZZ_20241116T000000_20241116T115959 i.e.  [Collection_ID]_[start_datetime/datetime]_[end_datetime]
    item_id can also take form EO.XXX.YYY.ZZZ_20241116T000000 i.e.  [Collection_ID]_[datetime]

    We should infer the datetime from the start_datetime element.
    if both are present the start_datetime and end_datetime are set AND the datetime is set from start_datetime
    if just the start_datetime is present then the interval is not set and datetime is set only
    """

    # string suffixed like this are ignored __LISBON
    # these could be picked up in the data preparation step to add additional metadata if necessary
    if '__' in item_id:
        additional_property_parts = item_id.split("__")
        # only consider the first element of string before __
        item_id = additional_property_parts[0]
    
    # remove the collection_id prefix from the item_id, so that we can extract the datetime
    # e.g. EO.XXX.YYY.ZZZ_20241115T000000_20241115T235959 to 20241115T000000_20241115T235959
    # Note: We add 1 to the length of the collection_id to account for the following underscore
    if item_id.startswith(collection_id):
        item_id = item_id[len(collection_id) + 1:]
    else:
        raise ValueError("Item ID does not start with the Collection ID.")
    
    parts = item_id.split("_")

    # Check if the number of parts is valid we expect 1 or 2 parts
    if len(parts) not in [1, 2]:
        raise ValueError("Invalid number of parts in item_id. Expected 1 or 2 parts.")

    # Extract start and end parts safely
    start = parts[0] if len(parts) >= 1 else None
    end = parts[1] if len(parts) == 2 else None

    properties = {}
    item_datetime: datetime = None

    # e.g. EO.XXX.YYY.ZZZ_20241115T000000_20241115T235959 there is a start and end
    if start and end:

        # Parse the original string into a datetime object
        start_datetime = datetime.strptime(start, "%Y%m%dT%H%M%S")
        # Format the datetime object to the desired string format
        formatted_start_datetime = start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Parse the original string into a datetime object
        end_datetime = datetime.strptime(end, "%Y%m%dT%H%M%S")
        # Format the datetime object to the desired string format
        formatted_end_datetime = end_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

        properties["start_datetime"] = formatted_start_datetime
        properties["end_datetime"] = formatted_end_datetime

        item_datetime = start_datetime

    elif start:
        # e.g. EO.XXX.YYY.ZZZ_20241115T000000

        # Parse the original string into a datetime object
        item_datetime = datetime.strptime(start, "%Y%m%dT%H%M%S")

    else:
        raise ValueError("Item must have a start and end datetime.")

    return (item_datetime, properties)


def guess_mime_type_advanced(file_path):
    """
    Guess the MIME type of a file based on its content using python-magic.

    Parameters:
    file_path (str): The path to the file.

    Returns:
    str: The guessed MIME type.
    """
    mime = magic.Magic(mime=True)
    return mime.from_file(file_path)
