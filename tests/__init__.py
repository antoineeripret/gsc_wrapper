# Tests package for gscwrapper

import os

def regenerate_credentials_from_env():
    """
    Regenerate the CREDENTIALS file (via OAuth flow) using the path specified in the .env file.
    This will overwrite the credentials file if it already exists.
    """

    from pathlib import Path
    from dotenv import load_dotenv

    # Load the .env file from project root
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)

    client_secret = os.getenv('CLIENT_SECRET')
    credentials_path = os.getenv('CREDENTIALS')

    if not client_secret:
        raise RuntimeError("CLIENT_SECRET not found in .env; cannot regenerate credentials.")
    if not credentials_path:
        raise RuntimeError("CREDENTIALS path not found in .env; cannot regenerate credentials.")

    # Run the OAuth flow to generate new credentials and save to credentials_path
    from gscwrapper.auth import generate_auth

    print("Regenerating credentials using OAuth flow. Please complete authentication in browser/CLI if prompted.")
    result = generate_auth(
        client_config=client_secret,
        serialize=credentials_path,
        flow="web",
        google_colab=False
    )
    print(f"Credentials written to {credentials_path}")


#regenerate_credentials_from_env()
