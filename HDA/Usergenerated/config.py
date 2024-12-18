import os
import logging

# Can be used if we need the absolute path of the root of the project
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

APP_LOGGER_NAME = "app_logger"
APP_LOGGER_FILE_PATH = "usergenerated.log"
APP_LOGGER_FILE_TRUNCATE_SIZE = 10 * 1024 * 1024
APP_LOGGER_FILE_BACKUP_COUNT = 5
APP_LOGGER_LEVEL = logging.INFO

ITEM_CONFIG_FILE_NAME = "item_config.json"

# expected config at collection level to indicate at what level to find Item Folders
ITEM_FOLDER_LEVEL = "item_folder_level"
# The different values that are expected. e.g. YYYY means Item Folders are expected to be in the YYYY folders
ITEM_FOLDER_LEVEL_YYYY = "YYYY"
ITEM_FOLDER_LEVEL_MM = "MM"
ITEM_FOLDER_LEVEL_DD = "DD"

# If this is false, There will be no upload when generate_item_metadata.py is complete. Set to True to uplad the whole folder
IS_UPLOAD_S3 = False
# If this is False, a check is first made to see if the file already exists in the bucket
IS_OVERWRITE_S3 = False
S3_ENDPOINT_URL = "https://s3.central.data.destination-earth.eu"
# Standardised bucket names for usergenerated collections e.g. usergenerated-EO.XXX.YYY.ZZZ. In the code we concatenate with the -EO.XXX.YYY.ZZZ
S3_USER_GENERATED_BUCKET_PREFIX = "usergenerated-proposal"



