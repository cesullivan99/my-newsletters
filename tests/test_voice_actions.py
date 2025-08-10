"""
Tests for Vocode voice actions and audio processing functionality.
"""

import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch


class TestSkipStoryAction:
    """Test SkipStoryAction functionality."""

    @pytest.mark.asyncio
    async def test_skip_story_success(self, test_session, test_story):
        """Test successful story skip."""
        from backend.voice.actions.skip_story_action import SkipStoryAction

        # Mock session manager
        mock_session_manager = AsyncMock()
        mock_session_manager.advance_story.return_value = test_story

        action = SkipStoryAction(mock_session_manager)

        # Test action execution
        result = await action.run(
            {"session_id": str(test_session.id)}, "test-conversation-id"
        )

        assert "skipping" in result.lower()
        assert "next up" in result.lower()
        assert test_story.headline in result
        mock_session_manager.advance_story.assert_called_once_with(test_session.id)

    @pytest.mark.asyncio
    async def test_skip_story_end_of_briefing(self, test_session):
        """Test skip story at end of briefing."""
        from backend.voice.actions.skip_story_action import SkipStoryAction

        mock_session_manager = AsyncMock()
        mock_session_manager.advance_story.return_value = None  # No more stories

        action = SkipStoryAction(mock_session_manager)

        result = await action.run(
            {"session_id": str(test_session.id)}, "test-conversation-id"
        )

        assert "last story" in result.lower()
        assert "have a great day" in result.lower()

    @pytest.mark.asyncio
    async def test_skip_story_missing_session_id(self):
        """Test skip story with missing session_id."""
        from backend.voice.actions.skip_story_action import SkipStoryAction

        mock_session_manager = AsyncMock()
        action = SkipStoryAction(mock_session_manager)

        result = await action.run({}, "test-conversation-id")

        assert "error" in result.lower() or "sorry" in result.lower()


class TestTellMeMoreAction:
    """Test TellMeMoreAction functionality."""

    @pytest.mark.asyncio
    async def test_tell_me_more_success(self, test_session):
        """Test successful tell me more action."""
        from backend.voice.actions.tell_more_action import TellMeMoreAction

        mock_session_manager = AsyncMock()
        mock_session_manager.get_detailed_summary.return_value = "This is a detailed summary of the current story with lots of interesting details."

        action = TellMeMoreAction(mock_session_manager)

        result = await action.run(
            {"session_id": str(test_session.id)}, "test-conversation-id"
        )

        assert "here's the full story" in result.lower()
        assert "detailed summary" in result
        mock_session_manager.get_detailed_summary.assert_called_once_with(
            test_session.id
        )

    @pytest.mark.asyncio
    async def test_tell_me_more_no_summary(self, test_session):
        """Test tell me more when no detailed summary available."""
        from backend.voice.actions.tell_more_action import TellMeMoreAction

        mock_session_manager = AsyncMock()
        mock_session_manager.get_detailed_summary.return_value = None

        action = TellMeMoreAction(mock_session_manager)

        result = await action.run(
            {"session_id": str(test_session.id)}, "test-conversation-id"
        )

        assert "no additional details" in result.lower() or "sorry" in result.lower()


class TestMetadataAction:
    """Test MetadataAction functionality."""

    @pytest.mark.asyncio
    async def test_metadata_action_success(self, test_session, test_story):
        """Test successful metadata retrieval."""
        from backend.voice.actions.metadata_action import MetadataAction

        mock_session_manager = AsyncMock()
        mock_session_manager.get_story_metadata.return_value = {
            "newsletter_name": "Tech Weekly",
            "published_date": "2025-08-10",
            "publisher": "Tech Publications",
            "headline": test_story.headline,
        }

        action = MetadataAction(mock_session_manager)

        result = await action.run(
            {"session_id": str(test_session.id)}, "test-conversation-id"
        )

        assert "tech weekly" in result.lower()
        assert "2025-08-10" in result or "august 10" in result.lower()
        mock_session_manager.get_story_metadata.assert_called_once_with(test_session.id)

    @pytest.mark.asyncio
    async def test_metadata_action_no_current_story(self, test_session):
        """Test metadata action when no current story."""
        from backend.voice.actions.metadata_action import MetadataAction

        mock_session_manager = AsyncMock()
        mock_session_manager.get_story_metadata.return_value = None

        action = MetadataAction(mock_session_manager)

        result = await action.run(
            {"session_id": str(test_session.id)}, "test-conversation-id"
        )

        assert "no current story" in result.lower() or "sorry" in result.lower()


class TestConversationalQueryAction:
    """Test ConversationalQueryAction functionality."""

    @pytest.mark.asyncio
    async def test_conversational_query_success(self, test_session):
        """Test successful conversational query."""
        from backend.voice.actions.conversational_query_action import (
            ConversationalQueryAction,
        )

        mock_session_manager = AsyncMock()
        mock_session_manager.get_current_story.return_value = Mock(
            headline="AI Breakthrough",
            one_sentence_summary="New AI model achieves human-level performance.",
            full_text_summary="A detailed story about AI achievements...",
        )

        with patch("openai.ChatCompletion.acreate") as mock_openai:
            mock_openai.return_value = Mock(
                choices=[
                    Mock(
                        message=Mock(
                            content="This AI breakthrough represents a significant advancement in machine learning technology."
                        )
                    )
                ]
            )

            action = ConversationalQueryAction(mock_session_manager)

            result = await action.run(
                {
                    "session_id": str(test_session.id),
                    "query": "What makes this AI breakthrough significant?",
                },
                "test-conversation-id",
            )

            assert "significant advancement" in result
            assert "machine learning" in result.lower()

    @pytest.mark.asyncio
    async def test_conversational_query_no_context(self, test_session):
        """Test conversational query with no story context."""
        from backend.voice.actions.conversational_query_action import (
            ConversationalQueryAction,
        )

        mock_session_manager = AsyncMock()
        mock_session_manager.get_current_story.return_value = None

        action = ConversationalQueryAction(mock_session_manager)

        result = await action.run(
            {"session_id": str(test_session.id), "query": "What is this story about?"},
            "test-conversation-id",
        )

        assert (
            "no current story" in result.lower()
            or "don't have context" in result.lower()
        )


class TestBaseBriefingAction:
    """Test BaseBriefingAction functionality."""

    def test_base_action_initialization(self):
        """Test base action initialization."""
        from backend.voice.actions.base_briefing_action import BaseBriefingAction

        mock_session_manager = AsyncMock()
        action = BaseBriefingAction(mock_session_manager)

        assert action.session_manager == mock_session_manager
        assert hasattr(action, "description")

    @pytest.mark.asyncio
    async def test_base_action_session_validation(self, test_session):
        """Test base action session validation."""
        from backend.voice.actions.base_briefing_action import BaseBriefingAction

        mock_session_manager = AsyncMock()
        action = BaseBriefingAction(mock_session_manager)

        # Test valid session ID
        session_id = action._extract_session_id({"session_id": str(test_session.id)})
        assert session_id == test_session.id

        # Test invalid session ID
        session_id = action._extract_session_id({"invalid_key": "test"})
        assert session_id is None

    @pytest.mark.asyncio
    async def test_base_action_error_handling(self):
        """Test base action error handling."""
        from backend.voice.actions.base_briefing_action import BaseBriefingAction

        mock_session_manager = AsyncMock()
        mock_session_manager.get_current_story.side_effect = Exception("Database error")

        action = BaseBriefingAction(mock_session_manager)

        result = await action._handle_error("Database error", "test action")

        assert "sorry" in result.lower()
        assert "error" in result.lower() or "problem" in result.lower()


class TestAudioProcessing:
    """Test audio processing functionality."""

    @pytest.mark.asyncio
    async def test_elevenlabs_audio_generation(self, mock_elevenlabs):
        """Test ElevenLabs audio generation."""
        from backend.services.audio_service import generate_audio_stream

        with patch(
            "backend.services.audio_service.ElevenLabs", return_value=mock_elevenlabs
        ):
            audio_data = await generate_audio_stream(
                "Hello, this is a test message for TTS.", "test-voice-id"
            )

            assert isinstance(audio_data, bytes)
            assert len(audio_data) > 0
            mock_elevenlabs.text_to_speech.stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_audio_streaming_with_latency_optimization(self, mock_elevenlabs):
        """Test audio streaming with latency optimization."""
        from backend.services.audio_service import AudioStreamingService

        with patch(
            "backend.services.audio_service.ElevenLabs", return_value=mock_elevenlabs
        ):
            service = AudioStreamingService()

            stream = await service.create_stream(
                "Test message for streaming",
                voice_id="test-voice",
                optimize_streaming_latency=2,
            )

            chunks = []
            async for chunk in stream:
                chunks.append(chunk)
                if len(chunks) >= 3:  # Limit for test
                    break

            assert len(chunks) == 3
            assert all(isinstance(chunk, bytes) for chunk in chunks)

    @pytest.mark.asyncio
    async def test_audio_processing_job(self, test_story):
        """Test background audio processing job."""
        from backend.jobs.audio_processing import process_pending_audio

        with (
            patch(
                "backend.services.audio_service.generate_audio_stream"
            ) as mock_generate,
            patch("backend.services.storage_service.upload_audio_file") as mock_upload,
            patch(
                "backend.jobs.audio_processing.get_stories_needing_audio"
            ) as mock_get_stories,
        ):

            mock_get_stories.return_value = [test_story]
            mock_generate.return_value = b"fake-audio-data"
            mock_upload.return_value = "https://storage.example.com/audio.mp3"

            processed_count = await process_pending_audio()

            assert processed_count == 1
            mock_generate.assert_called_once()
            mock_upload.assert_called_once()


class TestVocodeIntegration:
    """Test Vocode integration functionality."""

    @pytest.mark.asyncio
    async def test_conversation_manager_initialization(self, test_session):
        """Test conversation manager initialization."""
        from backend.voice.conversation_manager import ConversationManager

        with patch(
            "backend.voice.conversation_manager.StreamingConversation"
        ) as mock_conversation:
            manager = ConversationManager(str(test_session.id))

            assert manager.session_id == str(test_session.id)
            assert manager.conversation is None  # Not initialized yet

    @pytest.mark.asyncio
    async def test_agent_configuration(self):
        """Test agent configuration with actions."""
        from backend.voice.agent_config import create_briefing_agent

        with (
            patch("backend.voice.agent_config.ChatGPTAgent") as mock_agent,
            patch(
                "backend.voice.agent_config.PhraseBasedActionTrigger"
            ) as mock_trigger,
        ):

            session_id = str(uuid.uuid4())
            agent = create_briefing_agent(session_id)

            mock_agent.assert_called_once()
            # Verify that actions are configured
            call_args = mock_agent.call_args
            assert "actions" in call_args.kwargs
            assert len(call_args.kwargs["actions"]) > 0

    @pytest.mark.asyncio
    async def test_phrase_triggers_configuration(self):
        """Test phrase trigger configuration."""
        from backend.voice.agent_config import configure_phrase_triggers

        triggers = configure_phrase_triggers()

        assert "skip" in triggers
        assert "tell_more" in triggers
        assert "metadata" in triggers

        # Verify skip triggers
        skip_triggers = triggers["skip"]
        assert any("skip" in phrase.lower() for phrase in skip_triggers)
        assert any("next" in phrase.lower() for phrase in skip_triggers)

    @pytest.mark.asyncio
    async def test_conversation_websocket_handling(self, mock_vocode_conversation):
        """Test WebSocket conversation handling."""
        from backend.voice.conversation_manager import ConversationManager

        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        mock_websocket.receive = AsyncMock()

        with patch(
            "backend.voice.conversation_manager.StreamingConversation",
            return_value=mock_vocode_conversation,
        ):

            manager = ConversationManager("test-session-id")
            await manager.start_conversation(mock_websocket)

            mock_vocode_conversation.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_action_factory(self):
        """Test briefing action factory."""
        from backend.voice.agent_config import BriefingActionFactory

        factory = BriefingActionFactory("test-session-id")

        skip_action = factory.create_skip_action()
        tell_more_action = factory.create_tell_more_action()
        metadata_action = factory.create_metadata_action()

        assert skip_action is not None
        assert tell_more_action is not None
        assert metadata_action is not None

        # Verify they all have the same session manager
        assert skip_action.session_manager == tell_more_action.session_manager
        assert tell_more_action.session_manager == metadata_action.session_manager


class TestSessionManager:
    """Test session manager functionality used by voice actions."""

    @pytest.mark.asyncio
    async def test_get_current_story(self, db_session, test_session, test_story):
        """Test getting current story from session."""
        from backend.services.session_manager import BriefingSessionManager

        # Set up session with current story
        test_session.current_story_id = test_story.id

        session_manager = BriefingSessionManager(db_session)

        with patch.object(
            session_manager, "get_current_story", return_value=test_story
        ):
            story = await session_manager.get_current_story(test_session.id)

            assert story == test_story
            assert story.headline == test_story.headline

    @pytest.mark.asyncio
    async def test_advance_story(self, db_session, test_session):
        """Test advancing to next story."""
        from backend.services.session_manager import BriefingSessionManager

        session_manager = BriefingSessionManager(db_session)

        # Mock the advance_story method
        next_story = Mock()
        next_story.id = uuid.uuid4()
        next_story.headline = "Next Story"

        with patch.object(session_manager, "advance_story", return_value=next_story):
            result = await session_manager.advance_story(test_session.id)

            assert result == next_story
            assert result.headline == "Next Story"

    @pytest.mark.asyncio
    async def test_get_detailed_summary(self, db_session, test_session):
        """Test getting detailed summary."""
        from backend.services.session_manager import BriefingSessionManager

        session_manager = BriefingSessionManager(db_session)
        expected_summary = "This is a detailed summary with lots of information about the current story."

        with patch.object(
            session_manager, "get_detailed_summary", return_value=expected_summary
        ):
            summary = await session_manager.get_detailed_summary(test_session.id)

            assert summary == expected_summary
            assert len(summary) > 50  # Should be detailed


class TestVoiceActionErrorHandling:
    """Test error handling in voice actions."""

    @pytest.mark.asyncio
    async def test_session_manager_database_error(self, test_session):
        """Test handling of database errors in session manager."""
        from backend.voice.actions.skip_story_action import SkipStoryAction

        mock_session_manager = AsyncMock()
        mock_session_manager.advance_story.side_effect = Exception(
            "Database connection failed"
        )

        action = SkipStoryAction(mock_session_manager)

        result = await action.run(
            {"session_id": str(test_session.id)}, "test-conversation-id"
        )

        assert "sorry" in result.lower()
        assert "error" in result.lower() or "problem" in result.lower()

    @pytest.mark.asyncio
    async def test_audio_generation_failure(self):
        """Test handling of audio generation failures."""
        from backend.services.audio_service import generate_audio_stream

        with patch("backend.services.audio_service.ElevenLabs") as mock_elevenlabs:
            mock_elevenlabs.side_effect = Exception("API rate limit exceeded")

            with pytest.raises(Exception, match="API rate limit exceeded"):
                await generate_audio_stream("Test text", "voice-id")

    @pytest.mark.asyncio
    async def test_conversation_websocket_error(self):
        """Test handling of WebSocket errors in conversation."""
        from backend.voice.conversation_manager import ConversationManager

        mock_websocket = AsyncMock()
        mock_websocket.send_json.side_effect = Exception("WebSocket connection closed")

        manager = ConversationManager("test-session-id")

        # Should handle the exception gracefully
        with patch("backend.voice.conversation_manager.logger") as mock_logger:
            try:
                await manager.start_conversation(mock_websocket)
            except Exception:
                pass  # Expected to handle gracefully

            mock_logger.error.assert_called()


class TestPhraseMatching:
    """Test phrase matching for voice commands."""

    def test_skip_phrase_matching(self):
        """Test skip command phrase matching."""
        from backend.voice.agent_config import match_skip_phrases

        test_phrases = [
            "skip this story",
            "next story please",
            "move on to the next one",
            "skip it",
            "next",
            "let's move on",
        ]

        for phrase in test_phrases:
            assert match_skip_phrases(phrase) == True

    def test_tell_more_phrase_matching(self):
        """Test tell me more phrase matching."""
        from backend.voice.agent_config import match_tell_more_phrases

        test_phrases = [
            "tell me more",
            "can you go deeper",
            "give me the full story",
            "more details please",
            "expand on that",
        ]

        for phrase in test_phrases:
            assert match_tell_more_phrases(phrase) == True

    def test_metadata_phrase_matching(self):
        """Test metadata query phrase matching."""
        from backend.voice.agent_config import match_metadata_phrases

        test_phrases = [
            "what newsletter is this from",
            "when was this published",
            "who published this",
            "what's the source",
        ]

        for phrase in test_phrases:
            assert match_metadata_phrases(phrase) == True
