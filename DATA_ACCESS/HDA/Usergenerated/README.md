# User Generated Data - Process

- This project demonstrates the integration of a **User Generated** Collection into Destination Earth Data Lake - HDA (Harmonised Data Access)
    - Using this project to propose **new data** assumes you have already contacted the Destination Earth Data Lake Support Team and that your proposal has been accepted by the **Data Lake - Review Board**.
    - **Note**: Proposing new data is a manual process, and requires review with the **Data Lake - Review Board**. For this reason data cannot be continually updated. Each update will require a new request.


# Overview

At a high level the steps involved in preparing a **User Generated Collection** (i.e. a Collection contributed by DestinE Users) are:


- Describe your collection in a **STAC Collection** file
- Group/Move your Data assets into the expected structure
- Generate **STAC Item** metadata using the provided helper code in this project
- Deliver your prepared collection to an object storage S3 Bucket ready for review

> The full description of steps (options) and process are found at [DestinE Data Lake - Promote User Data to become DestinE data](https://destine-data-lake-docs.data.destination-earth.eu/en/latest/dedl-discovery-and-data-access/User-Generated-Data/Promote-user-data-to-become-DestinE-data/Promote-user-data-to-become-DestinE-data.html) 


> A full example of an expected deliverable for a **User Generated** Collection and associated Items is found in the folder **EO.XXX.YYY.ZZZ** in this project. 

> Helper code found here (entry point generate_item_metadata.py) helps you prepare your data in the expected format.

# Goal of this Project

The goal of this project is to help you prepare your data, ready for submission to the **Data Lake - Review Board**

- At a high-level, you will be expected to provide

  - A root folder whose name is the same as the *collection id* that you were provided with by the **Data Lake - Review Board**, e.g. **EO.XXX.YYY.ZZZ** or **EO.XXX.YYY.ZZZ_ZZZ**
    - **The collection id** uses UPPER-CASE letters separated by **'.'** and uderscores **_**
    - The folder should contain
        - a **metadata** subfolder, containing STAC 'Collection' and 'Item' metatdata
        - a **data** folder (YYYY/MM/DD) containing the data associated with 'Items' normally structured in folders YYYY/MM/DD (folder representing year, month, day that data is associated with)
            - Note: Depending on the granularity of your data the Item folders can be found at either the YYYY, MM or DD level (e.g. data that is specific to a given day would be found in the DD folder)

> As noted previously, the full description of steps (options) and process are found at [DestinE Data Lake - Promote User Data to become DestinE data](https://destine-data-lake-docs.data.destination-earth.eu/en/latest/dedl-discovery-and-data-access/User-Generated-Data/Promote-user-data-to-become-DestinE-data/Promote-user-data-to-become-DestinE-data.html) 



## Generating Item Level Metadata

- Given you now have a folder e.g. **EO.XXX.YYY.ZZZ** with **Collection** metadata and **data** in the expected structure, the file *generate_item_metadata.py* gives an example of generating the expected Item metadata.

    - **generate_item_metadata.py** is intended to be a generic python script ready to navigate through the prepared data and then generate STAC Item metadata appropriate for the collection and DEDL HDA.
        - **Note**: However, minor adjustments can be expected according to the specificities of your data

    - When this script is launched the last step uploads the prepared data to a private bucket that you will have been provided with following successful review by the **Data Lake - Review Board**. 
        - The bucket name is standardised and should take this format 'usergenerated-proposal-[your collection id]'
            - e.g. usergenerated-proposal-EO.XXX.YYY.ZZZ (case sensitive)
            - If the bucket name is different from this expected format a small modification to the code/configuration will be necessary.
        - The upload requires that you have created a **.env** file at the root of the project. This should be configured with the credentials passed to you.

```bash

# example of .env file at root of project. generate_item_metadata.py will need these credentials to push your Collection (data and metadata) to the configured private bucket.

AWS_ACCESS_KEY_ID="[Replace with your credentials access_key_id]"
AWS_SECRET_ACCESS_KEY="[Replace with your credentials secret_access_key]"

```

## Pre-requisites

- In order to provide data and metadata in the expected format, you will likely need a VM with adequate storage to allow you to:
    - Manipulate/Move files into the expected folders
    - Generate preliminary item specific metadata (See item_config.json) that will later be used to generate the final STAC Item metadata.



# STAC Collection and Item Definitions


## Collection - Definition

- https://stacspec.org/en/about/stac-spec/ Collection


    > A STAC Collection provides additional information about a spatio-temporal collection of data. It extends Catalog directly, layering on additional fields to enable description of things like the spatial and temporal extent of the data, the license, keywords, providers, etc. It in turn can easily be extended for additional collection level metadata. It is used standalone by parts of the STAC community, as a lightweight way to describe data holdings.

## Item - Definition

- https://stacspec.org/en/about/stac-spec/ Item

    > Fundamental to any STAC, a STAC Item represents an atomic collection of inseparable data and metadata. A STAC Item is a GeoJSON feature and can be easily read by any modern GIS or geospatial library. The STAC Item JSON specification includes additional fields for:

        - the time the asset represents
        - a thumbnail for quick browsing
        - asset links, links to the described data
        - relationship links, allowing users to traverse other related STAC Items



# metadata > collection-config.json

## Options

```python

# The file collection_config.json found in the path EO.XXX.YYY.ZZZ/metadata/collection_config.json
# Defines at a high level

{
    "id": "EO.XXX.YYY.ZZZ",                         # Collection ID
    "item_asset_ignore_list": ["item_config.json"], # Any files to ignore in the ITEM folders when generating metadata
    "item_config_optional": false,                  # Optional field: false by default. Determines whether the item_config.json file in ITEM folders is optional or not.
    "item_folder_level": "DD",                      # Where to exptect the ITEM folders. Possible values (YYYY, MM, DD, NONE)
    "thumbnail_regex": "^thumbnail",                # Regex of files in the ITEM folder that represent the 'thumbnail' of the Item (if any)
    "overview_regex": "^overview",                  # Regex of files in the ITEM folder that represent the 'overview' of the Item (if any)
    "additional_property_keys": []                  # List of property keys that are suffixed to the ITEM folder name using double underscores __
}


```

## NEW : Simple Process - ONLY with agreement of DEDL Support - Considered not standard

- A 'Simplified' structure is possible - but only with the agreement of DEDL Support
    - To do so. Set "item_folder_level": NONE (in the collection_config.json file)
    - Activating this process means: naming standards can be ignored
      - With the downside that STAC ITEM
        - datetime are not determined from ITEM folder name
        - additional filters can not be determined from the ITEM folder name

```python

{
    "id": "EO.XXX.YYY.ZZZ",
    "item_asset_ignore_list": ["item_config.json"],
    "item_folder_level": "NONE",         # This means we are in simplified mode and any folders found directly in the root of the data folder become STAC ITEMs
    "thumbnail_regex": "^thumbnail",
    "overview_regex": "^overview",
    "additional_property_keys": []
}

```

- Any folders at the root of the data folder will now become STAC Items
  - All files contained in any subfolders become assets of that item
  - The Item > properties > datetime associated with these items can be set at several levels (in the following order)
    - "item_date_overide" set in collection_config.json will set that datetime globally for all ITEMS
    - if the first level folder found in data is in the form YYYY we use YYYY0101 as the STAC ITEM > properties > datetime
    - if none of the above we use the current day as the datetime for that STAC ITEM (date of generation of metadata)

```python

{
    "id": "EO.XXX.YYY.ZZZ",
    "item_asset_ignore_list": ["item_config.json"],
    "item_folder_level": "NONE",         # This means we are in a 'simplified mode' and any folders found directly in the root of the data folder become STAC ITEMs
    "item_date_overide": "20240101",     # This YYYYMMDD will be used to set the STAC ITEM > properties > datetime
    "thumbnail_regex": "^thumbnail",
    "overview_regex": "^overview",
    "additional_property_keys": [],
    "bbox": [-10.0, 35.0, 10.0, 60.0]    # An Optional bbox can be set at the collection level here, and will be applied to ALL items
}

```