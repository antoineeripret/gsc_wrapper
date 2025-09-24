#source https://github.com/joshcarty/google-searchconsole/blob/master/searchconsole/auth.py 

"""
Convenience function for authenticating with Google Search
Console. You can use saved client configuration files or a
mapping object and generate your credentials using OAuth2 or
a serialized credentials file or mapping.

For more details on formatting your configuration files, see:
http://google-auth-oauthlib.readthedocs.io/en/latest/reference/google_auth_oauthlib.flow.html
"""

import collections.abc
import json, urllib
from .account import Account, Account_BQ

# Define Oath scopes with read only access
OAUTH_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

from apiclient import discovery
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from google.oauth2 import service_account

def generate_auth(
    client_config, 
    credentials=None, 
    serialize=None, 
    flow="web", 
    service_account_auth=False, 
    bigquery=False, 
    bigquery_dataset=None, 
    port=8080, 
    google_colab = False 
    ):
    """
    This function generates authentication for Google Search Console.
    
    Args:
        client_config (str): The path to the client configuration file.
        credentials (object, optional): The credentials object used for authentication with the Google Search Console API.
        serialize (str, optional): The path to the serialized credentials file.
        flow (str, optional): The flow type. Supported values are 'web' and 'installed_app'.
        service_account_auth (bool, optional): If True, service account authentication is used. If False, OAuth2 authentication is used.
        bigquery (bool, optional): If True, BigQuery authentication is used. If False, Google Search Console authentication is used.
        bigquery_dataset (str, optional): The BigQuery dataset name.
        port (int, optional): The port number for the local server.
        google_colab (bool, optional): If True, the authentication is generated for Google Colab. If False, the authentication is generated for local use.
    
    Returns:
        object: The authentication object.
    """
    
    if bigquery:
        if not bigquery_dataset:
            raise ValueError('You must provide a dataset name.')
        if len(bigquery_dataset.split('.')) != 2:
            raise ValueError('Dataset name must be in the format project_id.dataset_name')
        credentials = (
            service_account
            .Credentials
            .from_service_account_file(
                filename=client_config,
            )
        )
        
        return Account_BQ(credentials, bigquery_dataset)
    
    if service_account_auth:
        credentials = (
            service_account
            .Credentials
            .from_service_account_file(
                filename=client_config,
                scopes=['https://www.googleapis.com/auth/webmasters.readonly']
            )
        )
        
        service = discovery.build(
        serviceName='searchconsole',
        version='v1',
        credentials=credentials,
        cache_discovery=False,
    )
        return Account(service, credentials)

    if not credentials:
        
        if google_colab == True:
            # Set up the flow with a local redirect URI
            auth_flow = InstalledAppFlow.from_client_secrets_file(client_config, OAUTH_SCOPE)
            auth_flow.redirect_uri = 'http://localhost:8080/'

            # Get the authorization URL
            auth_url, _ = auth_flow.authorization_url(prompt='consent')
            print('Please go to this URL and authorize access:')
            print(auth_url)

            # Paste the authorization code you get after authorizing
            auth_code = input('Enter the authorization code or url: ')
            if 'http://localhost:8080' in auth_code:
                # Extract the code from the URL
                parsed = urllib.parse.urlparse(auth_code)
                params = urllib.parse.parse_qs(parsed.query)
                if 'code' not in params:
                    raise ValueError('Invalid URL: No code parameter found.')
                auth_code = params.get('code', [None])[0]    

            # Exchange the code for credentials
            auth_flow.fetch_token(code=auth_code)
            credentials = auth_flow.credentials
        
        if isinstance(client_config, collections.abc.Mapping):
            auth_flow = InstalledAppFlow.from_client_config(
                client_config=client_config,
                scopes=[OAUTH_SCOPE]
            )
        elif isinstance(client_config, str):
            auth_flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file=client_config,
                scopes=[OAUTH_SCOPE]
            )
        else:
            raise ValueError("Client secrets must be a mapping or path to file")
        if flow == "web" and google_colab == False :
            auth_flow.run_local_server(port=port)
            credentials = auth_flow.credentials
        elif flow == "console" and google_colab == False:
            auth_flow.run_console()
            credentials = auth_flow.credentials
        elif google_colab == True:
            pass
        else:
            raise ValueError("Authentication flow '{}' not supported".format(flow))
    else:
        if isinstance(credentials, str):
            with open(credentials, 'r') as f:
                credentials = json.load(f)
        credentials = Credentials(
            token=credentials['token'],
            refresh_token=credentials['refresh_token'],
            id_token=credentials['id_token'],
            token_uri=credentials['token_uri'],
            client_id=credentials['client_id'],
            client_secret=credentials['client_secret'],
            scopes=credentials['scopes']
        )
    service = discovery.build(
        serviceName='searchconsole',
        version='v1',
        credentials=credentials,
        cache_discovery=False,
    )
    if serialize:
        if isinstance(serialize, str):
            serialized = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'id_token': credentials.id_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            with open(serialize, 'w') as f:
                json.dump(serialized, f)
        else:
            raise TypeError('`serialize` must be a path.')

    return Account(service, credentials)