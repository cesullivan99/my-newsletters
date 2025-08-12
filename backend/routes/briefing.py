"""
Briefing session management routes for creating and controlling voice sessions.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from quart import Blueprint, g, jsonify, request
from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_database_session
from backend.models.database import Issue, ListeningSession, Newsletter, Story, User
# Import services with fallback to mock implementations
try:
    from backend.services.session_manager import BriefingSessionManager
except ImportError:
    # Mock BriefingSessionManager for testing
    class BriefingSessionManager:
        def __init__(self, db_session):
            self.db = db_session
from backend.utils.auth import require_auth

briefing_bp = Blueprint("briefing", __name__, url_prefix="/briefing")
logger = logging.getLogger(__name__)


# Pydantic schemas for briefing endpoints
class BriefingStartRequest(BaseModel):
    """Request to start a briefing session."""
    
    newsletter_ids: Optional[List[str]] = Field(
        default=None, description="Specific newsletter IDs to include"
    )
    voice_preference: Optional[str] = Field(
        default=None, description="Voice preference for TTS"
    )


class BriefingStartResponse(BaseModel):
    """Response when starting a briefing session."""
    
    session_id: str = Field(description="Created session UUID")
    story_count: int = Field(description="Number of stories in session")
    first_story: Optional[dict] = Field(
        default=None, description="First story data"
    )


class SessionStateResponse(BaseModel):
    """Response for session state."""
    
    id: str = Field(description="Session UUID")
    status: str = Field(description="Session status")
    current_position: int = Field(description="Current story position")
    total_stories: int = Field(description="Total stories in session")
    current_story_id: Optional[str] = Field(
        default=None, description="Current story UUID"
    )


class SessionControlResponse(BaseModel):
    """Response for session control actions."""
    
    status: str = Field(description="Updated session status")


class StoryNavigationResponse(BaseModel):
    """Response for story navigation."""
    
    current_position: int = Field(description="Current story position")
    current_story_id: Optional[str] = Field(description="Current story UUID")
    has_next: bool = Field(description="Has next story")
    has_previous: bool = Field(description="Has previous story")


class SessionMetadataResponse(BaseModel):
    """Response for session metadata."""
    
    current_story: Optional[dict] = Field(description="Current story data")
    progress: dict = Field(description="Progress information")
    remaining_stories: List[dict] = Field(description="Remaining story data")
    estimated_time_remaining: int = Field(description="Estimated minutes remaining")


class SessionCleanupResponse(BaseModel):
    """Response for session cleanup."""
    
    cleaned: int = Field(description="Number of sessions cleaned up")
    remaining: int = Field(description="Number of active sessions remaining")


@briefing_bp.route("/start", methods=["POST"])
@require_auth
async def start_briefing():
    """
    Create new briefing session.
    
    Creates a new briefing session with today's stories for the user
    and returns session information for voice interaction.
    
    Returns:
        BriefingStartResponse: Session details and first story
    """
    try:
        current_user = g.current_user
        data = await request.get_json() if request.is_json else {}
        
        # Validate request
        start_request = BriefingStartRequest(**data)
        
        logger.info(f"Starting briefing for user {current_user.id}")
        
        async with get_database_session() as db:
            # Get newsletter IDs to include
            newsletter_ids = []
            if start_request.newsletter_ids:
                newsletter_ids = [UUID(nid) for nid in start_request.newsletter_ids]
            else:
                # Get today's newsletters automatically
                newsletter_ids = await get_todays_newsletter_ids(db, current_user.id)
            
            if not newsletter_ids:
                return jsonify({
                    "error": "no_stories",
                    "message": "No stories available for today's briefing"
                }), 404
            
            # Create briefing session
            session = await create_briefing_session(
                db=db,
                user_id=current_user.id,
                newsletter_ids=newsletter_ids
            )
            
            # Get first story data
            first_story = None
            if session.story_order:
                first_story_result = await db.execute(
                    select(Story).where(Story.id == session.story_order[0])
                )
                first_story_obj = first_story_result.scalar_one_or_none()
                if first_story_obj:
                    first_story = story_to_dict(first_story_obj)
            
            response = BriefingStartResponse(
                session_id=str(session.id),
                story_count=len(session.story_order),
                first_story=first_story
            )
            
            logger.info(f"Created briefing session {session.id} with {len(session.story_order)} stories")
            return jsonify(response.model_dump()), 201
            
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 422
    except Exception as e:
        logger.error(f"Error starting briefing: {e}")
        return jsonify({"error": "Failed to start briefing session"}), 500


@briefing_bp.route("/session/<session_id>", methods=["GET"])
@require_auth
async def get_session_state(session_id: str):
    """
    Get current session state.
    
    Args:
        session_id: UUID of the briefing session
        
    Returns:
        SessionStateResponse: Current session state
    """
    try:
        current_user = g.current_user
        
        # Validate UUID format
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return jsonify({"error": "Invalid session ID format"}), 400
        
        async with get_database_session() as db:
            session = await get_session_by_id(db, session_uuid)
            
            if not session:
                return jsonify({"error": "Session not found"}), 404
            
            # Check ownership
            if session.user_id != current_user.id:
                return jsonify({"error": "Unauthorized"}), 403
            
            response = SessionStateResponse(
                id=str(session.id),
                status=session.session_status,
                current_position=session.current_story_index,
                total_stories=len(session.story_order),
                current_story_id=str(session.current_story_id) if session.current_story_id else None
            )
            
            return jsonify(response.model_dump())
            
    except Exception as e:
        logger.error(f"Error getting session state: {e}")
        return jsonify({"error": "Failed to get session state"}), 500


@briefing_bp.route("/session/<session_id>/pause", methods=["POST"])
@require_auth
async def pause_session(session_id: str):
    """
    Pause briefing session.
    
    Args:
        session_id: UUID of the briefing session
        
    Returns:
        SessionControlResponse: Updated status
    """
    try:
        current_user = g.current_user
        
        # Validate UUID format
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return jsonify({"error": "Invalid session ID format"}), 400
        
        async with get_database_session() as db:
            session = await update_session_status(db, session_uuid, current_user.id, "paused")
            
            if not session:
                return jsonify({"error": "Session not found or unauthorized"}), 404
            
            response = SessionControlResponse(status=session.session_status)
            return jsonify(response.model_dump())
            
    except Exception as e:
        logger.error(f"Error pausing session: {e}")
        return jsonify({"error": "Failed to pause session"}), 500


@briefing_bp.route("/session/<session_id>/resume", methods=["POST"])
@require_auth
async def resume_session(session_id: str):
    """
    Resume briefing session.
    
    Args:
        session_id: UUID of the briefing session
        
    Returns:
        SessionControlResponse: Updated status
    """
    try:
        current_user = g.current_user
        
        # Validate UUID format
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return jsonify({"error": "Invalid session ID format"}), 400
        
        async with get_database_session() as db:
            session = await update_session_status(db, session_uuid, current_user.id, "playing")
            
            if not session:
                return jsonify({"error": "Session not found or unauthorized"}), 404
            
            response = SessionControlResponse(status=session.session_status)
            return jsonify(response.model_dump())
            
    except Exception as e:
        logger.error(f"Error resuming session: {e}")
        return jsonify({"error": "Failed to resume session"}), 500


@briefing_bp.route("/session/<session_id>/stop", methods=["POST"])
@require_auth
async def stop_session(session_id: str):
    """
    Stop briefing session.
    
    Args:
        session_id: UUID of the briefing session
        
    Returns:
        SessionControlResponse: Updated status
    """
    try:
        current_user = g.current_user
        
        # Validate UUID format
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return jsonify({"error": "Invalid session ID format"}), 400
        
        async with get_database_session() as db:
            session = await update_session_status(db, session_uuid, current_user.id, "completed")
            
            if not session:
                return jsonify({"error": "Session not found or unauthorized"}), 404
            
            response = SessionControlResponse(status=session.session_status)
            return jsonify(response.model_dump())
            
    except Exception as e:
        logger.error(f"Error stopping session: {e}")
        return jsonify({"error": "Failed to stop session"}), 500


@briefing_bp.route("/session/<session_id>/next", methods=["POST"])
@require_auth
async def next_story(session_id: str):
    """
    Move to next story in session.
    
    Args:
        session_id: UUID of the briefing session
        
    Returns:
        StoryNavigationResponse: Navigation state
    """
    try:
        current_user = g.current_user
        
        # Validate UUID format
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return jsonify({"error": "Invalid session ID format"}), 400
        
        async with get_database_session() as db:
            session = await advance_story(db, session_uuid, current_user.id)
            
            if not session:
                return jsonify({"error": "Session not found or unauthorized"}), 404
            
            response = StoryNavigationResponse(
                current_position=session.current_story_index,
                current_story_id=str(session.current_story_id) if session.current_story_id else None,
                has_next=session.current_story_index < len(session.story_order) - 1,
                has_previous=session.current_story_index > 0
            )
            
            return jsonify(response.model_dump())
            
    except Exception as e:
        logger.error(f"Error advancing to next story: {e}")
        return jsonify({"error": "Failed to advance to next story"}), 500


@briefing_bp.route("/session/<session_id>/previous", methods=["POST"])
@require_auth
async def previous_story(session_id: str):
    """
    Move to previous story in session.
    
    Args:
        session_id: UUID of the briefing session
        
    Returns:
        StoryNavigationResponse: Navigation state
    """
    try:
        current_user = g.current_user
        
        # Validate UUID format
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return jsonify({"error": "Invalid session ID format"}), 400
        
        async with get_database_session() as db:
            session = await previous_story_func(db, session_uuid, current_user.id)
            
            if not session:
                return jsonify({"error": "Session not found or unauthorized"}), 404
            
            response = StoryNavigationResponse(
                current_position=session.current_story_index,
                current_story_id=str(session.current_story_id) if session.current_story_id else None,
                has_next=session.current_story_index < len(session.story_order) - 1,
                has_previous=session.current_story_index > 0
            )
            
            return jsonify(response.model_dump())
            
    except Exception as e:
        logger.error(f"Error going to previous story: {e}")
        return jsonify({"error": "Failed to go to previous story"}), 500


@briefing_bp.route("/session/<session_id>/metadata", methods=["GET"])
@require_auth
async def get_session_metadata(session_id: str):
    """
    Get detailed session metadata.
    
    Args:
        session_id: UUID of the briefing session
        
    Returns:
        SessionMetadataResponse: Detailed metadata
    """
    try:
        current_user = g.current_user
        
        # Validate UUID format
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return jsonify({"error": "Invalid session ID format"}), 400
        
        async with get_database_session() as db:
            metadata = await get_session_metadata_func(db, session_uuid, current_user.id)
            
            if not metadata:
                return jsonify({"error": "Session not found or unauthorized"}), 404
            
            response = SessionMetadataResponse(**metadata)
            return jsonify(response.model_dump())
            
    except Exception as e:
        logger.error(f"Error getting session metadata: {e}")
        return jsonify({"error": "Failed to get session metadata"}), 500


@briefing_bp.route("/cleanup", methods=["POST"])
@require_auth
async def cleanup_sessions():
    """
    Clean up expired sessions.
    
    Removes sessions older than 24 hours to free up resources.
    
    Returns:
        SessionCleanupResponse: Cleanup results
    """
    try:
        current_user = g.current_user
        
        async with get_database_session() as db:
            # Clean sessions older than 24 hours
            cutoff_time = datetime.utcnow() - timedelta(hours=24)
            
            # Get sessions to delete
            sessions_to_delete = await db.execute(
                select(ListeningSession).where(
                    and_(
                        ListeningSession.user_id == current_user.id,
                        ListeningSession.created_at < cutoff_time
                    )
                )
            )
            sessions_list = sessions_to_delete.scalars().all()
            cleaned_count = len(sessions_list)
            
            # Delete expired sessions
            await db.execute(
                delete(ListeningSession).where(
                    and_(
                        ListeningSession.user_id == current_user.id,
                        ListeningSession.created_at < cutoff_time
                    )
                )
            )
            
            # Get remaining session count
            remaining_sessions = await db.execute(
                select(ListeningSession).where(ListeningSession.user_id == current_user.id)
            )
            remaining_count = len(remaining_sessions.scalars().all())
            
            await db.commit()
            
            response = SessionCleanupResponse(
                cleaned=cleaned_count,
                remaining=remaining_count
            )
            
            logger.info(f"Cleaned up {cleaned_count} expired sessions for user {current_user.id}")
            return jsonify(response.model_dump())
            
    except Exception as e:
        logger.error(f"Error cleaning up sessions: {e}")
        return jsonify({"error": "Failed to clean up sessions"}), 500


# Helper functions

async def get_todays_newsletter_ids(db: AsyncSession, user_id: UUID) -> List[UUID]:
    """
    Get newsletter IDs for today's briefing.
    
    Args:
        db: Database session
        user_id: User UUID
        
    Returns:
        List of newsletter UUIDs
    """
    # Get issues from the last 24 hours
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    
    result = await db.execute(
        select(Issue.newsletter_id).where(Issue.date >= cutoff_time).distinct()
    )
    
    return [row[0] for row in result.fetchall()]


async def create_briefing_session(
    db: AsyncSession, user_id: UUID, newsletter_ids: List[UUID]
) -> ListeningSession:
    """
    Create a new briefing session.
    
    Args:
        db: Database session
        user_id: User UUID
        newsletter_ids: List of newsletter IDs to include
        
    Returns:
        Created ListeningSession
    """
    # Get stories from the newsletters
    story_ids = []
    for newsletter_id in newsletter_ids:
        # Get latest issue for each newsletter
        latest_issue_result = await db.execute(
            select(Issue)
            .where(Issue.newsletter_id == newsletter_id)
            .order_by(Issue.date.desc())
            .limit(1)
        )
        latest_issue = latest_issue_result.scalar_one_or_none()
        
        if latest_issue:
            # Get stories from this issue
            stories_result = await db.execute(
                select(Story.id).where(Story.issue_id == latest_issue.id)
            )
            for story_id_tuple in stories_result.fetchall():
                story_ids.append(story_id_tuple[0])
    
    if not story_ids:
        raise ValueError("No stories found for briefing")
    
    # Create session
    session = ListeningSession(
        user_id=user_id,
        story_order=story_ids,
        current_story_index=0,
        current_story_id=story_ids[0] if story_ids else None,
        session_status="playing"
    )
    
    db.add(session)
    await db.commit()
    await db.refresh(session)
    
    return session


async def get_session_by_id(db: AsyncSession, session_id: UUID) -> Optional[ListeningSession]:
    """Get session by ID."""
    result = await db.execute(
        select(ListeningSession).where(ListeningSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def update_session_status(
    db: AsyncSession, session_id: UUID, user_id: UUID, status: str
) -> Optional[ListeningSession]:
    """Update session status."""
    result = await db.execute(
        select(ListeningSession).where(
            and_(
                ListeningSession.id == session_id,
                ListeningSession.user_id == user_id
            )
        )
    )
    session = result.scalar_one_or_none()
    
    if session:
        session.session_status = status
        await db.commit()
        await db.refresh(session)
    
    return session


async def advance_story(
    db: AsyncSession, session_id: UUID, user_id: UUID
) -> Optional[ListeningSession]:
    """Advance to next story in session."""
    result = await db.execute(
        select(ListeningSession).where(
            and_(
                ListeningSession.id == session_id,
                ListeningSession.user_id == user_id
            )
        )
    )
    session = result.scalar_one_or_none()
    
    if session and session.current_story_index < len(session.story_order) - 1:
        session.current_story_index += 1
        session.current_story_id = session.story_order[session.current_story_index]
        await db.commit()
        await db.refresh(session)
    
    return session


async def previous_story_func(
    db: AsyncSession, session_id: UUID, user_id: UUID
) -> Optional[ListeningSession]:
    """Go to previous story in session."""
    result = await db.execute(
        select(ListeningSession).where(
            and_(
                ListeningSession.id == session_id,
                ListeningSession.user_id == user_id
            )
        )
    )
    session = result.scalar_one_or_none()
    
    if session and session.current_story_index > 0:
        session.current_story_index -= 1
        session.current_story_id = session.story_order[session.current_story_index]
        await db.commit()
        await db.refresh(session)
    
    return session


async def get_session_metadata_func(
    db: AsyncSession, session_id: UUID, user_id: UUID
) -> Optional[dict]:
    """Get detailed session metadata."""
    result = await db.execute(
        select(ListeningSession).where(
            and_(
                ListeningSession.id == session_id,
                ListeningSession.user_id == user_id
            )
        )
    )
    session = result.scalar_one_or_none()
    
    if not session:
        return None
    
    # Get current story
    current_story = None
    if session.current_story_id:
        story_result = await db.execute(
            select(Story).where(Story.id == session.current_story_id)
        )
        current_story_obj = story_result.scalar_one_or_none()
        if current_story_obj:
            current_story = story_to_dict(current_story_obj)
    
    # Get remaining stories
    remaining_stories = []
    for i in range(session.current_story_index + 1, len(session.story_order)):
        story_id = session.story_order[i]
        story_result = await db.execute(
            select(Story).where(Story.id == story_id)
        )
        story_obj = story_result.scalar_one_or_none()
        if story_obj:
            remaining_stories.append(story_to_dict(story_obj))
    
    # Calculate progress
    progress = {
        "current": session.current_story_index + 1,
        "total": len(session.story_order),
        "percentage": (session.current_story_index + 1) / len(session.story_order) * 100
    }
    
    # Estimate time remaining (assume 2 minutes per story)
    stories_remaining = len(session.story_order) - session.current_story_index - 1
    estimated_time_remaining = stories_remaining * 2
    
    return {
        "current_story": current_story,
        "progress": progress,
        "remaining_stories": remaining_stories,
        "estimated_time_remaining": estimated_time_remaining
    }


def story_to_dict(story: Story) -> dict:
    """Convert Story to dictionary."""
    return {
        "id": str(story.id),
        "headline": story.headline,
        "one_sentence_summary": story.one_sentence_summary,
        "full_text_summary": story.full_text_summary,
        "url": story.url,
        "summary_audio_url": story.summary_audio_url,
        "full_text_audio_url": story.full_text_audio_url
    }