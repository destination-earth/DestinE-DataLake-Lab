# destinelab
**Current version:** 0.3  
**destinelab** is a python package which allows DestinE users for basic interaction with Destination Earth Data Lake (DEDL) services.  
## Installation  
```
pip install destinelab
```
## Prerequisites
User ahs be registered on DestinE platform website [hyperlink](https://platform.destine.eu/
## Functions

### Authenication do Destination Earth Data Lake services
In order to get access to DEDL services user has to provide username and password.

```
DESP_USERNAME = 'username'
DESP_PASSWORD = 'password'

auth_desp = AuthHandler(DESP_USERNAME, DESP_PASSWORD)
```
Verify if it works 
```
if access_token is not None:
    print("DEDL/DESP Access Token Obtained Successfully")
else:
    print("Failed to Obtain DEDL/DESP Access Token"))
```
Expected results
```
Response code: 200
DEDL/DESP Access Token Obtained Successfully
```
Now, it is possible to deal with DEDL services.
