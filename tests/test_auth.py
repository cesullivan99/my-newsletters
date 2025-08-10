"""
Tests for authentication and OAuth flow functionality.
"""

import pytest
from unittest.mock import patch, Mock
from datetime import datetime, timezone, timedelta

from backend.utils.auth import (
    create_access_token,
    create_refresh_token,
    verify_token,
    AuthError,
    generate_state_token,
)


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self, test_user):
        """Test access token creation."""
        token_data = {"sub": str(test_user.id), "email": test_user.email}
        token = create_access_token(token_data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = verify_token(token, "access")
        assert payload["sub"] == str(test_user.id)
        assert payload["email"] == test_user.email
        assert payload["type"] == "access"

    def test_create_refresh_token(self, test_user):
        """Test refresh token creation."""
        token_data = {"sub": str(test_user.id), "email": test_user.email}
        token = create_refresh_token(token_data)

        assert isinstance(token, str)
        assert len(token) > 0

        # Verify token can be decoded
        payload = verify_token(token, "refresh")
        assert payload["sub"] == str(test_user.id)
        assert payload["email"] == test_user.email
        assert payload["type"] == "refresh"

    def test_verify_token_invalid_type(self, test_user):
        """Test token verification with wrong type."""
        token_data = {"sub": str(test_user.id), "email": test_user.email}
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


class TestAuthRoutes:
    """Test authentication routes."""

    @pytest.mark.asyncio
    async def test_gmail_oauth_start(self, client):
        """Test starting Gmail OAuth flow."""
        with patch("backend.routes.auth.create_oauth_flow") as mock_flow:
            mock_flow_instance = Mock()
            mock_flow_instance.authorization_url.return_value = (
                "https://accounts.google.com/oauth/authorize?test=1",
                "test-state",
            )
            mock_flow.return_value = mock_flow_instance

            response = await client.get("/auth/gmail-oauth")

            assert response.status_code == 302
            assert "accounts.google.com" in response.location

    @pytest.mark.asyncio
    async def test_oauth_callback_success(self, client, db_session):
        """Test successful OAuth callback."""
        with (
            patch("backend.routes.auth.create_oauth_flow") as mock_flow,
            patch("backend.routes.auth.get_google_user_info") as mock_user_info,
            patch("backend.routes.auth.get_database_session") as mock_db,
        ):

            # Setup mocks
            mock_flow_instance = Mock()
            mock_credentials = Mock()
            mock_credentials.token = "test-access-token"
            mock_credentials.refresh_token = "test-refresh-token"
            mock_credentials.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            mock_flow_instance.credentials = mock_credentials
            mock_flow.return_value = mock_flow_instance

            mock_user_info.return_value = {
                "email": "test@example.com",
                "name": "Test User",
            }

            mock_db.return_value.__aenter__ = lambda x: db_session
            mock_db.return_value.__aexit__ = lambda *args: None

            # Make request with session
            async with client.session_transaction() as sess:
                sess["oauth_state"] = "test-state"

            response = await client.get(
                "/auth/google/callback?code=test-code&state=test-state"
            )

            assert response.status_code == 302
            assert "myletters://auth?token=" in response.location

    @pytest.mark.asyncio
    async def test_oauth_callback_error(self, client):
        """Test OAuth callback with error."""
        response = await client.get("/auth/google/callback?error=access_denied")

        assert response.status_code == 302
        assert "myletters://auth?error=access_denied" in response.location

    @pytest.mark.asyncio
    async def test_get_user_authenticated(self, client, test_user, auth_headers):
        """Test getting user information when authenticated."""
        with patch("backend.utils.auth.get_async_session") as mock_db:
            mock_session = Mock()
            mock_session.get.return_value = test_user
            mock_db.return_value.__aenter__ = lambda x: mock_session
            mock_db.return_value.__aexit__ = lambda *args: None

            response = await client.get("/auth/user", headers=auth_headers)

            assert response.status_code == 200
            data = await response.get_json()
            assert data["email"] == test_user.email
            assert data["name"] == test_user.name

    @pytest.mark.asyncio
    async def test_get_user_unauthenticated(self, client):
        """Test getting user information without authentication."""
        response = await client.get("/auth/user")

        assert response.status_code == 401
        data = await response.get_json()
        assert data["error"] == "Authentication token required"

    @pytest.mark.asyncio
    async def test_token_validation(self, client, test_user, auth_headers):
        """Test token validation endpoint."""
        with patch("backend.utils.auth.get_async_session") as mock_db:
            mock_session = Mock()
            mock_session.get.return_value = test_user
            mock_db.return_value.__aenter__ = lambda x: mock_session
            mock_db.return_value.__aexit__ = lambda *args: None

            response = await client.post("/auth/validate", headers=auth_headers)

            assert response.status_code == 200
            data = await response.get_json()
            assert data["valid"] is True
            assert data["user_id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_token_refresh(self, client, test_user):
        """Test token refresh endpoint."""
        with patch("backend.utils.auth.get_async_session") as mock_db:
            mock_session = Mock()
            mock_session.get.return_value = test_user
            mock_db.return_value.__aenter__ = lambda x: mock_session
            mock_db.return_value.__aexit__ = lambda *args: None

            refresh_token = create_refresh_token(
                {"sub": str(test_user.id), "email": test_user.email}
            )

            response = await client.post(
                "/auth/refresh", json={"refresh_token": refresh_token}
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert "token" in data
            assert "refresh_token" in data
            assert "user" in data

    @pytest.mark.asyncio
    async def test_logout(self, client, auth_headers):
        """Test logout endpoint."""
        with patch("backend.utils.auth.get_async_session"):
            response = await client.post("/auth/logout", headers=auth_headers)

            assert response.status_code == 200
            data = await response.get_json()
            assert data["message"] == "Logged out successfully"

    @pytest.mark.asyncio
    async def test_update_profile(self, client, test_user, auth_headers):
        """Test profile update endpoint."""
        with patch("backend.utils.auth.get_async_session") as mock_db:
            mock_session = Mock()
            mock_session.get.return_value = test_user
            mock_session.add = Mock()
            mock_session.commit = Mock()
            mock_session.refresh = Mock()
            mock_db.return_value.__aenter__ = lambda x: mock_session
            mock_db.return_value.__aexit__ = lambda *args: None

            update_data = {
                "name": "Updated Name",
                "default_voice_type": "new_voice",
                "default_playback_speed": 1.5,
            }

            response = await client.put(
                "/auth/profile", headers=auth_headers, json=update_data
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["name"] == "Updated Name"


class TestAuthMiddleware:
    """Test authentication middleware functionality."""

    @pytest.mark.asyncio
    async def test_require_auth_valid_token(self, client, test_user, auth_token):
        """Test require_auth decorator with valid token."""
        with patch("backend.utils.auth.get_async_session") as mock_db:
            mock_session = Mock()
            mock_session.get.return_value = test_user
            mock_db.return_value.__aenter__ = lambda x: mock_session
            mock_db.return_value.__aexit__ = lambda *args: None

            # Test protected endpoint
            response = await client.post(
                "/start-briefing",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={"user_id": str(test_user.id)},
            )

            # Should not get 401 (might get other errors due to missing data, but not auth error)
            assert response.status_code != 401

    @pytest.mark.asyncio
    async def test_require_auth_invalid_token(self, client):
        """Test require_auth decorator with invalid token."""
        response = await client.post(
            "/start-briefing",
            headers={"Authorization": "Bearer invalid-token"},
            json={"user_id": "test-id"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_require_auth_missing_token(self, client):
        """Test require_auth decorator with missing token."""
        response = await client.post("/start-briefing", json={"user_id": "test-id"})

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_require_auth_malformed_header(self, client):
        """Test require_auth decorator with malformed Authorization header."""
        response = await client.post(
            "/start-briefing",
            headers={"Authorization": "InvalidFormat"},
            json={"user_id": "test-id"},
        )

        assert response.status_code == 401


class TestGoogleOAuthIntegration:
    """Test Google OAuth integration functions."""

    @patch("backend.utils.auth.build")
    def test_get_google_user_info(self, mock_build):
        """Test getting user info from Google API."""
        from backend.utils.auth import get_google_user_info

        # Setup mock
        mock_service = Mock()
        mock_userinfo = Mock()
        mock_userinfo.get.return_value.execute.return_value = {
            "email": "test@example.com",
            "name": "Test User",
            "id": "12345",
        }
        mock_service.userinfo.return_value = mock_userinfo
        mock_build.return_value = mock_service

        mock_credentials = Mock()
        result = get_google_user_info(mock_credentials)

        assert result["email"] == "test@example.com"
        assert result["name"] == "Test User"
        mock_build.assert_called_once_with("oauth2", "v2", credentials=mock_credentials)

    @patch("backend.utils.auth.Flow.from_client_config")
    def test_create_oauth_flow(self, mock_flow_class):
        """Test creating OAuth flow."""
        from backend.utils.auth import create_oauth_flow

        mock_flow = Mock()
        mock_flow_class.return_value = mock_flow

        result = create_oauth_flow()

        assert result == mock_flow
        mock_flow_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_google_credentials(self, db_session, test_user):
        """Test refreshing Google credentials."""
        from backend.utils.auth import refresh_google_credentials

        with (
            patch("backend.utils.auth.Credentials") as mock_creds_class,
            patch("backend.utils.auth.Request") as mock_request,
        ):

            mock_credentials = Mock()
            mock_credentials.expired = True
            mock_credentials.token = "new-token"
            mock_credentials.refresh_token = "new-refresh-token"
            mock_creds_class.return_value = mock_credentials

            # Set initial credentials on user
            test_user.google_refresh_token = "old-refresh-token"
            test_user.google_access_token = "old-token"

            result = await refresh_google_credentials(test_user, db_session)

            assert result == mock_credentials
            mock_credentials.refresh.assert_called_once()
