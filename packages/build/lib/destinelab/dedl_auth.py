import requests
from lxml import html
from urllib.parse import parse_qs, urlparse

IAM_URL = "https://auth.destine.eu/"
CLIENT_ID = "dedl-hda"
REALM = "desp"
SERVICE_URL = "https://hda.data.destination-earth.eu/stac"

class DEDLAuth:
    def __init__(self, desp_access_token):
        self.desp_access_token = desp_access_token

    def get_token(self):
        DEDL_TOKEN_URL='https://identity.data.destination-earth.eu/auth/realms/dedl/protocol/openid-connect/token'
        DEDL_CLIENT_ID='hda-public'
        AUDIENCE='hda-public'
        
        data = { 
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange", 
            "subject_token": self.desp_access_token,
            "subject_issuer": "desp-oidc",
            "subject_token_type": "urn:ietf:params:oauth:token-type:access_token",
            "client_id": DEDL_CLIENT_ID,
            "audience": AUDIENCE
        }

        response = requests.post(DEDL_TOKEN_URL, data=data)
        
        print("Response code:", response.status_code)

        if response.status_code == 200: 
            dedl_token = response.json()["access_token"]
            return dedl_token
        else: 
            print(response.json())
            print("Error obtaining DEDL access token")