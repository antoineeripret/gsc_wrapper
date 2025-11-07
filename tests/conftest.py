"""
Pytest configuration and fixtures for gscwrapper tests.
"""
import os
import pytest
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


@pytest.fixture
def client_secret_path(tmp_path):
    """
    Fixture that creates a temporary client_secret.json file from CLIENT_SECRET env var.
    Returns the path to the temporary file.
    """
    client_secret = os.getenv('CLIENT_SECRET')
    if not client_secret:
        pytest.skip("CLIENT_SECRET not found in .env file")
    
    # Create temporary file
    client_secret_file = tmp_path / 'client_secret.json'
    client_secret_file.write_text(client_secret)
    
    return str(client_secret_file)


@pytest.fixture
def credentials_path(tmp_path):
    """
    Fixture that creates a temporary credentials.json file from CREDENTIALS env var.
    Returns the path to the temporary file.
    """
    credentials = os.getenv('CREDENTIALS')
    if not credentials:
        pytest.skip("CREDENTIALS not found in .env file")
    
    # Create temporary file
    credentials_file = tmp_path / 'credentials.json'
    credentials_file.write_text(credentials)
    
    return str(credentials_file)


@pytest.fixture
def client_secret_dict():
    """
    Fixture that loads CLIENT_SECRET file (path from env) and parses it as JSON, returning a dict.
    """
    import json
    client_secret_path = os.getenv('CLIENT_SECRET')
    if not client_secret_path or not os.path.exists(client_secret_path):
        pytest.skip("CLIENT_SECRET file path not found or does not exist in .env file")

    with open(client_secret_path, 'r') as f:
        client_secret_data = json.load(f)

    return client_secret_data


@pytest.fixture
def credentials_dict():
    """
    Fixture that loads CREDENTIALS file (path from env) and parses it as JSON, returning a dict.
    """
    import json
    credentials_path = os.getenv('CREDENTIALS')
    if not credentials_path or not os.path.exists(credentials_path):
        pytest.skip("CREDENTIALS file path not found or does not exist in .env file")

    with open(credentials_path, 'r') as f:
        creds = json.load(f)

    required_fields = ['token', 'refresh_token', 'id_token', 'token_uri', 
                       'client_id', 'client_secret', 'scopes']
    missing = [key for key in required_fields if key not in creds]
    if missing:
        pytest.skip(f"CREDENTIALS is missing required keys: {missing}")

    return credentials_path

