"""
Authentication routes for OAuth flow and JWT token management.
"""

import logging
import uuid
from datetime import UTC

from google.oauth2.credentials import Credentials
from quart import Blueprint, g, jsonify, redirect, request, session
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_database_session
from backend.models.database import User
from backend.utils.auth import (
    AuthError,
    create_access_token,
    create_oauth_flow,
    create_refresh_token,
    generate_state_token,
    get_google_user_info,
    require_auth,
    verify_token,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)


@auth_bp.route("/gmail-oauth", methods=["POST"])
async def gmail_oauth():
    """
    Start Gmail OAuth 2.0 flow.

    Returns JSON with OAuth URL instead of redirecting.

    Returns:
        JSON with auth_url for frontend to redirect to
    """
    try:
        # Generate state token for CSRF protection
        state_token = generate_state_token()
        session["oauth_state"] = state_token

        # Create OAuth flow
        flow = create_oauth_flow()

        # Generate authorization URL
        authorization_url, _ = flow.authorization_url(
            access_type="offline",  # Get refresh token
            include_granted_scopes="true",
            state=state_token,
            prompt="consent",  # Force consent screen to get refresh token
        )

        return jsonify({"auth_url": authorization_url})

    except Exception as e:
        logger.error(f"Error starting OAuth flow: {e}")
        return jsonify({"error": "Failed to start authentication"}), 500


@auth_bp.route("/google/callback")
async def google_callback():
    """
    Handle Google OAuth 2.0 callback.

    Processes the authorization code and creates/updates user account.

    Returns:
        Redirect to frontend with token or error
    """
    try:
        # Get authorization code from query parameters
        code = request.args.get("code")
        state = request.args.get("state")
        error = request.args.get("error")

        if error:
            print(f"OAuth error: {error}")
            return redirect(f"myletters://auth?error={error}")

        if not code:
            return jsonify({"error": "Missing authorization code"}), 400

        # Verify state token
        stored_state = session.get("oauth_state")
        if not stored_state or state != stored_state:
            return jsonify({"error": "Invalid state token"}), 422

        # Exchange code for tokens
        flow = create_oauth_flow()
        flow.fetch_token(code=code)

        # Get credentials
        credentials = flow.credentials

        # Get user information from Google
        user_info = get_google_user_info(credentials)

        # Create or update user in database
        async with get_database_session() as db:
            user = await get_or_create_user(
                db=db,
                email=user_info["email"],
                name=user_info["name"],
                credentials=credentials,
            )

            # Create JWT tokens
            token_data = {"sub": str(user.id), "email": user.email}
            access_token = create_access_token(token_data)
            refresh_token = create_refresh_token(token_data)

        # Redirect to mobile app with tokens
        return redirect(
            f"myletters://auth?token={access_token}&refresh_token={refresh_token}"
        )

    except Exception as e:
        print(f"Error in OAuth callback: {e}")
        return redirect("myletters://auth?error=callback_failed")


@auth_bp.route("/user")
@require_auth
async def get_user():
    """
    Get current authenticated user information.

    Returns:
        User profile data
    """
    try:
        user = g.current_user
        return jsonify(
            {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "default_voice_type": user.default_voice_type,
                "default_playback_speed": user.default_playback_speed,
                "created_at": user.created_at.isoformat(),
            }
        )
    except Exception as e:
        print(f"Error getting user: {e}")
        return jsonify({"error": "Failed to get user information"}), 500


@auth_bp.route("/refresh", methods=["POST"])
async def refresh_token():
    """
    Refresh JWT access token using refresh token.

    Returns:
        New access token and user data
    """
    try:
        # Get refresh token from request
        data = await request.get_json()
        refresh_token_str = data.get("refresh_token")

        if not refresh_token_str:
            # Try to get from Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header:
                refresh_token_str = auth_header.split(" ")[1]

        if not refresh_token_str:
            return jsonify({"error": "Refresh token required"}), 401

        # Verify refresh token
        payload = verify_token(refresh_token_str, "refresh")
        user_id = payload.get("sub")

        if not user_id:
            return jsonify({"error": "Invalid token payload"}), 401

        # Get user from database
        async with get_database_session() as db:
            user = await db.get(User, user_id)
            if not user:
                return jsonify({"error": "User not found"}), 401

            # Create new tokens
            token_data = {"sub": str(user.id), "email": user.email}
            new_access_token = create_access_token(token_data)
            new_refresh_token = create_refresh_token(token_data)

            return jsonify(
                {
                    "token": new_access_token,
                    "refresh_token": new_refresh_token,
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": user.name,
                        "default_voice_type": user.default_voice_type,
                        "default_playback_speed": user.default_playback_speed,
                    },
                }
            )

    except AuthError as e:
        return jsonify({"error": str(e)}), 401
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return jsonify({"error": "Token refresh failed"}), 500


@auth_bp.route("/validate", methods=["POST"])
@require_auth
async def validate_token_endpoint():
    """
    Validate JWT access token.

    Returns:
        Token validation status
    """
    try:
        # If we get here, token is valid (require_auth decorator validates)
        user = g.current_user
        return jsonify({"valid": True, "user_id": str(user.id), "email": user.email})
    except Exception as e:
        print(f"Error validating token: {e}")
        return jsonify({"valid": False, "error": "Token validation failed"}), 401


@auth_bp.route("/logout", methods=["POST"])
@require_auth
async def logout():
    """
    Logout user (invalidate tokens on client side).

    In a production app, you might want to maintain a token blacklist.

    Returns:
        Logout success message
    """
    try:
        # Clear session data
        session.clear()

        return jsonify({"message": "Logged out successfully"})
    except Exception as e:
        print(f"Error during logout: {e}")
        return jsonify({"error": "Logout failed"}), 500


@auth_bp.route("/profile", methods=["PUT"])
@require_auth
async def update_profile():
    """
    Update user profile settings.

    Returns:
        Updated user profile
    """
    try:
        user = g.current_user
        data = await request.get_json()

        # Update allowed fields
        if "name" in data:
            user.name = data["name"]
        if "default_voice_type" in data:
            user.default_voice_type = data["default_voice_type"]
        if "default_playback_speed" in data:
            user.default_playback_speed = float(data["default_playback_speed"])
        if "summarization_depth" in data:
            user.summarization_depth = data["summarization_depth"]

        async with get_database_session() as db:
            db.add(user)
            await db.commit()
            await db.refresh(user)

        return jsonify(
            {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "default_voice_type": user.default_voice_type,
                "default_playback_speed": user.default_playback_speed,
                "summarization_depth": user.summarization_depth,
            }
        )

    except Exception as e:
        print(f"Error updating profile: {e}")
        return jsonify({"error": "Failed to update profile"}), 500


async def get_or_create_user(
    db: AsyncSession, email: str, name: str, credentials: Credentials
) -> User:
    """
    Get existing user or create new one.

    Args:
        db: Database session
        email: User email
        name: User name
        credentials: Google OAuth credentials

    Returns:
        User object
    """
    # Check if user exists
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        # Update existing user's credentials
        user.google_access_token = credentials.token
        if credentials.refresh_token:
            user.google_refresh_token = credentials.refresh_token
        if credentials.expiry:
            user.google_token_expires_at = credentials.expiry.replace(tzinfo=UTC)
    else:
        # Create new user
        user = User(
            id=uuid.uuid4(),
            email=email,
            name=name,
            google_access_token=credentials.token,
            google_refresh_token=credentials.refresh_token,
            google_token_expires_at=(
                credentials.expiry.replace(tzinfo=UTC) if credentials.expiry else None
            ),
        )
        db.add(user)

    await db.commit()
    await db.refresh(user)
    return user
