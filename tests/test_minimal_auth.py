"""
Minimal authentication tests that don't require database setup.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta

from backend.utils.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    AuthError,
    generate_state_token,
)


class TestJWTTokensMinimal:
    """Test JWT token creation and verification without database."""

    def test_create_access_token(self):
        """Test access token creation."""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        token_data = {"sub": user_id, "email": email}
        
        token = create_access_token(token_data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = verify_token(token, "access")
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Test refresh token creation."""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        token_data = {"sub": user_id, "email": email}
        
        token = create_refresh_token(token_data)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Verify token can be decoded
        payload = verify_token(token, "refresh")
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["type"] == "refresh"

    def test_verify_token_invalid_type(self):
        """Test token verification with wrong type."""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        token_data = {"sub": user_id, "email": email}
        access_token = create_access_token(token_data)
        
        # Try to verify access token as refresh token
        with pytest.raises(AuthError, match="Invalid token type"):
            verify_token(access_token, "refresh")

    def test_verify_token_invalid_token(self):
        """Test token verification with invalid token."""
        with pytest.raises(AuthError, match="Invalid token"):
            verify_token("invalid.token.here", "access")

    def test_generate_state_token(self):
        """Test OAuth state token generation."""
        token1 = generate_state_token()
        token2 = generate_state_token()
        
        assert isinstance(token1, str)
        assert isinstance(token2, str)
        assert len(token1) >= 32
        assert len(token2) >= 32
        assert token1 != token2  # Should be random

    def test_token_expiration(self):
        """Test token expiration handling."""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        token_data = {"sub": user_id, "email": email}
        
        # Create token with very short expiration
        short_expiry = timedelta(seconds=-1)  # Already expired
        token = create_access_token(token_data, expires_delta=short_expiry)
        
        # Should raise expired error
        with pytest.raises(AuthError, match="Token has expired"):
            verify_token(token, "access")

    def test_token_payload_validation(self):
        """Test token payload validation."""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        
        # Test with additional data
        token_data = {
            "sub": user_id, 
            "email": email,
            "name": "Test User",
            "role": "user"
        }
        
        token = create_access_token(token_data)
        payload = verify_token(token, "access")
        
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["name"] == "Test User" 
        assert payload["role"] == "user"
        assert "exp" in payload
        assert "type" in payload


class TestConfigValidation:
    """Test configuration validation without database."""

    def test_config_environment_variables(self):
        """Test that configuration loads correctly."""
        from backend.config import get_config
        
        config = get_config()
        
        # Test that required environment variables are loaded
        # (These should be set in conftest.py for tests)
        assert hasattr(config, 'jwt_secret')
        assert hasattr(config, 'app_host')
        assert hasattr(config, 'app_port')
        assert hasattr(config, 'backend_url')
        
        # Test defaults
        assert config.app_host == "localhost"
        assert config.app_port == 5001


if __name__ == "__main__":
    pytest.main([__file__])