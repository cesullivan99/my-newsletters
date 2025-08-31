"""
Authentication utilities for JWT token management and OAuth flow.
"""

import secrets
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any

import jwt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from quart import g, jsonify, request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_config
from backend.models.database import User, get_async_session

settings = get_config()

# JWT Configuration
JWT_SECRET_KEY = settings.jwt_secret_key
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Google OAuth Configuration
GOOGLE_CLIENT_ID = settings.google_client_id
GOOGLE_CLIENT_SECRET = settings.google_client_secret
GOOGLE_REDIRECT_URI = f"{settings.backend_url}/auth/google/callback"

SCOPES = [
    "openid",  # Google automatically adds this, so we include it explicitly
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


class AuthError(Exception):
    """Custom authentication error."""

    pass


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """
    Create JWT access token.

    Args:
        data: Payload data to encode
        expires_delta: Token expiration time

    Returns:
        JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create JWT refresh token.

    Args:
        data: Payload data to encode

    Returns:
        JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> dict[str, Any]:
    """
    Verify JWT token and return payload.

    Args:
        token: JWT token to verify
        token_type: Expected token type (access or refresh)

    Returns:
        Token payload

    Raises:
        AuthError: If token is invalid
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])

        if payload.get("type") != token_type:
            raise AuthError(f"Invalid token type. Expected {token_type}")

        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired") from None
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token") from None


async def get_user_by_id(user_id: str, db: AsyncSession) -> User | None:
    """
    Get user by ID from database.

    Args:
        user_id: User UUID
        db: Database session

    Returns:
        User object or None
    """
    try:
        user = await db.get(User, user_id)
        return user
    except Exception as e:
        print(f"Error getting user {user_id}: {e}")
        return None


def create_oauth_flow() -> Flow:
    """
    Create Google OAuth 2.0 flow.

    Returns:
        OAuth flow object
    """
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [GOOGLE_REDIRECT_URI],
            }
        },
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )


def get_google_user_info(credentials: Credentials) -> dict[str, Any]:
    """
    Get user information from Google API.

    Args:
        credentials: Google OAuth credentials

    Returns:
        User information dictionary
    """
    service = build("oauth2", "v2", credentials=credentials)
    user_info = service.userinfo().get().execute()
    return user_info


def require_auth(f):
    """
    Decorator to require authentication for routes.

    Args:
        f: Route function to protect

    Returns:
        Decorated function
    """

    @wraps(f)
    async def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")

        if auth_header:
            if not auth_header.startswith('Bearer '):
                return jsonify({"error": "Invalid Authorization format"}), 401
            
            try:
                # Extract token from "Bearer <token>"
                token = auth_header.split(" ")[1]
                if not token:
                    return jsonify({"error": "Empty token"}), 401
            except IndexError:
                return jsonify({"error": "Invalid authorization header format"}), 401

        if not token:
            return jsonify({"error": "Missing Authorization header"}), 401

        try:
            # Verify token
            payload = verify_token(token, "access")
            user_id = payload.get("sub")

            if not user_id:
                return jsonify({"error": "Invalid token payload"}), 401

            # Get user from database
            async with get_async_session() as db:
                user = await get_user_by_id(user_id, db)
                if not user:
                    return jsonify({"error": "User not found"}), 401

                # Store user in request context
                g.current_user = user
                g.current_user_id = user_id

        except AuthError as e:
            error_message = str(e)
            if "expired" in error_message.lower():
                return jsonify({"error": "Token expired"}), 401
            elif "invalid" in error_message.lower():
                return jsonify({"error": "Invalid token"}), 401
            else:
                return jsonify({"error": str(e)}), 401
        except Exception as e:
            print(f"Auth error: {e}")
            return jsonify({"error": "Authentication failed"}), 401

        return await f(*args, **kwargs)

    return decorated_function


def optional_auth(f):
    """
    Decorator for optional authentication (sets user if token present).

    Args:
        f: Route function

    Returns:
        Decorated function
    """

    @wraps(f)
    async def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization")

        if auth_header:
            try:
                token = auth_header.split(" ")[1]
                payload = verify_token(token, "access")
                user_id = payload.get("sub")

                if user_id:
                    async with get_async_session() as db:
                        user = await get_user_by_id(user_id, db)
                        if user:
                            g.current_user = user
                            g.current_user_id = user_id
            except (AuthError, IndexError):
                # Continue without authentication
                pass

        return await f(*args, **kwargs)

    return decorated_function


async def refresh_google_credentials(
    user: User, db: AsyncSession
) -> Credentials | None:
    """
    Refresh Google OAuth credentials.

    Args:
        user: User object with stored credentials
        db: Database session

    Returns:
        Refreshed credentials or None
    """
    try:
        if not user.google_refresh_token:
            return None

        credentials = Credentials(
            token=user.google_access_token,
            refresh_token=user.google_refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        )

        # Refresh if needed
        if credentials.expired:
            credentials.refresh(Request())

            # Update stored credentials
            user.google_access_token = credentials.token
            if credentials.refresh_token:
                user.google_refresh_token = credentials.refresh_token

            await db.commit()

        return credentials

    except Exception as e:
        print(f"Error refreshing credentials for user {user.id}: {e}")
        return None


def generate_state_token() -> str:
    """
    Generate secure state token for OAuth flow.

    Returns:
        Random state token
    """
    return secrets.token_urlsafe(32)
