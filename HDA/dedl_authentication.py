import requests
from lxml import html
from urllib.parse import parse_qs, urlparse

IAM_URL = "https://auth.destine.eu/"
CLIENT_ID = "dedl-hda"
REALM = "desp"
SERVICE_URL = "https://hda.data.destination-earth.eu/stac/"


class DESPAuth:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        
    def get_token(self):
        with requests.Session() as s:

            # Get the auth url
            auth_url = html.fromstring(s.get(url=IAM_URL + "/realms/" + REALM + "/protocol/openid-connect/auth",
                                     params = {
                                            "client_id": CLIENT_ID,
                                            "redirect_uri": SERVICE_URL,
                                            "scope": "openid",
                                            "response_type": "code"
                                     }
                                       ).content.decode()).forms[0].action
            
            # Login and get auth code
            login = s.post(auth_url,
                            data = {
                                "username" : self.username,
                                "password" : self.password,
                            },
                            allow_redirects=False
            )


            # We expect a 302, a 200 means we got sent back to the login page and there's probably an error message
            if login.status_code == 200:
                tree = html.fromstring(login.content)
                error_message_element = tree.xpath('//span[@id="input-error"]/text()')
                error_message = error_message_element[0].strip() if error_message_element else 'Error message not found'
                raise Exception(error_message)

            if login.status_code != 302:
                print("DESP Login failed")
                return None
            

            auth_code = parse_qs(urlparse(login.headers["Location"]).query)['code'][0]

            # Use the auth code to get the token
            response = requests.post(IAM_URL + "/realms/" + REALM + "/protocol/openid-connect/token",
                    data = {
                        "client_id" : CLIENT_ID,
                        "redirect_uri" : SERVICE_URL,
                        "code" : auth_code,
                        "grant_type" : "authorization_code",
                        "scope" : ""
                    }
                )
            
            if response.status_code != 200:
                raise Exception("Failed to get token")
            
            token = response.json()['access_token']

            return token  
        
class DEDLAuth:
    def __init__(self, desp_access_token, username, password):
        self.desp_access_token = desp_access_token
        self.username = username
        self.password = password

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

    def get_token_dedl(self):
        DEDL_TOKEN_URL='https://identity.data.destination-earth.eu/auth/realms/dedl/protocol/openid-connect/token'
        DEDL_CLIENT_ID='hda-public'
        
        data = { 
                "grant_type": "password", 
                "scope": "openid",
                "client_id": DEDL_CLIENT_ID,
                "username" : self.username,
                "password" : self.password            
        }

        response = requests.post(DEDL_TOKEN_URL, data=data, headers = {"Content-Type" : "application/x-www-form-urlencoded"})
        
        print("Response code:", response.status_code)

        if response.status_code == 200: 
            dedl_token = response.json()["access_token"]
            return dedl_token
        else: 
            print(response.json())
            print("Error obtaining DEDL access token")               
            
class AuthHandler:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.desp_access_token = None
        self.dedl_access_token = None
    
    def get_token(self):
        # Get DESP auth token   
        try:
            desp_auth = DESPAuth(self.username, self.password)    
            # Try to obtain DESP token
            self.desp_access_token = desp_auth.get_token()
        except Exception as e:
            # Code to handle the exception
            print("DESP authentication flow failed:", e) 
            # Token not available from DESP. Try from DEDL instead (local account)
            dedl_auth = DEDLAuth(self.desp_access_token,self.username, self.password)
            self.dedl_access_token = dedl_auth.get_token_dedl()                     
            print("trying with DEDL local authentication") 
            if(len(self.dedl_access_token)>0):
                print("DEDL local authentication submitted successfully!")
            else:
                print("DEDL local authentication failed!")
        else: 
            # Get DEDL auth token
            dedl_auth = DEDLAuth(self.desp_access_token,self.username, self.password)
            self.dedl_access_token = dedl_auth.get_token()
        finally:        
            return self.dedl_access_token
    
 
    
