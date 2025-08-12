"""
Vocode conversation management for newsletter briefings.

Handles the setup and lifecycle of voice conversations during daily
newsletter briefings, including agent configuration and action coordination.
"""

import logging
from typing import Any

from vocode.streaming.action.abstract_factory import AbstractActionFactory
from vocode.streaming.models.actions import ActionConfig
from vocode.streaming.models.synthesizer import ElevenLabsSynthesizerConfig
from vocode.streaming.models.transcriber import DeepgramTranscriberConfig
from vocode.streaming.streaming_conversation import StreamingConversation

from backend.config import settings
from backend.voice.actions.conversational_query_action import ConversationalQueryAction
from backend.voice.actions.metadata_action import MetadataAction
from backend.voice.actions.skip_story_action import SkipStoryAction
from backend.voice.actions.tell_more_action import TellMeMoreAction
from backend.voice.agent_config import (
    create_briefing_agent_config,
)

logger = logging.getLogger(__name__)


class BriefingActionFactory(AbstractActionFactory):
    """
    Custom action factory for briefing actions.

    Creates instances of briefing-specific actions based on their configuration.
    """

    def create_action(self, action_config: ActionConfig):
        """
        Create action instances based on configuration.

        Args:
            action_config: Configuration for the action to create

        Returns:
            Action instance
        """
        if action_config.type == "action_skip_story":
            return SkipStoryAction()
        elif action_config.type == "action_tell_more":
            return TellMeMoreAction()
        elif action_config.type == "action_metadata":
            return MetadataAction()
        elif action_config.type == "action_conversational_query":
            return ConversationalQueryAction()
        else:
            logger.warning(f"Unknown action type: {action_config.type}")
            return None


class ConversationManager:
    """
    Manages Vocode streaming conversations for newsletter briefings.

    Handles conversation setup, configuration, and lifecycle management
    for voice-based newsletter delivery with real-time interruptions.
    """

    def __init__(self, session_id: str):
        """
        Initialize conversation manager for a specific session.

        Args:
            session_id: ID of the briefing session
        """
        self.session_id = session_id
        self.conversation: StreamingConversation | None = None
        self.action_factory = BriefingActionFactory()

        # Configure speech services
        self._setup_speech_configs()

    def _setup_speech_configs(self):
        """Setup speech-to-text and text-to-speech configurations."""

        # Configure ElevenLabs TTS with streaming optimization
        self.synthesizer_config = ElevenLabsSynthesizerConfig(
            api_key=settings.elevenlabs_api_key,
            voice_id=settings.default_voice_id,
            model_id=settings.default_voice_model,
            optimize_streaming_latency=settings.audio_streaming_latency,
            stability=0.5,  # Balance between consistency and expressiveness
            similarity_boost=0.75,  # Enhance voice similarity
            streaming_chunk_size=1024,  # Optimize for real-time streaming
        )

        # Configure Deepgram STT for voice recognition
        if settings.deepgram_api_key:
            self.transcriber_config = DeepgramTranscriberConfig(
                api_key=settings.deepgram_api_key,
                model="nova-2",  # Latest Deepgram model
                language="en",
                smart_format=True,  # Automatic punctuation and formatting
                interim_results=True,  # Enable real-time transcription
                endpointing=300,  # Milliseconds of silence before ending utterance
            )
        else:
            # Fallback to default transcriber if Deepgram key not available
            logger.warning("Deepgram API key not provided, using default transcriber")
            self.transcriber_config = None  # Will use Vocode's default

    async def create_conversation(self) -> StreamingConversation:
        """
        Create and configure a new streaming conversation.

        Returns:
            Configured StreamingConversation instance
        """

        # Get agent configuration with actions
        agent_config = create_briefing_agent_config(self.session_id)

        # Create conversation with all components
        conversation = StreamingConversation(
            agent_config=agent_config,
            transcriber_config=self.transcriber_config,
            synthesizer_config=self.synthesizer_config,
            action_factory=self.action_factory,
            conversation_id=f"briefing_{self.session_id}",
            # Additional conversation settings
            logger=logger,
        )

        self.conversation = conversation
        logger.info(f"Created streaming conversation for session {self.session_id}")
        return conversation

    async def start_conversation(self, websocket) -> None:
        """
        Start the streaming conversation with WebSocket integration.

        Args:
            websocket: WebSocket connection for audio streaming
        """
        if not self.conversation:
            await self.create_conversation()

        try:
            # Start the conversation with WebSocket
            await self.conversation.start(websocket)
            logger.info(f"Started conversation for session {self.session_id}")

        except Exception as e:
            logger.error(
                f"Error starting conversation for session {self.session_id}: {e}"
            )
            raise

    async def end_conversation(self) -> None:
        """End the current conversation gracefully."""
        if self.conversation:
            try:
                await self.conversation.terminate()
                logger.info(f"Ended conversation for session {self.session_id}")
            except Exception as e:
                logger.error(f"Error ending conversation: {e}")
            finally:
                self.conversation = None

    def get_conversation_status(self) -> dict[str, Any]:
        """
        Get current conversation status.

        Returns:
            Dictionary with conversation status information
        """
        return {
            "session_id": self.session_id,
            "conversation_active": self.conversation is not None,
            "conversation_id": f"briefing_{self.session_id}",
        }


class ConversationPool:
    """
    Pool manager for multiple concurrent conversations.

    Manages multiple briefing conversations and handles resource cleanup.
    """

    def __init__(self):
        """Initialize the conversation pool."""
        self._conversations: dict[str, ConversationManager] = {}

    async def get_conversation_manager(self, session_id: str) -> ConversationManager:
        """
        Get or create conversation manager for a session.

        Args:
            session_id: ID of the briefing session

        Returns:
            ConversationManager instance
        """
        if session_id not in self._conversations:
            self._conversations[session_id] = ConversationManager(session_id)
            logger.info(f"Created new conversation manager for session {session_id}")

        return self._conversations[session_id]

    async def remove_conversation(self, session_id: str) -> None:
        """
        Remove and cleanup conversation for a session.

        Args:
            session_id: ID of the session to cleanup
        """
        if session_id in self._conversations:
            manager = self._conversations[session_id]
            await manager.end_conversation()
            del self._conversations[session_id]
            logger.info(f"Removed conversation for session {session_id}")

    async def cleanup_all(self) -> None:
        """Cleanup all active conversations."""
        for session_id in list(self._conversations.keys()):
            await self.remove_conversation(session_id)
        logger.info("Cleaned up all conversations")

    def get_active_sessions(self) -> list[str]:
        """Get list of active session IDs."""
        return list(self._conversations.keys())


# Global conversation pool instance
conversation_pool = ConversationPool()
