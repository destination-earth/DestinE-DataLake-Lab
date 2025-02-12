<img src="../img/DestinE-banner.jpg"
     alt="Destination Earth banner"
/>

# Hook Service

<img style="float:left; width:5%" src="../img/EUMETSAT-icon.png"/> **Author:** EUMETSAT 
<br>

This folder contains materials for learning how to use Hook Service. 

The Destination Earth Data Lake (DEDL) ‘Hook service’ provides ready-to-use high level serverless workflows and functions preconfigured to efficiently access and manipulate Destination Earth Data Lake (DEDL) data. A growing number of workflows and functions will provide on-demand capabilities for the diverse data analysis needs.

## Notebooks


### [Tutorial](): How to discover available workflows and run one example (data-harvest workflow)


```shell
#The Tutorial.ipynb is executeable as-is, but parameters can be provided from a file .env_tutorial
#To provide environment parameters from file

# 1. create a file called .env_tutorial in the same folder as the notebook
# 2. paste in the following contents
# 3. execute the Tutorial.ipynb notebook which should now pick up the environment variables from file

########## SET HOOK_ORDER_NAME ##########
# This will be added to the order name. e.g. replace XXXX with your name

HOOK_ORDER_NAME=XXXX-20250212-1

########## SET WORKFLOW, COLLECTION_ID and DATA_ID ##########
# Uncomment HOOK_WORKFLOW (to identify the HOOK to execute)
# Uncomment HOOK_COLLECTION_ID (to identify the DEDL Collection where the data comes from)
# Uncomment HOOK_DATA_ID (to identify the data that is input to the HOOK)
# Uncomment HOOK_SOURCE_TYPE (to identify the source_type of the HOOK. Possible values are DESP, EXTERNAL...)

# DEDL HDA input possible

#HOOK_WORKFLOW=card_bs
#HOOK_COLLECTION_ID=EO.ESA.DAT.SENTINEL-1.L1_GRD
#HOOK_DATA_ID=S1A_IW_GRDH_1SDV_20230910T054256_20230910T054321_050261_060CD9_BF21.SAFE
#HOOK_SOURCE_TYPE=DESP

#HOOK_WORKFLOW=lai
#HOOK_COLLECTION_ID=EO.ESA.DAT.SENTINEL-2.MSI.L2A
#HOOK_DATA_ID=S2A_MSIL2A_20230906T102601_N0509_R108_T32UMA_20230906T164400.SAFE
#HOOK_SOURCE_TYPE=DESP

# INPUT PRODUCT TYPES: SLC, S1_SLC__1S, S2_SLC__1S, S3_SLC__1S, S4_SLC__1S, S5_SLC__1S, S6_SLC__1S, IW_SLC__1S, EW_SLC__1S, WV_SLC__1S
#HOOK_WORKFLOW=card_cohinf
#HOOK_COLLECTION_ID=EO.ESA.DAT.SENTINEL-1.L1_SLC
#HOOK_DATA_ID=S1A_IW_SLC__1SDV_20240121T155314_20240121T155341_052207_064FA6_3AB9
#HOOK_ADDITIONAL1="NAME=card_producttype;VALUE=CARD_COH;VALUE_TYPE=str"
#HOOK_DATA_ID=S1A_IW_SLC__1SDV_20230930T172417_20230930T172444_050560_06170F_59DF
#HOOK_ADDITIONAL1="NAME=card_producttype;VALUE=CARD_INF;VALUE_TYPE=str"
#HOOK_ADDITIONAL2="NAME=timespan;VALUE=24;VALUE_TYPE=int"
#HOOK_SOURCE_TYPE=DESP

#HOOK_WORKFLOW=c2rcc
#HOOK_COLLECTION_ID=EO.ESA.DAT.SENTINEL-2.MSI.L1C
#HOOK_DATA_ID=S2B_MSIL1C_20231001T102739_N0509_R108_T31TGL_20231001T123227
#HOOK_SOURCE_TYPE=DESP

HOOK_WORKFLOW=data-harvest
HOOK_COLLECTION_ID=EO.ESA.DAT.SENTINEL-2.MSI.L1C
HOOK_DATA_ID=S2A_MSIL1C_20230910T050701_N0509_R019_T47VLH_20230910T074321.SAFE
HOOK_SOURCE_TYPE=DESP
#HOOK_SOURCE_TYPE=EXTERNAL
#HOOK_EXTERNAL_TOKEN_URL=https://identity.XXXX/auth/realms/XXXX/protocol/openid-connect/token
#HOOK_EXTERNAL_CLIENT_ID=hda_public
#HOOK_EXTERNAL_USERNAME=
#HOOK_EXTERNAL_PASSWORD=

#HOOK_WORKFLOW=sen2cor
#HOOK_COLLECTION_ID=EO.ESA.DAT.SENTINEL-2.MSI.L1C
#HOOK_DATA_ID=S2B_MSIL1C_20231001T102739_N0509_R108_T32TMS_20231001T123227
#HOOK_SOURCE_TYPE=DESP

##### DEDL HDA input NOT possible at the moment. i.e. source_type is not DESP nor EXTERNAL #####
# These HOOKs have specific configuration. See below

# Accesses Creodias Catalogue in the background
#HOOK_WORKFLOW=copdem
#HOOK_COLLECTION_ID=
#HOOK_DATA_ID=S3A_SL_1_RBT____20161110T022134_20161110T022434_20181003T070309_0179_010_374______LR1_R_NT_003.SEN3
#HOOK_SOURCE_TYPE=

# Accesses Creodias Catalogue in the background
#HOOK_WORKFLOW=maja
#HOOK_COLLECTION_ID=
#HOOK_DATA_ID=S2B_MSIL1C_20220429T102549_N0400_R108_T31UGQ_20220429T124017.SAFE
#HOOK_SOURCE_TYPE=
#HOOK_ADDITIONAL1="NAME=input_type;VALUE=TIMESPAN;VALUE_TYPE=str"
#HOOK_ADDITIONAL2="NAME=timeseries_end_id;VALUE=S2B_MSIL1C_20220429T102549_N0400_R108_T31UGQ_20220429T124017.SAFE;VALUE_TYPE=str"
#HOOK_ADDITIONAL3="NAME=timespan;VALUE=18;VALUE_TYPE=int"


########## START : Example Triggering CUSTOM HOOOK - dedl_hello_world ##########

# # This 'Custom Hook' demonstrator expects a file called 'example.data' in the 'source_s3_path' bucket/folder (of the configured source_s3_endpoint)
# # The text contents of example.data will be converted to Upper Case and output to Private or Temporary Storage

# HOOK_WORKFLOW=dedl_hello_world

# # Needs to be empty
# HOOK_COLLECTION_ID=

# # This normally contains the ID of a product, but for Custom Hooks we will set it to an arbitrary value 'Custom Hook'
# HOOK_DATA_ID=Custom Hook

# # Needs to be empty
# HOOK_SOURCE_TYPE=

# # Setting source_s3_path TO s3://XXXX/dedl_hello_world/input_file_location
# HOOK_ADDITIONAL1="NAME=source_s3_path;VALUE=s3://XXXX/dedl_hello_world/input_file_location;VALUE_TYPE=str"
# # Setting source_s3_endpoint_url TO https://s3.central.data.destination-earth.eu
# HOOK_ADDITIONAL2="NAME=source_s3_endpoint_url;VALUE=https://s3.central.data.destination-earth.eu;VALUE_TYPE=str"
# # Setting source_s3_access_key TO YYYY (change this to your access_key)
# HOOK_ADDITIONAL3="NAME=source_s3_access_key;VALUE=YYYY;VALUE_TYPE=str"
# # Setting source_s3_secret_key TO ZZZZ (change this to your access_key)
# HOOK_ADDITIONAL4="NAME=source_s3_secret_key;VALUE=ZZZZ;VALUE_TYPE=str"

########## END : Example Triggering CUSTOM HOOOK - dedl_hello_world ##########

########## SET STORAGE OPTION ##########
# If you set HOOK_IS_PRIVATE_STORAGE to True you will need to set the bucket name, access key, and secret key
HOOK_IS_PRIVATE_STORAGE=False
#HOOK_OUTPUT_BUCKET=your_bucket-name
#HOOK_OUTPUT_STORAGE_ACCESS_KEY=your_access_key
#HOOK_OUTPUT_STORAGE_SECRET_KEY=your_secret_key

```


### [DEDL-Hook_access.ipynb](): Simple retrieval of token and listing of workflows

- Launch this noteboook with your DESP credentials and retrieve a token you can use to interact with OnDemand Processing API (Hook API)



## Further Information

Further information available in DestinE Data Lake documentation: https://destine-data-lake-docs.data.destination-earth.eu/en/latest/index.html

>**Additional ressources:**
>DestinE Data Portfolio: https://hda.data.destination-earth.eu/ui/catalog
>DataLake Priority services: https://hda.data.destination-earth.eu/ui/services 
>HDA SWAGGER UI: https://hda.data.destination-earth.eu/docs/