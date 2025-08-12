"""
Quart application entry point for newsletter briefing system.

Provides async API routes and WebSocket endpoints for voice-based
newsletter briefings with real-time interaction capabilities.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from quart import Quart, g, jsonify, request, websocket
from quart_cors import cors

from backend.config import get_database_session, settings, validate_environment
from backend.models.schemas import (
    BriefingRequest,
    BriefingResponse,
    ErrorResponse,
    HealthCheckResponse,
    SessionControlRequest,
    SessionProgressResponse,
)
from backend.routes.auth import auth_bp
from backend.services.session_manager import BriefingSessionManager
from backend.utils.auth import require_auth
from backend.voice.conversation_manager import conversation_pool

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create Quart app
app = Quart(__name__)
app.config.update(
    {
        "SECRET_KEY": settings.jwt_secret,
        "DEBUG": settings.app_debug,
        "TESTING": settings.is_testing,
    }
)

# Enable CORS for frontend integration
app = cors(
    app,
    allow_origin=settings.get_cors_origins(),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Total-Count", "X-Page"],
    max_age=3600,
)

# Register blueprints
app.register_blueprint(auth_bp)

# Import and register other blueprints
from backend.routes.newsletters import newsletters_bp
from backend.routes.briefing import briefing_bp
from backend.routes.audio import audio_bp
app.register_blueprint(newsletters_bp)
app.register_blueprint(briefing_bp)
app.register_blueprint(audio_bp)

# Track active connections
active_connections: dict[str, Any] = {}


@app.before_request
async def validate_request():
    """Validate all incoming requests."""
    # Check content-type for POST/PUT/PATCH (except file uploads)
    if request.method in ["POST", "PUT", "PATCH"]:
        # Allow multipart/form-data for file upload endpoints
        if request.path == "/audio/upload":
            pass  # Skip content-type validation for file uploads
        elif not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 415
    
    # Validate pagination parameters
    if "page" in request.args:
        try:
            page = int(request.args.get("page"))
            if page < 1:
                return jsonify({"error": "Page must be >= 1"}), 422
        except ValueError:
            return jsonify({"error": "Page must be an integer"}), 422
    
    if "limit" in request.args:
        try:
            limit = int(request.args.get("limit"))
            if limit < 1 or limit > 100:
                return jsonify({"error": "Limit must be between 1 and 100"}), 422
        except ValueError:
            return jsonify({"error": "Limit must be an integer"}), 422


@app.before_serving
async def startup():
    """Initialize application on startup."""
    try:
        validate_environment()
        logger.info("✅ Newsletter briefing API started successfully")
        logger.info(f"🚀 Server running on {settings.app_host}:{settings.app_port}")
    except Exception as e:
        logger.error(f"❌ Failed to start application: {e}")
        raise


@app.after_serving
async def shutdown():
    """Cleanup on application shutdown."""
    logger.info("🔄 Shutting down newsletter briefing API...")

    # Cleanup all active conversations
    await conversation_pool.cleanup_all()

    logger.info("✅ Application shutdown complete")


@app.errorhandler(ValidationError)
async def handle_validation_error(error):
    """Handle Pydantic validation errors."""
    return (
        jsonify(
            ErrorResponse(
                error="validation_error",
                message="Request validation failed",
                details={"errors": error.errors()},
            ).model_dump()
        ),
        400,
    )


@app.errorhandler(404)
async def handle_not_found(error):
    """Handle 404 errors."""
    return (
        jsonify({"error": "Endpoint not found", "path": request.path}),
        404,
    )


@app.errorhandler(500)
async def handle_internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return (
        jsonify({"error": "Internal server error"}),
        500,
    )


@app.errorhandler(Exception)
async def handle_general_error(error):
    """Handle general application errors."""
    logger.error(f"Unhandled error: {error}")
    return (
        jsonify(
            ErrorResponse(
                error="internal_error", message="An unexpected error occurred"
            ).model_dump()
        ),
        500,
    )


# Health check endpoint
@app.route("/health", methods=["GET"])
async def health_check():
    """
    Health check endpoint for monitoring.

    Returns:
        HealthCheckResponse: System health status
    """
    services_status = {
        "database": "healthy",  # We could add actual DB health checks here
        "elevenlabs": "healthy" if settings.elevenlabs_api_key else "not_configured",
        "openai": "healthy" if settings.openai_api_key else "not_configured",
    }

    overall_status = (
        "healthy"
        if all(status == "healthy" for status in services_status.values())
        else "degraded"
    )

    response = HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        services=services_status,
    )

    return jsonify(response.model_dump())


# Start briefing endpoint
@app.route("/start-briefing", methods=["POST"])
@require_auth
async def start_briefing():
    """
    Initialize daily briefing session.

    Creates a new briefing session with today's stories for the user
    and returns session information for voice interaction.
    """
    try:
        # Parse and validate request
        data = await request.get_json()
        briefing_request = BriefingRequest(**data)

        logger.info(f"Starting briefing for user {briefing_request.user_id}")

        async with get_database_session() as db_session:
            session_manager = BriefingSessionManager(db_session)

            # Get today's stories for the user
            stories = await session_manager.get_today_stories(briefing_request.user_id)

            if not stories:
                return (
                    jsonify(
                        ErrorResponse(
                            error="no_stories",
                            message="No stories available for today's briefing",
                        ).model_dump()
                    ),
                    404,
                )

            # Create briefing session
            story_ids = [story.id for story in stories]
            session = await session_manager.create_session(
                briefing_request.user_id, story_ids
            )

            # Build WebSocket URL
            websocket_url = f"{settings.websocket_url}/voice-stream/{session.id}"

            response = BriefingResponse(
                session_id=session.id,
                first_story_id=stories[0].id,
                total_stories=len(stories),
                websocket_url=websocket_url,
            )

            logger.info(
                f"Created briefing session {session.id} with {len(stories)} stories"
            )
            return jsonify(response.model_dump())

    except ValidationError as e:
        return (
            jsonify(
                ErrorResponse(
                    error="validation_error",
                    message="Invalid request data",
                    details={"errors": e.errors()},
                ).model_dump()
            ),
            400,
        )

    except Exception as e:
        logger.error(f"Error starting briefing: {e}")
        return (
            jsonify(
                ErrorResponse(
                    error="briefing_start_failed",
                    message="Failed to start briefing session",
                ).model_dump()
            ),
            500,
        )


# Session progress endpoint
@app.route("/session/<session_id>/progress", methods=["GET"])
async def get_session_progress(session_id: str):
    """
    Get current progress of a briefing session.

    Args:
        session_id: UUID of the briefing session

    Returns:
        SessionProgressResponse: Current session progress
    """
    try:
        session_uuid = UUID(session_id)

        async with get_database_session() as db_session:
            session_manager = BriefingSessionManager(db_session)
            progress = await session_manager.get_session_progress(session_uuid)

            if not progress:
                return (
                    jsonify(
                        ErrorResponse(
                            error="session_not_found",
                            message="Briefing session not found",
                        ).model_dump()
                    ),
                    404,
                )

            response = SessionProgressResponse(**progress)
            return jsonify(response.model_dump())

    except ValueError:
        return (
            jsonify(
                ErrorResponse(
                    error="invalid_session_id", message="Invalid session ID format"
                ).model_dump()
            ),
            400,
        )

    except Exception as e:
        logger.error(f"Error getting session progress: {e}")
        return (
            jsonify(
                ErrorResponse(
                    error="progress_fetch_failed",
                    message="Failed to get session progress",
                ).model_dump()
            ),
            500,
        )


# Session control endpoint
@app.route("/session/<session_id>/control", methods=["POST"])
async def control_session(session_id: str):
    """
    Control session playback (pause, resume, skip, etc.).

    Args:
        session_id: UUID of the briefing session

    Returns:
        Success response or error
    """
    try:
        session_uuid = UUID(session_id)
        data = await request.get_json()
        control_request = SessionControlRequest(**data)

        async with get_database_session() as db_session:
            session_manager = BriefingSessionManager(db_session)

            success = False
            if control_request.action == "pause":
                success = await session_manager.pause_session(session_uuid)
            elif control_request.action == "resume":
                success = await session_manager.resume_session(session_uuid)
            elif control_request.action == "skip":
                next_story = await session_manager.advance_story(session_uuid)
                success = next_story is not None
            else:
                return (
                    jsonify(
                        ErrorResponse(
                            error="invalid_action", message="Invalid control action"
                        ).model_dump()
                    ),
                    400,
                )

            if success:
                return jsonify({"status": "success", "action": control_request.action})
            else:
                return (
                    jsonify(
                        ErrorResponse(
                            error="control_failed",
                            message="Failed to execute control action",
                        ).model_dump()
                    ),
                    400,
                )

    except ValueError:
        return (
            jsonify(
                ErrorResponse(
                    error="invalid_session_id", message="Invalid session ID format"
                ).model_dump()
            ),
            400,
        )

    except Exception as e:
        logger.error(f"Error controlling session: {e}")
        return (
            jsonify(
                ErrorResponse(
                    error="control_failed", message="Failed to control session"
                ).model_dump()
            ),
            500,
        )


# WebSocket endpoint for voice streaming
@app.websocket("/voice-stream/<session_id>")
async def voice_stream(session_id: str):
    """
    Handle real-time voice communication with Vocode actions.

    This WebSocket endpoint manages the voice conversation for a briefing
    session, handling speech-to-text, action triggering, and text-to-speech.

    Args:
        session_id: UUID of the briefing session
    """
    try:
        UUID(session_id)  # Validate session_id format
        logger.info(f"Voice stream connected for session {session_id}")

        # Track connection
        active_connections[session_id] = {
            "connected_at": datetime.utcnow(),
            "websocket": websocket._get_current_object(),
        }

        # Get conversation manager
        conversation_manager = await conversation_pool.get_conversation_manager(
            session_id
        )

        # Start Vocode streaming conversation
        await conversation_manager.start_conversation(websocket)

    except ValueError:
        logger.error(f"Invalid session ID format: {session_id}")
        await websocket.send_json(
            {"type": "error", "message": "Invalid session ID format"}
        )

    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.send_json(
            {"type": "error", "message": "Voice stream error occurred"}
        )

    finally:
        # Clean up connection
        if session_id in active_connections:
            del active_connections[session_id]

        # Clean up conversation
        try:
            await conversation_pool.remove_conversation(session_id)
        except Exception as e:
            logger.error(f"Error cleaning up conversation: {e}")

        logger.info(f"Voice stream disconnected for session {session_id}")


# Additional API endpoints for frontend integration


@app.route("/briefing/<session_id>/state", methods=["GET"])
@require_auth
async def get_briefing_state(session_id: str):
    """Get current briefing session state."""
    try:
        session_uuid = UUID(session_id)

        async with get_database_session() as db_session:
            session_manager = BriefingSessionManager(db_session)
            session = await session_manager.get_session(session_uuid)

            if not session:
                return (
                    jsonify(
                        ErrorResponse(
                            error="session_not_found",
                            message="Briefing session not found",
                        ).model_dump()
                    ),
                    404,
                )

            return jsonify(
                {
                    "session_id": str(session.id),
                    "current_story_id": (
                        str(session.current_story_id)
                        if session.current_story_id
                        else None
                    ),
                    "current_story_index": session.current_story_index,
                    "session_status": session.session_status,
                    "total_stories": len(session.story_order),
                }
            )
    except Exception as e:
        logger.error(f"Error getting briefing state: {e}")
        return jsonify({"error": "Failed to get session state"}), 500


@app.route("/briefing/<session_id>/current-story", methods=["GET"])
@require_auth
async def get_current_story(session_id: str):
    """Get current story in briefing session."""
    try:
        session_uuid = UUID(session_id)

        async with get_database_session() as db_session:
            session_manager = BriefingSessionManager(db_session)
            story = await session_manager.get_current_story(session_uuid)

            if not story:
                return jsonify({"error": "No current story"}), 404

            return jsonify(
                {
                    "id": str(story.id),
                    "headline": story.headline,
                    "one_sentence_summary": story.one_sentence_summary,
                    "full_text_summary": story.full_text_summary,
                    "audio_url": story.summary_audio_url,
                    "newsletter_name": story.issue.newsletter.name,
                    "published_at": story.issue.date.isoformat(),
                }
            )
    except Exception as e:
        logger.error(f"Error getting current story: {e}")
        return jsonify({"error": "Failed to get current story"}), 500


@app.route("/briefing/<session_id>/pause", methods=["POST"])
@require_auth
async def pause_briefing(session_id: str):
    """Pause briefing session."""
    try:
        session_uuid = UUID(session_id)

        async with get_database_session() as db_session:
            session_manager = BriefingSessionManager(db_session)
            success = await session_manager.pause_session(session_uuid)

            if success:
                return jsonify({"status": "paused"})
            else:
                return jsonify({"error": "Failed to pause session"}), 400
    except Exception as e:
        logger.error(f"Error pausing briefing: {e}")
        return jsonify({"error": "Failed to pause briefing"}), 500


@app.route("/briefing/<session_id>/resume", methods=["POST"])
@require_auth
async def resume_briefing(session_id: str):
    """Resume briefing session."""
    try:
        session_uuid = UUID(session_id)

        async with get_database_session() as db_session:
            session_manager = BriefingSessionManager(db_session)
            success = await session_manager.resume_session(session_uuid)

            if success:
                return jsonify({"status": "playing"})
            else:
                return jsonify({"error": "Failed to resume session"}), 400
    except Exception as e:
        logger.error(f"Error resuming briefing: {e}")
        return jsonify({"error": "Failed to resume briefing"}), 500


@app.route("/briefing/<session_id>/skip", methods=["POST"])
@require_auth
async def skip_story(session_id: str):
    """Skip to next story in briefing."""
    try:
        session_uuid = UUID(session_id)

        async with get_database_session() as db_session:
            session_manager = BriefingSessionManager(db_session)
            next_story = await session_manager.advance_story(session_uuid)

            if next_story:
                return jsonify(
                    {
                        "next_story": {
                            "id": str(next_story.id),
                            "headline": next_story.headline,
                            "one_sentence_summary": next_story.one_sentence_summary,
                            "audio_url": next_story.summary_audio_url,
                            "newsletter_name": next_story.issue.newsletter.name,
                            "published_at": next_story.issue.date.isoformat(),
                        }
                    }
                )
            else:
                return jsonify({"next_story": None})
    except Exception as e:
        logger.error(f"Error skipping story: {e}")
        return jsonify({"error": "Failed to skip story"}), 500


@app.route("/briefing/<session_id>/detailed-summary", methods=["GET"])
@require_auth
async def get_detailed_summary(session_id: str):
    """Get detailed summary of current story."""
    try:
        session_uuid = UUID(session_id)

        async with get_database_session() as db_session:
            session_manager = BriefingSessionManager(db_session)
            detailed_summary = await session_manager.get_detailed_summary(session_uuid)

            if detailed_summary:
                return jsonify({"detailed_summary": detailed_summary})
            else:
                return jsonify({"error": "No detailed summary available"}), 404
    except Exception as e:
        logger.error(f"Error getting detailed summary: {e}")
        return jsonify({"error": "Failed to get detailed summary"}), 500


@app.route("/users/<user_id>/newsletters", methods=["GET"])
@require_auth
async def get_user_newsletters(user_id: str):
    """Get user's newsletter subscriptions."""
    try:
        # For now, return empty list - would be implemented with actual newsletter data
        return jsonify({"newsletters": []})
    except Exception as e:
        logger.error(f"Error getting user newsletters: {e}")
        return jsonify({"error": "Failed to get newsletters"}), 500


@app.route("/users/<user_id>/preferences", methods=["PUT"])
@require_auth
async def update_user_preferences(user_id: str):
    """Update user preferences."""
    try:
        _ = await request.get_json()  # Get request data (not used in stub)
        _ = g.current_user  # Access current user (not used in stub)

        # Update preferences would be handled here
        return jsonify({"status": "updated"})
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        return jsonify({"error": "Failed to update preferences"}), 500


# Active sessions endpoint
@app.route("/sessions/active", methods=["GET"])
async def get_active_sessions():
    """
    Get list of currently active voice sessions.

    Returns:
        List of active session information
    """
    active_sessions = []

    for session_id, connection_info in active_connections.items():
        active_sessions.append(
            {
                "session_id": session_id,
                "connected_at": connection_info["connected_at"].isoformat(),
                "status": "active",
            }
        )

    return jsonify(
        {"active_sessions": active_sessions, "total_count": len(active_sessions)}
    )


# Run the application
if __name__ == "__main__":
    """Run the application directly."""
    app.run(host=settings.app_host, port=settings.app_port, debug=settings.app_debug)
