import os
import logging
from typing import Literal
from enum import StrEnum

# Can be used if we need the absolute path of the root of the project
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

APP_LOGGER_NAME: str = "app_logger"
APP_LOGGER_FILE_PATH: str = "usergenerated.log"
APP_LOGGER_FILE_TRUNCATE_SIZE: int = 10 * 1024 * 1024
APP_LOGGER_FILE_BACKUP_COUNT: int = 5
APP_LOGGER_LEVEL: int = logging.INFO

# HDA uses stac version 1.0.0 for the moment.
STAC_VERSION: str = "1.0.0"

ITEM_CONFIG_FILE_NAME: str = "item_config.json"
# optional field that determines if the item_config.json file is optional or not in ITEM folders: values true or false
ITEM_CONFIG_OPTIONAL: str = "item_config_optional"

# expected config at collection level to indicate at what level to find Item Folders
ITEM_FOLDER_LEVEL: str = "item_folder_level"
# The different values that are expected. e.g. YYYY means Item Folders are expected to be in the YYYY folders
ITEM_FOLDER_LEVEL_YYYY: str = "YYYY"
ITEM_FOLDER_LEVEL_MM: str = "MM"
ITEM_FOLDER_LEVEL_DD: str = "DD"
# NONE means that we are in a 'simplified' process, any root folder in the data folder becomes an item. Considered not standard - would need approval from DEDL Support
ITEM_FOLDER_LEVEL_NONE: str = "NONE"

# optional config at the collection level (i.e. in collection_config.json) to indicate the keys of additional properties found in suffix of the item folder
# e.g "additional_property_keys": ["model", "period_type"] would indicate that we are expecting item folders to end with the suffix __somemodelname__someperiodtype
# these additional properties are extracted and added to the properties key of the item.
ADDITIONAL_PROPERTY_KEYS: str = "additional_property_keys"

# If this is false, There will be no upload when generate_item_metadata.py is complete. Set to True to upload the whole folder
IS_UPLOAD_S3: bool = False
# If this is False, a check is first made to see if the file already exists in the bucket
IS_OVERWRITE_S3: bool = False
S3_ENDPOINT_URL: str = "https://s3.central.data.destination-earth.eu"
# Standardised bucket names for usergenerated collections e.g. usergenerated-EO.XXX.YYY.ZZZ. In the code we concatenate with the -EO.XXX.YYY.ZZZ
S3_USER_GENERATED_BUCKET_PREFIX: str = "usergenerated-proposal"


class ItemFolderNamingConventionType(StrEnum):
    STANDARD = "standard"
    NON_STANDARD_1 = "non_standard_1"

# Default Item Folder Naming Convention: STANDARD
ITEM_FOLDER_NAMING_CONVENTION_TYPE = ItemFolderNamingConventionType.STANDARD

