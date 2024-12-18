import pystac
import json
import os
from pathlib import Path
import logging

from config import APP_LOGGER_NAME, ROOT_DIR

# Get App Logger
logger = logging.getLogger(APP_LOGGER_NAME)

def load_and_validate_collection(collection_path, expected_collection_id):
    """
    Load and validate a STAC collection from a JSON file.
    Also checks the expected_collection_id

    Parameters:
    collection_path (str): The path to the JSON file containing the STAC collection.

    Returns:
    pystac.Collection: The loaded and validated STAC collection, or None if loading or validation fails.
    """
    try:
        with open(collection_path, "r", encoding="utf-8") as f:
            collection_dict = json.load(f)

        collection: pystac.Collection = pystac.Collection.from_dict(collection_dict)

        if collection is not None:
            logger.debug(f"Successfully loaded stac collection: {collection.id}")
            # Check that the collection is valid against any jsonschemas
            collection.validate()
            logger.info(f"Successfully validated stac collection: {collection.id}")
        else:
            logger.error("Failed to load the collection.")

        if collection.id != expected_collection_id:
            raise ValueError(
                f"The collection.id: '{collection.id}' from the Collection file does not correspond to the expected_collection_id:'{expected_collection_id}'"
            )

        return collection
    except FileNotFoundError:
        logger.error(f"Error: The file {collection_path} was not found.")
        return None
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
