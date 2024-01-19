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
import json
from .account import Account

# Define Oath scopes with read only access
OAUTH_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

from apiclient import discovery
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

def generate_auth(client_config, credentials=None, serialize=None, flow="console"):

    if not credentials:
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
        if flow == "web":
            auth_flow.run_local_server()
        elif flow == "console":
            auth_flow.run_console()
        else:
            raise ValueError("Authentication flow '{}' not supported".format(flow))
        credentials = auth_flow.credentials
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