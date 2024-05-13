import requests
from lxml import html
from urllib.parse import parse_qs, urlparse

IAM_URL = "https://auth.destine.eu/"
CLIENT_ID = "dedl-hda"
REALM = "desp"
SERVICE_URL = "https://hda.data.destination-earth.eu/stac"

# Import DESPAuth and DEDLAuth here to ensure they are available
from .desp_auth import DESPAuth
from .dedl_auth import DEDLAuth

class AuthHandler:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.desp_access_token = None
        self.dedl_access_token = None
    
    def get_token(self):
        # Get DESP auth token
        desp_auth = DESPAuth(self.username, self.password)
        self.desp_access_token = desp_auth.get_token()
        
        # Get DEDL auth token
        dedl_auth = DEDLAuth(self.desp_access_token)
        self.dedl_access_token = dedl_auth.get_token()
        
        return self.dedl_access_token