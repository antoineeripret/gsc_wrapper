"""
Tests for the auth module of gscwrapper.
"""
import os
import pytest

from gscwrapper.auth import generate_auth, OAUTH_SCOPE
from gscwrapper.account import Account

class TestGenerateAuth:
    """Test cases for the generate_auth function."""
    
    def test_oauth_scope_constant(self):
        """Test that OAUTH_SCOPE is correctly defined."""
        assert OAUTH_SCOPE == "https://www.googleapis.com/auth/webmasters.readonly"
    
    def test_generate_auth_with_invalid_client_config_type(self):
        """Test that generate_auth raises ValueError for invalid client_config type."""
        with pytest.raises(ValueError, match="Client secrets must be a mapping or path to file"):
            generate_auth(client_config=12345)  # Invalid type
    
    def test_generate_auth_with_service_account_auth(self):
        """Test service account authentication."""
        service_account_path = os.getenv('SERVICE_ACCOUNT')
        if not service_account_path:
            pytest.skip("SERVICE_ACCOUNT not found in .env file")
        
        result = generate_auth(
            client_config=service_account_path,
            service_account_auth=True
        )
        
        assert isinstance(result, Account)
        assert result.service is not None
        assert result.credentials is not None
    
    def test_generate_auth_with_credentials_string_path(self, credentials_path=os.getenv('CREDENTIALS'), client_secret_dict=os.getenv('CLIENT_SECRET')):
        """Test generate_auth with credentials as a file path string."""
        if not credentials_path or not client_secret_dict:
            pytest.skip("CREDENTIALS or CLIENT_SECRET not found in .env file")
        
        result = generate_auth(
            client_config=client_secret_dict,
            credentials=credentials_path
        )
        
        assert isinstance(result, Account)
    
    
    def test_generate_auth_serialize_invalid_type(self, credentials_dict=os.getenv('CREDENTIALS'), client_secret_dict=os.getenv('CLIENT_SECRET'), serialize=12345):
        """Test that serialize parameter must be a string."""
        if not credentials_dict or not client_secret_dict:
            pytest.skip("CREDENTIALS or CLIENT_SECRET not found in .env file")
        
        with pytest.raises(TypeError, match="`serialize` must be a path"):
            generate_auth(
                client_config=client_secret_dict,
                credentials=credentials_dict,
                serialize=12345  # Invalid type
            )
    def test_generate_auth_returns_account_instance(self, credentials_dict=os.getenv('CREDENTIALS'), client_secret_dict=os.getenv('CLIENT_SECRET')):
        """Test that generate_auth returns an Account instance."""
        if not credentials_dict or not client_secret_dict:
            pytest.skip("CREDENTIALS or CLIENT_SECRET not found in .env file")
        
        result = generate_auth(
            client_config=client_secret_dict,
            credentials=credentials_dict
        )
        
        assert isinstance(result, Account)
        assert result.service is not None
        assert result.credentials is not None

