import pystac
import json
from pathlib import Path
import logging
import re
import os
from collections import OrderedDict
from typing import List, Dict, Any, Optional

from config import APP_LOGGER_NAME, ROOT_DIR

from pystac import Collection
from pystac.validation import JsonSchemaSTACValidator, set_validator
from pystac.validation.schema_uri_map import DefaultSchemaUriMap
from pystac.errors import STACValidationError
from pystac import get_stac_version
from pystac.version import set_stac_version


# Get App Logger
logger = logging.getLogger(APP_LOGGER_NAME)


# Custom StacIO to log read operations
class LoggingStacIO(pystac.StacIO.default().__class__):
    """Custom STAC IO class for logging read operations."""

    def read_text(self, uri: str) -> str:
        """Log STAC file read operations."""
        logger.debug(f"STAC IO is reading from: {uri}")
        return super().read_text(uri)


pystac.StacIO.set_default(lambda: LoggingStacIO())


def print_validation_errors(e: STACValidationError, max_depth: int = 2) -> None:
    """
    Recursively print all validation errors with their JSON path.

    Args:
        e: The STACValidationError raised during validation
        max_depth: How deeply to walk nested contexts (e.g. context-of-context)
    """

    def walk_errors(errors: list, depth: int = 0) -> None:
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
    collection_dict: Dict[str, Any],
    required_fields: List[str],
    require_non_null: bool = True,
) -> None:
    """
    Check for presence (and optional non-nullness) of fields in a PySTAC Collection.
    
    Args:
        collection_dict: The collection dictionary to check
        required_fields: List of required field names
        require_non_null: Whether fields must be non-null
        
    Raises:
        ValueError: If any required fields are missing or null
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


def cleanup_json_file(file_path: str) -> None:
    """
    Clean up a JSON file by removing self and root links and re-indenting.
    
    Args:
        file_path: Path to the JSON file to clean up
    """
    try:
        # Open and load the original JSON data
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Clean up the 'links' field if present
        if "links" in data and isinstance(data["links"], list):
            data["links"] = [
                link
                for link in data["links"]
                if link.get("rel") not in ["root", "self"]
            ]

        # Re-save the data with indentation
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        print(f"Reindented JSON file saved to: {file_path}")
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error processing file: {e}")


def load_and_validate_collection(
    collection_path: Path,
    expected_collection_id: str,
    save_reordered_collection: bool = False,
    is_compare_expected_id: bool = True,
) -> Optional[Collection]:
    """
    Load and validate a STAC collection from a JSON file.

    Args:
        collection_path: Path to the JSON file containing the STAC collection
        expected_collection_id: Expected ID of the collection
        save_reordered_collection: If True, saves a reordered version
        is_compare_expected_id: If True, validates that collection ID matches expected

    Returns:
        The loaded and validated STAC collection, or None if loading/validation fails
    """
    # Set the STAC version to 1.0.0
    set_stac_version("1.0.0")

    try:
        with open(collection_path, "r", encoding="utf-8") as f:
            collection_dict = json.load(f)

        collection: Collection = Collection.from_dict(collection_dict)
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
                "providers",
            ]

            # Check Obligatory fields which should not have null values
            check_collection_fields(collection_dict, important_fields)

            # Check that the collection.id matches the expected format
            if not bool(re.fullmatch(r"[A-Z._]+", collection.id)):
                raise ValueError(
                    f"The collection.id: '{collection.id}' from the Collection file does not match "
                    f"the expected format. It should only contain uppercase letters, dots, and underscores. "
                    f"e.g. 'EO.AAA.DAT.BBB_CCC'"
                )

            # Check that the collection.id matches the expected_collection_id
            if is_compare_expected_id and collection.id != expected_collection_id:
                raise ValueError(
                    f"The collection.id: '{collection.id}' from the Collection file does not correspond "
                    f"to the expected_collection_id:'{expected_collection_id}'"
                )

            # Check that the collection is valid against any jsonschemas
            collection.validate()

            # Save a reordered normalised version of the collection
            if save_reordered_collection:
                # Save the reordered collection to a new file
                collection.set_self_href("collection_reordered.json")
                collection.save_object()
                cleanup_json_file("collection_reordered.json")

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


def load_config(
    config_file_path: Path, is_config_file_optional: bool = False
) -> Dict[str, Any]:
    """
    Load and return configuration data from a JSON file.

    Args:
        config_file_path: Path to the configuration file
        is_config_file_optional: If True, returns empty dict if file not found

    Returns:
        Dictionary containing the configuration data

    Raises:
        FileNotFoundError: If the config file does not exist and is not optional
    """
    # Check if the config file exists
    if not config_file_path.exists():
        if is_config_file_optional:
            # It's ok not to have a config file
            logger.info(
                f"Optional Config file not found: {config_file_path}. "
                f"Returning empty dictionary."
            )
            return {}
        else:
            raise FileNotFoundError(f"Config file not found: {config_file_path}")

    # Load the JSON data from the config file
    with open(config_file_path, "r", encoding="utf-8") as f:
        config_data = json.load(f)

    return config_data


def get_config_value(
    config_list: List[Dict[str, Any]],
    search_key: str,
    is_search_key_optional: bool = False,
) -> Optional[Any]:
    """
    Retrieve a value from a configuration list based on the search key.

    Args:
        config_list: List of dictionaries containing configuration key-value pairs
        search_key: The key to search for in the configuration list
        is_search_key_optional: If True, returns None instead of raising error

    Returns:
        The value associated with the search key if found, otherwise None

    Raises:
        KeyError: If the key is not found and is not optional
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
    Iterate through all JSON files in a folder and sort asset keys in STAC Items.

    Writes the updated content back to the original file with assets sorted alphabetically.

    Args:
        folder_path: Path to the folder containing STAC Item JSON files
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
                    # Sort assets alphabetically
                    data["assets"] = OrderedDict(sorted(data["assets"].items()))

                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)

                    print(f"✔ Sorted assets in: {file_path}")
                else:
                    logger.debug(f"Skipped (not a STAC Item): {file_path}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
