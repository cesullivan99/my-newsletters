"""
Quart application entry point for newsletter briefing system.

Provides async API routes and WebSocket endpoints for voice-based
newsletter briefings with real-time interaction capabilities.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from quart import Quart, request, jsonify, websocket
from quart_cors import cors
from pydantic import ValidationError

from backend.config import settings, validate_environment, get_database_session
from backend.models.schemas import (
    BriefingRequest, BriefingResponse, SessionProgressResponse,
    SessionControlRequest, ErrorResponse, HealthCheckResponse
)
from backend.services.session_manager import BriefingSessionManager
from backend.voice.conversation_manager import conversation_pool

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Quart app
app = Quart(__name__)
app.config.update({
    'SECRET_KEY': settings.jwt_secret,
    'DEBUG': settings.app_debug,
    'TESTING': settings.is_testing,
})

# Enable CORS for frontend integration
app = cors(app, allow_origin=settings.get_cors_origins())

# Track active connections
active_connections: Dict[str, Any] = {}


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
    return jsonify(ErrorResponse(
        error="validation_error",
        message="Request validation failed",
        details={"errors": error.errors()}
    ).model_dump()), 400


@app.errorhandler(Exception)
async def handle_general_error(error):
    """Handle general application errors."""
    logger.error(f"Unhandled error: {error}")
    return jsonify(ErrorResponse(
        error="internal_error",
        message="An unexpected error occurred"
    ).model_dump()), 500


# Health check endpoint
@app.route('/health', methods=['GET'])
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
    
    overall_status = "healthy" if all(
        status == "healthy" for status in services_status.values()
    ) else "degraded"
    
    response = HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        services=services_status
    )
    
    return jsonify(response.model_dump())


# Start briefing endpoint
@app.route('/start-briefing', methods=['POST'])
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
                return jsonify(ErrorResponse(
                    error="no_stories",
                    message="No stories available for today's briefing"
                ).model_dump()), 404
            
            # Create briefing session
            story_ids = [story.id for story in stories]
            session = await session_manager.create_session(
                briefing_request.user_id, 
                story_ids
            )
            
            # Build WebSocket URL
            websocket_url = f"{settings.websocket_url}/voice-stream/{session.id}"
            
            response = BriefingResponse(
                session_id=session.id,
                first_story_id=stories[0].id,
                total_stories=len(stories),
                websocket_url=websocket_url
            )
            
            logger.info(f"Created briefing session {session.id} with {len(stories)} stories")
            return jsonify(response.model_dump())
    
    except ValidationError as e:
        return jsonify(ErrorResponse(
            error="validation_error",
            message="Invalid request data",
            details={"errors": e.errors()}
        ).model_dump()), 400
    
    except Exception as e:
        logger.error(f"Error starting briefing: {e}")
        return jsonify(ErrorResponse(
            error="briefing_start_failed",
            message="Failed to start briefing session"
        ).model_dump()), 500


# Session progress endpoint
@app.route('/session/<session_id>/progress', methods=['GET'])
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
                return jsonify(ErrorResponse(
                    error="session_not_found",
                    message="Briefing session not found"
                ).model_dump()), 404
            
            response = SessionProgressResponse(**progress)
            return jsonify(response.model_dump())
    
    except ValueError:
        return jsonify(ErrorResponse(
            error="invalid_session_id",
            message="Invalid session ID format"
        ).model_dump()), 400
    
    except Exception as e:
        logger.error(f"Error getting session progress: {e}")
        return jsonify(ErrorResponse(
            error="progress_fetch_failed",
            message="Failed to get session progress"
        ).model_dump()), 500


# Session control endpoint
@app.route('/session/<session_id>/control', methods=['POST'])
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
                return jsonify(ErrorResponse(
                    error="invalid_action",
                    message="Invalid control action"
                ).model_dump()), 400
            
            if success:
                return jsonify({"status": "success", "action": control_request.action})
            else:
                return jsonify(ErrorResponse(
                    error="control_failed",
                    message="Failed to execute control action"
                ).model_dump()), 400
    
    except ValueError:
        return jsonify(ErrorResponse(
            error="invalid_session_id",
            message="Invalid session ID format"
        ).model_dump()), 400
    
    except Exception as e:
        logger.error(f"Error controlling session: {e}")
        return jsonify(ErrorResponse(
            error="control_failed",
            message="Failed to control session"
        ).model_dump()), 500


# WebSocket endpoint for voice streaming
@app.websocket('/voice-stream/<session_id>')
async def voice_stream(session_id: str):
    """
    Handle real-time voice communication with Vocode actions.
    
    This WebSocket endpoint manages the voice conversation for a briefing
    session, handling speech-to-text, action triggering, and text-to-speech.
    
    Args:
        session_id: UUID of the briefing session
    """
    try:
        session_uuid = UUID(session_id)
        logger.info(f"Voice stream connected for session {session_id}")
        
        # Track connection
        active_connections[session_id] = {
            "connected_at": datetime.utcnow(),
            "websocket": websocket._get_current_object()
        }
        
        # Get conversation manager
        conversation_manager = await conversation_pool.get_conversation_manager(session_id)
        
        # Start Vocode streaming conversation
        await conversation_manager.start_conversation(websocket)
        
    except ValueError:
        logger.error(f"Invalid session ID format: {session_id}")
        await websocket.send_json({
            "type": "error",
            "message": "Invalid session ID format"
        })
    
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.send_json({
            "type": "error",
            "message": "Voice stream error occurred"
        })
    
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


# Active sessions endpoint
@app.route('/sessions/active', methods=['GET'])
async def get_active_sessions():
    """
    Get list of currently active voice sessions.
    
    Returns:
        List of active session information
    """
    active_sessions = []
    
    for session_id, connection_info in active_connections.items():
        active_sessions.append({
            "session_id": session_id,
            "connected_at": connection_info["connected_at"].isoformat(),
            "status": "active"
        })
    
    return jsonify({
        "active_sessions": active_sessions,
        "total_count": len(active_sessions)
    })


# Run the application
if __name__ == "__main__":
    """Run the application directly."""
    app.run(
        host=settings.app_host,
        port=settings.app_port,
        debug=settings.app_debug
    )