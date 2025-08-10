"""
Pydantic models for API request/response validation.

Defines the data structures for API endpoints with proper validation
and serialization for the newsletter briefing system.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class BriefingRequest(BaseModel):
    """Request to start a daily briefing session."""
    
    user_id: UUID = Field(description="ID of the user requesting the briefing")
    voice_type: Optional[str] = Field(default=None, description="Preferred voice type for TTS")
    playback_speed: Optional[float] = Field(default=1.0, description="Playback speed (0.5-2.0)")


class BriefingResponse(BaseModel):
    """Response when starting a briefing session."""
    
    session_id: UUID = Field(description="ID of the created briefing session")
    first_story_id: UUID = Field(description="ID of the first story in the briefing")
    total_stories: int = Field(description="Total number of stories in the briefing")
    websocket_url: str = Field(description="WebSocket URL for voice interaction")


class SessionProgressResponse(BaseModel):
    """Current progress of a briefing session."""
    
    session_id: UUID = Field(description="ID of the briefing session")
    current_story_index: int = Field(description="Index of current story (0-based)")
    total_stories: int = Field(description="Total number of stories")
    progress_percentage: float = Field(description="Completion percentage (0-100)")
    session_status: str = Field(description="Status: 'playing', 'paused', or 'completed'")
    stories_remaining: int = Field(description="Number of stories remaining")


class StoryResponse(BaseModel):
    """Response containing story information."""
    
    id: UUID = Field(description="Story ID")
    headline: str = Field(description="Story headline")
    one_sentence_summary: str = Field(description="Brief story summary")
    full_text_summary: str = Field(description="Detailed story summary")
    newsletter_name: str = Field(description="Name of source newsletter")
    publisher: str = Field(description="Newsletter publisher")
    issue_date: Optional[datetime] = Field(description="Publication date")
    summary_audio_url: Optional[str] = Field(description="URL to summary audio file")
    full_text_audio_url: Optional[str] = Field(description="URL to detailed audio file")


class SessionControlRequest(BaseModel):
    """Request to control session playback."""
    
    action: str = Field(description="Control action: 'pause', 'resume', 'skip', 'restart'")


class VoiceActionInput(BaseModel):
    """Input for voice actions during conversations."""
    
    session_id: UUID = Field(description="ID of the active briefing session")
    action_type: str = Field(description="Type of action: 'skip', 'tell_more', 'metadata'")
    user_query: Optional[str] = Field(default=None, description="Optional user query text")


class ActionResult(BaseModel):
    """Result from executing a voice action."""
    
    action: str = Field(description="Action that was executed")
    message: str = Field(description="Response message for the user")
    next_story_id: Optional[UUID] = Field(default=None, description="ID of next story if advanced")
    session_completed: bool = Field(default=False, description="True if session is now complete")


class SessionStateUpdate(BaseModel):
    """Update to session state."""
    
    session_id: UUID = Field(description="ID of the session")
    current_story_id: UUID = Field(description="ID of the current story")
    current_story_index: int = Field(description="Current story index")
    session_status: str = Field(description="Updated session status")


class UserPreferences(BaseModel):
    """User preferences for briefing experience."""
    
    default_voice_type: str = Field(default="default", description="Preferred voice type")
    default_playback_speed: float = Field(default=1.0, description="Preferred playback speed")
    summarization_depth: str = Field(default="high-level", description="Preferred detail level")


class ErrorResponse(BaseModel):
    """Standard error response format."""
    
    error: str = Field(description="Error type or code")
    message: str = Field(description="Human-readable error message")
    details: Optional[dict] = Field(default=None, description="Additional error details")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(description="Service status")
    timestamp: datetime = Field(description="Check timestamp")
    version: str = Field(description="API version")
    services: dict = Field(description="Status of dependent services")


class WebSocketMessage(BaseModel):
    """Base structure for WebSocket messages."""
    
    type: str = Field(description="Message type")
    session_id: UUID = Field(description="Session ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict = Field(description="Message payload")


class AudioStreamMessage(WebSocketMessage):
    """WebSocket message for audio streaming."""
    
    type: str = Field(default="audio_stream", description="Message type")
    audio_data: Optional[bytes] = Field(default=None, description="Audio data chunk")
    is_final: bool = Field(default=False, description="True if this is the last chunk")


class TranscriptionMessage(WebSocketMessage):
    """WebSocket message for transcription results."""
    
    type: str = Field(default="transcription", description="Message type")
    text: str = Field(description="Transcribed text")
    confidence: Optional[float] = Field(default=None, description="Transcription confidence")
    is_final: bool = Field(default=False, description="True if transcription is final")


class VoiceCommandMessage(WebSocketMessage):
    """WebSocket message for voice commands."""
    
    type: str = Field(default="voice_command", description="Message type")
    command: str = Field(description="Recognized voice command")
    intent: Optional[str] = Field(default=None, description="Detected intent")
    confidence: Optional[float] = Field(default=None, description="Recognition confidence")


class SystemMessage(WebSocketMessage):
    """WebSocket message for system notifications."""
    
    type: str = Field(default="system", description="Message type")
    level: str = Field(description="Message level: 'info', 'warning', 'error'")
    message: str = Field(description="System message content")