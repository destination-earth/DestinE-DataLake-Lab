import logging
import os
import json
import pystac
from datetime import datetime
from pathlib import Path
import pystac.utils
from shapely.geometry import box, mapping


from config import (
    APP_LOGGER_NAME,
    IS_OVERWRITE_S3,
    IS_UPLOAD_S3,
    ITEM_CONFIG_FILE_NAME,
    ITEM_FOLDER_LEVEL,
    ITEM_FOLDER_LEVEL_DD,
    ITEM_FOLDER_LEVEL_MM,
    ITEM_FOLDER_LEVEL_YYYY,
    S3_ENDPOINT_URL,
    S3_USER_GENERATED_BUCKET_PREFIX,
)

import usergenerated.logging_config # import must come before other modules in this project so that logging setup correctly
from usergenerated import datetools
from usergenerated.config import confighelper
from usergenerated.item import itemhelper
from usergenerated.s3tools import S3Tools


class ItemGenerator:

    def __init__(self, collection_id: str):

        # instance collection_id
        self.collection_id = collection_id

        # Path to root of all collection related data: used when uploading to S3 bucket
        self.collection_root = Path(collection_id)

        # Path to collection.json STAC file
        self.collection_path = Path(f"{collection_id}/metadata/collection.json")
        # Path to collection level config file, containing global config when generating Item metadata
        self.collection_config_path = Path(
            f"{collection_id}/metadata/collection_config.json"
        )
        # Path to expected folder where STAC Item (feature) metadata will be generated
        self.items_root = Path(f"{collection_id}/metadata/items")
        # Path to expected data folder which is used to generate the Item metadata
        self.data_root = Path(f"{collection_id}/data")

        ##### Initialise S3Tools object to handle S3 interaction

        self.is_overwrite_s3 = IS_OVERWRITE_S3
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise ValueError("Bucket Credentials not set in .env file")

        self.s3tools = S3Tools(
            self.aws_access_key_id, self.aws_secret_access_key, self.is_overwrite_s3
        )

    def run(self):

        ##### Load and Validate the Collection #####
        collection = confighelper.load_and_validate_collection(
            self.collection_path, self.collection_id
        )

        ###### load the collection config #####
        collection_config = confighelper.load_config(self.collection_config_path)
        logger.debug(f"collection_config:{collection_config}")

        # List to store the folder names found in YYYY/MM/DD folders (i.e. the folders at this level represent Items)
        item_folder_paths = []

        # ITEM Folders are expected by defulat to be in a folder representing a day DD
        if ITEM_FOLDER_LEVEL not in collection_config:
            collection_config[ITEM_FOLDER_LEVEL] = ITEM_FOLDER_LEVEL_DD

        # Determine at which level Item folders are found in the structure YYYY/MM/DD and get list of item_folder_paths.
        # If not defined in collection_config default is DD
        if collection_config[ITEM_FOLDER_LEVEL] == ITEM_FOLDER_LEVEL_DD:

            # Iterate over 'data' root folder : expecting YYYY folders
            for year_folder in self.data_root.iterdir():
                if year_folder.is_dir():
                    # Iterate over YYYY folders : expecting MM folders
                    for month_folder in year_folder.iterdir():
                        if month_folder.is_dir():
                            # Iterate over MM folders : expecting DD folders
                            for day_folder in month_folder.iterdir():
                                if day_folder.is_dir():
                                    # Iterate over DD folders : expecting Item folders
                                    for item_folder in day_folder.iterdir():
                                        if item_folder.is_dir():
                                            # Add the item folder to the list
                                            item_folder_paths.append(item_folder)

        elif collection_config[ITEM_FOLDER_LEVEL] == ITEM_FOLDER_LEVEL_MM:
            # Iterate over 'data' root folder : expecting YYYY folders
            for year_folder in self.data_root.iterdir():
                if year_folder.is_dir():
                    # Iterate over YYYY folders : expecting MM folders
                    for month_folder in year_folder.iterdir():
                        if month_folder.is_dir():
                            # Iterate over MM folders : expecting Item folders
                            for item_folder in month_folder.iterdir():
                                if item_folder.is_dir():
                                    # Add the item folder to the list
                                    item_folder_paths.append(item_folder)

        # Iterate over the YYYY/MM/DD structure in the data folder : expecting item folders according to configuration
        elif collection_config[ITEM_FOLDER_LEVEL] == ITEM_FOLDER_LEVEL_YYYY:
            # Iterate over 'data' root folder : expecting YYYY folders
            for year_folder in self.data_root.iterdir():
                if year_folder.is_dir():
                    # Iterate over YYYY folders : expecting Item folders
                    for item_folder in year_folder.iterdir():
                        if item_folder.is_dir():
                            # Add the item folder to the list
                            item_folder_paths.append(item_folder)

        else:
            raise ValueError(
                "Unexpected configuration for ITEM_FOLDER_LEVEL. expected values YYYY, MM or DD"
            )

        # Iterate over Item folders to create Item files
        for item_folder_path in item_folder_paths:
            self.create_item(item_folder_path, collection, collection_config)

        if IS_UPLOAD_S3:
            # Upload whole folder to S3
            self.s3tools.upload_folder_to_s3(
                str(self.collection_root),
                S3_ENDPOINT_URL,
                f"{S3_USER_GENERATED_BUCKET_PREFIX}-{self.collection_id}",
            )

    def create_item(
        self,
        item_folder_path: Path,
        collection: pystac.Collection,
        collection_config: dict,
    ):
        """
        Function to create an item for each data file

        Parameters:
        item_folder_path (Path): Path to the folder containing the item data files.
        collection (pystac.Collection): The STAC collection to which the item belongs.
        collection_config (dict): Configuration dictionary for the collection.

        Returns:
        pystac.Item: The created STAC item.
        """
        try:
            # Load item-specific configuration from a file in the item folder
            item_config = confighelper.load_config(
                item_folder_path / ITEM_CONFIG_FILE_NAME
            )
            logger.debug(item_config)

            # Combine item and collection configuration, with item-specific values overriding collection values
            config_list = [item_config, collection_config]

            ########## Initialize Variables For Item ##########

            logger.info(f"item_folder_path:{item_folder_path}")

            # Extract item ID and date components from the folder path
            item_id = item_folder_path.name
            item_folder_path_parts = str(item_folder_path).split(os.path.sep)
            collection_id = item_folder_path_parts[0]
            # year folder will always be present
            year_from_folder_path = item_folder_path_parts[2]

            # month folder will only be present if items at MM or DD level or not specified (default DD)
            if (
                not collection_config[ITEM_FOLDER_LEVEL]
                or collection_config[ITEM_FOLDER_LEVEL] == ITEM_FOLDER_LEVEL_MM
                or collection_config[ITEM_FOLDER_LEVEL] == ITEM_FOLDER_LEVEL_DD
            ):
                month_from_folder_path = item_folder_path_parts[3]
            else:
                month_from_folder_path = "01"

            # day folder will only be present if items at DD level or not specified (default DD)
            if (
                not collection_config[ITEM_FOLDER_LEVEL]
                or collection_config[ITEM_FOLDER_LEVEL] == ITEM_FOLDER_LEVEL_DD
            ):
                day_from_folder_path = item_folder_path_parts[4]
            else:
                day_from_folder_path = "01"

            logger.info(
                f"item_id:{item_id}, collection_id:{collection_id}, "
                f"year_from_folder_path:{year_from_folder_path}, "
                f"month_from_folder_path:{month_from_folder_path}, "
                f"day_from_folder_path:{day_from_folder_path}"
            )

            # Convert date components to a datetime object
            datetime_from_folder_path = datetime(
                int(year_from_folder_path),
                int(month_from_folder_path),
                int(day_from_folder_path),
            )

            # Get datetime object and date related properties from the item ID
            (item_datetime, item_properties) = itemhelper.get_item_properties(item_id)

            # Update item_properties with additional properties if they exist
            item_properties.update(
                confighelper.get_config_value(config_list, "properties", True) or {}
            )

            # Ensure the folder date matches the item ID date : Sanity Check
            datetools.is_same_day(datetime_from_folder_path, item_datetime)

            # Retrieve bounding box from the configuration : Normally Item Specific i.e. in item_config.json
            bbox = confighelper.get_config_value(config_list, "bbox", True)

            # Create a polygon from the bounding box and convert to GeoJSON
            if bbox:
                polygon = box(*bbox)
                geometry = mapping(polygon)
            else:
                geometry = None

            ####################

            # Create the STAC item
            item = pystac.Item(
                id=item_id,
                geometry=geometry,
                bbox=bbox,
                datetime=item_datetime,
                properties=item_properties,
            )

            ####################

            # Gather all file paths in the item folder and subfolders
            asset_paths = [
                file for file in item_folder_path.rglob("*") if file.is_file()
            ]

            # Process each file and add as an asset to the item
            for asset_path in asset_paths:

                asset_href_data_root = Path(*asset_path.parts[1:])

                # Compute the relative href
                asset_href = asset_path.relative_to(item_folder_path)
                logger.info(f"asset_href:{asset_href}")

                # Skip files listed in the ignore list from the configuration
                item_asset_ignore_list = confighelper.get_config_value(
                    config_list, "item_asset_ignore_list"
                )
                if asset_href.name not in item_asset_ignore_list:
                    # Determine the MIME type of the asset
                    media_type = itemhelper.get_media_type(asset_path)

                    # Get regex patterns for thumbnails and overviews
                    thumbnail_regex = confighelper.get_config_value(
                        config_list, "thumbnail_regex"
                    )
                    overview_regex = confighelper.get_config_value(
                        config_list, "overview_regex"
                    )

                    # Add the asset to the item
                    item.add_asset(
                        key=str(asset_href),
                        asset=pystac.Asset(
                            href=str(asset_href_data_root),
                            media_type=media_type,
                            roles=itemhelper.get_asset_role(
                                media_type, asset_href, thumbnail_regex, overview_regex
                            ),
                        ),
                    )

            # Set collection and item self links
            collection.set_self_href(
                f"https://hda.data.destination-earth.eu/stac/collections/{collection_id}"
            )
            item.set_collection(collection)
            item.set_self_href(
                f"https://hda.data.destination-earth.eu/stac/collections/{collection_id}/items/{item_id}"
            )

            # Ensure the items_root directory exists
            self.items_root.mkdir(parents=True, exist_ok=True)

            # Save the item metadata to a JSON file
            item_path = self.items_root / f"{item.id}.json"
            with open(item_path, "w") as f:
                json.dump(item.to_dict(), f, indent=4)

            logger.info(f"Item metadata saved to {item_path}\n")
            return item

        except Exception as e:
            logger.error(f"Error creating item: {e}")
            return None


#################### START ####################

if __name__ == "__main__":

    # Get App Logger
    logger = logging.getLogger(APP_LOGGER_NAME)

    # The collection_id expects a folder with this id containing data and metadata
    collection_id = "EO.XXX.YYY.ZZZ"

    # Initialise ItemGenerator to create Item (Feature) metadata associated with the Collection and Data
    item_generator = ItemGenerator(collection_id)
    item_generator.run()
