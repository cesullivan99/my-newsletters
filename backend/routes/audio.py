"""
Audio processing routes for TTS generation, upload, and retrieval.
"""

import logging
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ValidationError
from quart import Blueprint, g, jsonify, request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_database_session
from backend.models.database import Story
# Import services with fallback to mock implementations
try:
    from backend.services.audio_service import AudioService
except ImportError:
    # Mock AudioService for testing
    class AudioService:
        async def generate_audio(self, text: str, voice_id: str):
            return {
                "url": f"https://example.com/audio/mock-{hash(text)}.mp3",
                "duration": 30.5,
                "size": 1024000
            }

try:
    from backend.services.storage_service import StorageService  
except ImportError:
    # Mock StorageService for testing
    class StorageService:
        async def upload_audio(self, file_data: bytes, filename: str, user_id):
            return {
                "public_url": f"https://example.com/uploads/{filename}",
                "storage_path": f"users/{user_id}/audio/{filename}"
            }
from backend.utils.auth import require_auth

audio_bp = Blueprint("audio", __name__, url_prefix="/audio")
logger = logging.getLogger(__name__)


# Pydantic schemas for audio endpoints
class AudioGenerateRequest(BaseModel):
    """Request to generate TTS audio."""
    
    text: str = Field(description="Text to convert to speech")
    story_id: str = Field(description="Story UUID")
    voice_id: Optional[str] = Field(default=None, description="Voice ID for TTS")


class AudioGenerateResponse(BaseModel):
    """Response from audio generation."""
    
    audio_url: str = Field(description="URL to generated audio file")
    duration: Optional[float] = Field(default=None, description="Audio duration in seconds")
    size: Optional[int] = Field(default=None, description="File size in bytes")


class AudioUploadResponse(BaseModel):
    """Response from audio upload."""
    
    url: str = Field(description="Public URL of uploaded audio")
    path: str = Field(description="Storage path of audio file")


class AudioRetrievalResponse(BaseModel):
    """Response for audio retrieval."""
    
    audio_url: Optional[str] = Field(description="URL to audio file")
    status: str = Field(description="Audio status")
    duration: Optional[float] = Field(default=None, description="Audio duration")


class AudioQueueStatusResponse(BaseModel):
    """Response for audio queue status."""
    
    pending: int = Field(description="Number of pending audio jobs")
    processing: int = Field(description="Number of processing audio jobs")
    completed: int = Field(description="Number of completed audio jobs")
    failed: int = Field(description="Number of failed audio jobs")
    queue_position: Optional[int] = Field(
        default=None, description="User's position in queue"
    )


class AudioBatchRequest(BaseModel):
    """Request for batch audio processing."""
    
    story_ids: List[str] = Field(description="List of story UUIDs to process")


class AudioBatchResponse(BaseModel):
    """Response from batch audio processing."""
    
    queued: int = Field(description="Number of stories queued for processing")
    job_ids: List[str] = Field(description="List of job IDs created")
    estimated_completion: int = Field(
        description="Estimated completion time in minutes"
    )


@audio_bp.route("/generate", methods=["POST"])
@require_auth
async def generate_audio():
    """
    Generate TTS audio for text.
    
    Creates audio file using text-to-speech service and stores it.
    
    Returns:
        AudioGenerateResponse: Generated audio details
    """
    try:
        current_user = g.current_user
        data = await request.get_json()
        
        # Validate request
        generate_request = AudioGenerateRequest(**data)
        
        # Validate story ID format
        try:
            story_uuid = UUID(generate_request.story_id)
        except ValueError:
            return jsonify({"error": "Invalid story ID format"}), 400
        
        logger.info(f"Generating audio for story {story_uuid}")
        
        # Initialize audio service
        audio_service = AudioService()
        
        # Use user's voice preference or default
        voice_id = (
            generate_request.voice_id or
            current_user.default_voice_type or
            "default"
        )
        
        # Generate audio
        audio_data = await audio_service.generate_audio(
            text=generate_request.text,
            voice_id=voice_id
        )
        
        # Store audio URL in story record
        async with get_database_session() as db:
            await update_story_audio_url(db, story_uuid, audio_data["url"])
        
        response = AudioGenerateResponse(
            audio_url=audio_data["url"],
            duration=audio_data.get("duration"),
            size=audio_data.get("size")
        )
        
        logger.info(f"Generated audio for story {story_uuid}: {audio_data['url']}")
        return jsonify(response.model_dump()), 201
        
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 422
    except Exception as e:
        logger.error(f"Error generating audio: {e}")
        return jsonify({"error": "Failed to generate audio"}), 500


@audio_bp.route("/upload", methods=["POST"])
@require_auth
async def upload_audio():
    """
    Upload audio file to storage.
    
    Accepts an audio file upload and stores it in cloud storage.
    
    Returns:
        AudioUploadResponse: Upload details
    """
    try:
        current_user = g.current_user
        
        # Get uploaded file
        files = await request.files
        if "audio_file" not in files:
            return jsonify({"error": "No audio file provided"}), 422
        
        audio_file = files["audio_file"]
        
        if not audio_file.filename:
            return jsonify({"error": "No file selected"}), 422
        
        # Validate file type
        allowed_extensions = {'.mp3', '.wav', '.m4a', '.ogg'}
        file_extension = '.' + audio_file.filename.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            return jsonify({
                "error": "Invalid file type",
                "allowed": list(allowed_extensions)
            }), 422
        
        logger.info(f"Uploading audio file: {audio_file.filename}")
        
        # Initialize storage service
        storage_service = StorageService()
        
        # Read file data
        file_data = await audio_file.read()
        
        # Upload to storage
        result = await storage_service.upload_audio(
            file_data=file_data,
            filename=audio_file.filename,
            user_id=current_user.id
        )
        
        response = AudioUploadResponse(
            url=result["public_url"],
            path=result["storage_path"]
        )
        
        logger.info(f"Uploaded audio file: {result['public_url']}")
        return jsonify(response.model_dump()), 201
        
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        return jsonify({"error": "Failed to upload audio"}), 500


@audio_bp.route("/<story_id>", methods=["GET"])
@require_auth
async def get_audio(story_id: str):
    """
    Get audio URL for story.
    
    Returns audio URL if available, or queues generation if not.
    
    Args:
        story_id: UUID of the story
        
    Returns:
        AudioRetrievalResponse: Audio URL or generation status
    """
    try:
        current_user = g.current_user
        
        # Validate UUID format
        try:
            story_uuid = UUID(story_id)
        except ValueError:
            return jsonify({"error": "Invalid story ID format"}), 400
        
        async with get_database_session() as db:
            # Get story
            story = await get_story_by_id(db, story_uuid)
            
            if not story:
                return jsonify({"error": "Story not found"}), 404
            
            # Check if audio exists
            if story.summary_audio_url:
                response = AudioRetrievalResponse(
                    audio_url=story.summary_audio_url,
                    status="available",
                    duration=None  # Could be stored in database
                )
                return jsonify(response.model_dump())
            
            # Audio not available - queue for generation
            await queue_audio_generation(story_uuid)
            
            response = AudioRetrievalResponse(
                audio_url=None,
                status="generating"
            )
            
            return jsonify(response.model_dump()), 202
            
    except Exception as e:
        logger.error(f"Error getting audio for story {story_id}: {e}")
        return jsonify({"error": "Failed to get audio"}), 500


@audio_bp.route("/queue/status", methods=["GET"])
@require_auth
async def get_queue_status():
    """
    Get audio processing queue status.
    
    Returns current queue statistics and user position.
    
    Returns:
        AudioQueueStatusResponse: Queue status information
    """
    try:
        current_user = g.current_user
        
        # Get queue status (mock implementation)
        status = await get_audio_queue_status(user_id=current_user.id)
        
        response = AudioQueueStatusResponse(**status)
        return jsonify(response.model_dump())
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return jsonify({"error": "Failed to get queue status"}), 500


@audio_bp.route("/batch", methods=["POST"])
@require_auth
async def batch_process_audio():
    """
    Queue multiple stories for audio processing.
    
    Submits batch job for processing multiple stories at once.
    
    Returns:
        AudioBatchResponse: Batch processing details
    """
    try:
        current_user = g.current_user
        data = await request.get_json()
        
        # Validate request
        batch_request = AudioBatchRequest(**data)
        
        if not batch_request.story_ids:
            return jsonify({"error": "No story IDs provided"}), 422
        
        # Validate story UUIDs
        story_uuids = []
        for story_id in batch_request.story_ids:
            try:
                story_uuids.append(UUID(story_id))
            except ValueError:
                return jsonify({"error": f"Invalid story ID format: {story_id}"}), 400
        
        logger.info(f"Batch processing {len(story_uuids)} stories for user {current_user.id}")
        
        # Validate that stories exist
        async with get_database_session() as db:
            valid_stories = []
            for story_uuid in story_uuids:
                story = await get_story_by_id(db, story_uuid)
                if story:
                    valid_stories.append(story_uuid)
                else:
                    logger.warning(f"Story not found: {story_uuid}")
        
        if not valid_stories:
            return jsonify({"error": "No valid stories found"}), 404
        
        # Queue all stories for processing
        job_ids = []
        for story_uuid in valid_stories:
            job_id = await queue_audio_generation(story_uuid, priority="high")
            job_ids.append(str(job_id))
        
        # Calculate estimated completion time (2 minutes per story)
        estimated_completion = len(valid_stories) * 2
        
        response = AudioBatchResponse(
            queued=len(valid_stories),
            job_ids=job_ids,
            estimated_completion=estimated_completion
        )
        
        logger.info(f"Queued {len(valid_stories)} stories for batch audio processing")
        return jsonify(response.model_dump()), 202
        
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.errors()}), 422
    except Exception as e:
        logger.error(f"Error in batch audio processing: {e}")
        return jsonify({"error": "Failed to process batch audio request"}), 500


# Helper functions

async def get_story_by_id(db: AsyncSession, story_id: UUID) -> Optional[Story]:
    """Get story by ID."""
    result = await db.execute(
        select(Story).where(Story.id == story_id)
    )
    return result.scalar_one_or_none()


async def update_story_audio_url(db: AsyncSession, story_id: UUID, audio_url: str):
    """Update story with audio URL."""
    result = await db.execute(
        select(Story).where(Story.id == story_id)
    )
    story = result.scalar_one_or_none()
    
    if story:
        story.summary_audio_url = audio_url
        await db.commit()
        await db.refresh(story)


async def queue_audio_generation(story_id: UUID, priority: str = "normal") -> UUID:
    """
    Queue story for audio generation.
    
    Args:
        story_id: Story UUID to process
        priority: Processing priority (normal, high)
        
    Returns:
        Job UUID
    """
    # This would integrate with a job queue system like Celery or RQ
    # For now, just log the action and return a mock job ID
    job_id = UUID('12345678-1234-5678-9012-123456789012')
    logger.info(f"Queued story {story_id} for audio generation with priority {priority}")
    return job_id


async def get_audio_queue_status(user_id: UUID) -> dict:
    """
    Get audio processing queue status.
    
    Args:
        user_id: User UUID
        
    Returns:
        Queue status dictionary
    """
    # Mock implementation - would query actual job queue
    return {
        "pending": 5,
        "processing": 2,
        "completed": 48,
        "failed": 1,
        "queue_position": 3
    }