# User Generated Data - Process

- This project demonstrates the integration of a **User Generated** Collection into Destination Earth Data Lake - HDA (Harmonised Data Access)
    - Using this project to propose **new data** assumes you have already contacted the Destination Earth Data Lake Support Team and that your proposal has been accepted by the **Data Lake - Review Board**.
    - **Note**: Proposing new data is a manual process, and requires review with the 'Data Lake - Review Board'. For this reason data cannot be continually updated. Each update will require a new request.

# User Generated Data Example

- Note: 
    > A full example representing a Collection and associated Items is found in the folder **EO.XXX.YYY.ZZZ** in this project


- The following describes the steps to follow to assure that you provide **data** and **metadata** that is ready to integrate into the HDA.


- You will be expected to provide (in a dedicated Bucket e.g. usergenerated-proposal-EO.XXX.YYY.ZZZ on your DEDL Islet Storage):
    - A root folder whose name is the same as the *collection id* that will be used in HDA. In this project we domonstrate with the collection id **EO.XXX.YYY.ZZZ**. This id will need to have been previously discussed and agreed with the Data Lake review board.
    - The folder should contain
        - a **metadata** subfolder, containing STAC 'Collection' and 'Item' metatdata
        - a **data** folder (YYYY/MM/DD) containing the data associated with 'Items' normally structured in folders YYYY/MM/DD (folder representing year, month, day that data is associated with)
            - Note: Depending on the granularity of your data the Item folders can be found at either the YYYY, MM or DD level (e.g. data that is specific to a given day would be found in the DD folder)

- In order to provide data and metadata in the expected format, you will likely need a VM with adequate storage to allow you to:
    - Manipulate/Move files into the expected folders
    - Generate preliminary item specific metadata (See item_config.json) that will later be used to generate the final STAC Item metadata.
- Given you now have a folder e.g. **EO.XXX.YYY.ZZZ** with **Collection** metadata and **data** in the expected structure, the file *generate_item_metadata.py* gives an example of generating the expected Item metadata.
    - generate_item_metadata.py is intended to be a generic python script ready to navigate through the prepared data and then generate STAC Item metadata appropriate for the collection and DEDL HDA.
    - When this script is launched the last step uploads the prepared data to a private bucket in your Data Lake tenant. The bucket name is standardised and set by the code 'usergenerated-proposal-[your collection id]'
        - The upload requires that you have created a **.env** file at the root of the project with previously created ec2 credentials (See https://destine-data-lake-docs.data.destination-earth.eu/en/latest/cloud/How-to-generate-ec2-credentials.html)


```bash

# .env file at root of project. generate_item_metadata.py will need these credentials to push your Collection (data and metadata) to the private bucket.

AWS_ACCESS_KEY_ID="[Replace with your ec2 credentials access_key_id]"
AWS_SECRET_ACCESS_KEY="[Replace with your ec2 credentials secret_access_key]"

```


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


## Structure of Project

Here we show the structure of this project which contains a Collection, associated Items and Data. For a demonstration collection, ready for integration into HDA, see the folder 'EO.XXX.YYY.ZZZ' at the root of this project

```bash

└── [MY_COLLECTION_ID]                           # e.g. EO.XXX.YYY.ZZZ (HIGH_LEVEL_DATA_TYPE.DATA_PROVIDER.DATATYPE.DATASET_NAME)
    └── metadata
        ├── collection_config.json               # Global configuration that can be used when generating items. This can be overloaded at the item level in item_config.json (see below). e.g. "thumbnail_regex" (to identify thumbnails)
        ├── collection.json                      # A STAC file of type 'Collection' in json format gives an overview of the collection. The name of the file is simply collection.json
        └── items
            └── ITEM_1_ID.json                   # A STAC file representing individual Items of type 'Feature' in json format gives information on the 'Item'
            └── ITEM_2_ID.json
    └── data                                             # The data associated with Items is stored in folders YYYY/MM/DD/...
        └── 2024                                         # 2024
            └── 11                                       # 11 = November
                └── 15                                   # 15 = 15th (of November)
                    └── ITEM_1_ID                        # a folder containing 1-n files/folders: naming convention [MY_COLLECTION_ID]_[start_datetime]_[end_datetime] or [MY_COLLECTION_ID]_[datetime]
                        └── item_config.json             # Item level configuration. Overides Collection level config if any. e.g. "bbox"
                        └── datafile1                    # Each file in this folder/subfolders is an 'Asset' of the Item (Possibility of ignoring some files using configuration). Each Asset should have a role "data", "metadata", "thumbnail", "overview"
                        └── datafile2
                        └── ...

            

```

## Collection Example


- Here we give an example of a STAC Collection describing high level information about your data Items
    - path = MY_COLLECTION_ID/metadata/collection.json

```json

// One of the files you will need to provide is a 'Collection' type STAC file
// The 'Collection' type STAC file is in json format and represents the high level overview of your individual Items
// (Remember to remove comments - which are not allowed in json format)

{
  "type": "Collection",
  "id": "EO.XXX.YYY.ZZZ",                                                  // Replace this e.g. EO.CLMS.DAT.CORINE
  "stac_version": "1.0.0",
  "description": "Text describing the dataset. This text will be shown in the Overview section of hda catalogue and can be a paragraph of text.",
  "links": [
      {
          "rel": "license",
          "href": "LICENCE_URL_LINK",                                      // Replace this e.g. https://land.copernicus.eu/en/data-policy
          "title": "LICENCE_NAME"                                          // Replace this e.g. Copernicus Land Data Policy
      },
      {
          "rel": "cite-as",
          "href": "DOI_URL",                                               // Replace this e.g. https://doi.org/10.2909/17ab2088-6907-470f-90b6-8c1364865803
          "title": "DOI_DATASET_TITLE"                                     // Replace this e.g. CORINE Land Cover Change 1990-2000 (vector), Europe, 6-yearly - version 2020_20u1, May 2020
      },
      {
          "rel": "describedby",                                            
          "href": "OTHER_DATASET_URL",                                     // Replace this e.g. https://land.copernicus.eu/en/products/corine-land-cover
          "title": "DATASET_TITLE"                                         // Replace this e.g. CORINE Land Cover
      }
                                                                           // NOTE: Other links will be added dynamically when integrating the collection into DEDL HDA (e.g. Parent, Self etc...)
  ],
  "stac_extensions": [
      "https://stac-extensions.github.io/scientific/v1.0.0/schema.json"    // e.g. Optional extension e.g. to expose Digital Object Identifiers
  ],
  "sci:publications": [
      {
          "sci:doi": "DOI_CODE",                                           // Replace this e.g. 10.2909/c62bb056-5ac3-4512-b642-7f484175d951
          "sci:citation": "DOI_DATASET_TITLE"                              // Replace this e.g. European Union's Copernicus Land Monitoring Service information (CORINE Land Cover Change 1990-2000 (raster 100 m), Europe, 6-yearly)
      }
  ],
  "title": "DATASET_TITLE",                                                // Replace this (A short description of the collection) e.g. CORRINE Land Cover
  "extent": {
      "spatial": {
          "bbox": [                                                        // Replace these values with your spatial bbox coordinates
              [
                  -31.561261,
                  27.405827,
                  44.820775,
                  71.409109
              ]
          ]
      },
      "temporal": {
          "interval": [                                                    // Replace these values with your temporal extent (covering the temporal extent of the planned Items you are exposing). if no end date the second date can be replaced with null (no quotation marks)
              [
                  "2024-11-01T00:00:00Z",
                  "2024-11-30T23:59:59Z"
              ]
          ]
      }
  },
  "license": "proprietary",
  "keywords": [                                                            // Replace these keywords - refer to https://hda.central.data.destination-earth.eu/ui/catalog to see existing. Use these where possible
      "Satellite Image Interpretation",
      "Land Cover Change",
      "geospatial data",
      "landscape alteration",
      "Land cover",
      "European",
      "Copernicus"
  ],
  "providers": [
      {
          "name": "PROVIDER_NAME",                                         // Replace this e.g. European Environment Agency
          "roles": [                                                       // Replace these values as appropriate
              "producer",
              "processor",
              "licensor"
          ],
          "url": "PROVIDER_URL"                                            // Replace this e.g. https://www.eea.europa.eu/
      }
  ],
  "assets": {
      "thumbnail": {
          "href": "URL_TO_DATASET_IMAGE",                                  // Replace this e.g. https://land.copernicus.eu/en/products/corine-land-cover/@@images/image-400-7d8e8dfc63d50c9bf89ff5a7475dcd46.png
          "type": "image/png",                                             // Replace this with the correct Mime type
          "title": "overview",
          "roles": [
              "thumbnail"
          ]
      }
  }
}



```

## Items Example

This is an example of a generated Item from this project. This is a possible starting point and can enriched as needed

```json

{
    "type": "Feature",
    "stac_version": "1.0.0",
    "stac_extensions": [],
    "id": "EO.XXX.YYY.ZZZ_20241115T000000_20241115T235959",
    "geometry": {
        "type": "Polygon",
        "coordinates": [
            [
                [
                    10.0,
                    35.0
                ],
                [
                    10.0,
                    60.0
                ],
                [
                    -10.0,
                    60.0
                ],
                [
                    -10.0,
                    35.0
                ],
                [
                    10.0,
                    35.0
                ]
            ]
        ]
    },
    "bbox": [
        -10.0,
        35.0,
        10.0,
        60.0
    ],
    "properties": {
        "start_datetime": "2024-11-15T00:00:00Z",
        "end_datetime": "2024-11-15T23:59:59Z",
        "datetime": "2024-11-15T00:00:00Z"
    },
    "links": [
        {
            "rel": "collection",
            "href": "https://hda.data.destination-earth.eu/stac/collections/EO.XXX.YYY.ZZZ",
            "type": "application/json",
            "title": "DATASET_TITLE"
        },
        {
            "rel": "self",
            "href": "https://hda.data.destination-earth.eu/stac/collections/EO.XXX.YYY.ZZZ/items/EO.XXX.YYY.ZZZ_20241115T000000_20241115T235959",
            "type": "application/json"
        }
    ],
    "assets": {
        "metadata1.json": {
            "href": "data/2024/11/15/EO.XXX.YYY.ZZZ_20241115T000000_20241115T235959/metadata1.json",
            "type": "application/json",
            "roles": [
                "metadata"
            ]
        },
        "thumbnail.jpg": {
            "href": "data/2024/11/15/EO.XXX.YYY.ZZZ_20241115T000000_20241115T235959/thumbnail.jpg",
            "type": "image/jpeg",
            "roles": [
                "thumbnail"
            ]
        },
        "overview.jpg": {
            "href": "data/2024/11/15/EO.XXX.YYY.ZZZ_20241115T000000_20241115T235959/overview.jpg",
            "type": "image/jpeg",
            "roles": [
                "overview"
            ]
        },
        "20241115.png": {
            "href": "data/2024/11/15/EO.XXX.YYY.ZZZ_20241115T000000_20241115T235959/20241115.png",
            "type": "image/png",
            "roles": [
                "data"
            ]
        }
    },
    "collection": "EO.XXX.YYY.ZZZ"
}

```