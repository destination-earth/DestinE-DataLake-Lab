import requests
from lxml import html
from urllib.parse import parse_qs, urlparse

IAM_URL = "https://auth.destine.eu/"
CLIENT_ID = "dedl-hda"
REALM = "desp"
SERVICE_URL = "https://hda.data.destination-earth.eu/stac"


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
                raise Exception("Login failed")
            

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