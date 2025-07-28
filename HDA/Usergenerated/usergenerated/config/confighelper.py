import pystac
import json
from pathlib import Path
import logging
import re
import os
from collections import OrderedDict

from config import APP_LOGGER_NAME, ROOT_DIR

from typing import List, Dict, Any
from pystac import Collection
from pathlib import Path
from pystac.validation import JsonSchemaSTACValidator, set_validator
from pystac.validation.schema_uri_map import DefaultSchemaUriMap
from pystac.errors import STACValidationError
from pystac import get_stac_version
from pystac.version import set_stac_version


# Get App Logger
logger = logging.getLogger(APP_LOGGER_NAME)


# Custom StacIO to log read operations
class LoggingStacIO(pystac.StacIO.default().__class__):
    def read_text(self, uri):
        print(f"STAC IO is reading from: {uri}")
        return super().read_text(uri)


pystac.StacIO.set_default(lambda: LoggingStacIO())


def print_validation_errors(e: STACValidationError, max_depth=2):
    """
    Recursively print all validation errors with their JSON path.

    Parameters:
    - e: The STACValidationError raised during validation.
    - max_depth: How deeply to walk nested contexts (e.g. context-of-context).
    """

    def walk_errors(errors, depth=0):
        for err in errors:
            indent = "  " * depth
            loc = "/".join(map(str, err.path)) or "(root)"
            print(f"{indent}❌ {err.message} at {loc}")
            if depth < max_depth and getattr(err, "context", None):
                walk_errors(err.context, depth + 1)

    print("🔎 STAC validation failed with the following errors:")
    errors = e.source if isinstance(e.source, list) else [e.source]
    walk_errors(errors)


def check_collection_fields(
    collection_dict: Dict, required_fields: List[str], require_non_null: bool = True
) -> None:
    """
    Checks for presence (and optional non-nullness) of fields in a PySTAC Collection.
    Raises ValueError if any issues are found.
    """
    issues = []

    for field in required_fields:
        if field not in collection_dict:
            issues.append(f"Missing field: {field}")
        elif require_non_null and collection_dict[field] is None:
            issues.append(f"Field '{field}' is null")

    if issues:
        raise ValueError("Invalid STAC Collection:\n" + "\n".join(issues))
    else:
        print("Collection passed all field checks.")


def load_and_validate_collection(
    collection_path, expected_collection_id, save_reordered_collection: bool = False
):
    """
    Load and validate a STAC collection from a JSON file.
    Also checks the expected_collection_id
    and optionally saves a reordered version of the collection.

    Parameters:
    collection_path (str): The path to the JSON file containing the STAC collection.
    expected_collection_id (str): The expected ID of the collection.
    save_reordered_collection (bool): If True, saves a reordered version of the collection.

    Returns:
    pystac.Collection: The loaded and validated STAC collection, or None if loading or validation fails.
    """

    # Set the STAC version to 1.0.0
    set_stac_version("1.0.0")

    try:
        with open(collection_path, "r", encoding="utf-8") as f:
            collection_dict = json.load(f)

        collection: pystac.Collection = pystac.Collection.from_dict(collection_dict)
        print(f"PySTAC version: {get_stac_version()}")

        if collection is not None:
            logger.debug(f"Successfully loaded stac collection: {collection.id}")

            # Define the obligatory fields for Destination Earth Data Lake Collections
            important_fields = [
                "id",
                "title",
                "description",
                "dedl:short_description",
                "license",
                "extent",
                "links",
                "keywords",
                "stac_extensions",
                "providers"
            ]

            ##########################################################################

            # Check Obligatory fields which should not have null values
            check_collection_fields(collection_dict, important_fields)

            # Check that the collection.id matches the expected format
            if not bool(re.fullmatch(r"[A-Z._]+", collection.id)):
                raise ValueError(
                    f"The collection.id: '{collection.id}' from the Collection file does not match the expected format. It should only contain uppercase letters, dots, and underscores. e.g. 'EO.AAA.DAT.BBB_CCC'"
                )

            # Check that the collection.id matches the expected_collection_id
            if collection.id != expected_collection_id:
                raise ValueError(
                    f"The collection.id: '{collection.id}' from the Collection file does not correspond to the expected_collection_id:'{expected_collection_id}'"
                )

            ##########################################################################

            # Check that the collection is valid against any jsonschemas
            collection.validate()

            # Save a reordered normalised version of the collection
            if save_reordered_collection:
                # Save the reordered collection to a new file
                collection.set_self_href("collection_reordered.json")
                collection.save_object()

            logger.info(f"Successfully validated stac collection: {collection.id}")
        else:
            logger.error("Failed to load the collection.")

        return collection

    except STACValidationError as e:
        print_validation_errors(e)
    except FileNotFoundError:
        logger.error(f"Error: The file {collection_path} was not found.")
    except json.JSONDecodeError:
        logger.error(f"Error: Failed to decode JSON from the file {collection_path}.")

    return None


def load_config(config_file_path: Path):
    """
    Load and return the configuration data from a JSON file.

    Parameters:
    config_file_path (Path): The path to the configuration file.

    Returns:
    dict: The configuration data loaded from the file.

    Raises:
    FileNotFoundError: If the config file does not exist.
    """
    # Check if the config file exists
    if not config_file_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file_path}")

    # logger.info(f"{os.path.join(ROOT_DIR, config_file_path)}")

    # Load the JSON data from the config file
    with open(config_file_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    return config_data


def get_config_value(config_list, search_key, is_search_key_optional: bool = False):
    """
    Retrieve the value from the configuration list based on the search key.

    Parameters:
    config_list (list): A list of dictionaries containing configuration key-value pairs.
    search_key (str): The key to search for in the configuration list.

    Returns:
    The value associated with the search key if found, otherwise None.
    """
    for config in config_list:
        if search_key in config:
            return config[search_key]

    if not is_search_key_optional:
        raise KeyError(f"Key '{search_key}' not found in any of the config files.")
    else:
        return None


def sort_item_assets_in_folder(folder_path: str) -> None:
    """
    Iterates through all JSON files in a folder, sorts asset keys in STAC Items,
    and writes the updated content back to the original file.

    Args:
        folder_path (str): The path to the folder containing STAC Item JSON files.
    """
    for root, _, files in os.walk(folder_path):
        for file in files:
            if not file.endswith(".json"):
                continue

            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if data.get("type") == "Feature" and "assets" in data:
                    # original_keys = list(data["assets"].keys())
                    data["assets"] = OrderedDict(sorted(data["assets"].items()))

                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)

                    print(f"✔ Sorted assets in: {file_path}")
                else:
                    print(f"ℹSkipped (not a STAC Item): {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
