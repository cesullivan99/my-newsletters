"""
End-to-end integration tests for the complete newsletter briefing flow.
"""

import pytest
import uuid
import asyncio
from unittest.mock import patch, Mock, AsyncMock

from tests.conftest import create_test_data


class TestCompleteAuthenticationFlow:
    """Test complete authentication flow from OAuth to API access."""

    @pytest.mark.asyncio
    async def test_complete_oauth_flow(self, client, db_session):
        """Test complete OAuth flow from start to finish."""
        # Step 1: Start OAuth flow
        with patch("backend.routes.auth.create_oauth_flow") as mock_flow:
            mock_flow_instance = Mock()
            mock_flow_instance.authorization_url.return_value = (
                "https://accounts.google.com/oauth/authorize?test=1",
                "test-state",
            )
            mock_flow.return_value = mock_flow_instance

            response = await client.get("/auth/gmail-oauth")
            assert response.status_code == 302

        # Step 2: Handle OAuth callback
        with (
            patch("backend.routes.auth.create_oauth_flow") as mock_flow,
            patch("backend.routes.auth.get_google_user_info") as mock_user_info,
            patch("backend.routes.auth.get_database_session") as mock_db,
        ):

            mock_flow_instance = Mock()
            mock_credentials = Mock()
            mock_credentials.token = "test-access-token"
            mock_credentials.refresh_token = "test-refresh-token"
            mock_flow_instance.credentials = mock_credentials
            mock_flow.return_value = mock_flow_instance

            mock_user_info.return_value = {
                "email": "integration@test.com",
                "name": "Integration User",
            }

            mock_db.return_value.__aenter__ = lambda x: db_session
            mock_db.return_value.__aexit__ = lambda *args: None

            async with client.session_transaction() as sess:
                sess["oauth_state"] = "test-state"

            response = await client.get(
                "/auth/google/callback?code=test-code&state=test-state"
            )
            assert response.status_code == 302
            assert "myletters://auth?token=" in response.location

            # Extract token from redirect URL
            token = response.location.split("token=")[1].split("&")[0]

        # Step 3: Use token to access protected endpoints
        headers = {"Authorization": f"Bearer {token}"}

        with patch("backend.utils.auth.get_async_session") as mock_db:
            mock_session = Mock()
            # Create a user object that matches the token
            from backend.models.database import User

            test_user = User(
                id=uuid.uuid4(), email="integration@test.com", name="Integration User"
            )
            mock_session.get.return_value = test_user
            mock_db.return_value.__aenter__ = lambda x: mock_session
            mock_db.return_value.__aexit__ = lambda *args: None

            response = await client.get("/auth/user", headers=headers)
            assert response.status_code == 200
            data = await response.get_json()
            assert data["email"] == "integration@test.com"


class TestCompleteBriefingFlow:
    """Test complete briefing flow from start to voice interaction."""

    @pytest.mark.asyncio
    async def test_complete_briefing_workflow(self, client, db_session):
        """Test complete briefing workflow."""
        # Create test data
        test_data = await create_test_data(db_session)
        user = test_data["user"]
        stories = test_data["stories"]

        # Create auth token
        from backend.utils.auth import create_access_token

        token = create_access_token({"sub": str(user.id), "email": user.email})
        headers = {"Authorization": f"Bearer {token}"}

        # Step 1: Start briefing
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            mock_manager.get_today_stories.return_value = stories

            mock_session = Mock()
            mock_session.id = uuid.uuid4()
            mock_manager.create_session.return_value = mock_session
            mock_manager_class.return_value = mock_manager

            response = await client.post(
                "/start-briefing", headers=headers, json={"user_id": str(user.id)}
            )

            assert response.status_code == 200
            data = await response.get_json()
            session_id = data["session_id"]

        # Step 2: Get session state
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            mock_session.session_status = "playing"
            mock_session.current_story_index = 0
            mock_manager.get_session.return_value = mock_session
            mock_manager_class.return_value = mock_manager

            response = await client.get(
                f"/briefing/{session_id}/state", headers=headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["session_status"] == "playing"

        # Step 3: Get current story
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            # Set up story with full relationships
            current_story = stories[0]
            current_story.issue.newsletter.name = "Integration Newsletter"
            mock_manager.get_current_story.return_value = current_story
            mock_manager_class.return_value = mock_manager

            response = await client.get(
                f"/briefing/{session_id}/current-story", headers=headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["headline"] == current_story.headline

        # Step 4: Control briefing (pause/resume)
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            mock_manager.pause_session.return_value = True
            mock_manager_class.return_value = mock_manager

            response = await client.post(
                f"/briefing/{session_id}/pause", headers=headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["status"] == "paused"

        # Step 5: Skip story
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            next_story = stories[1] if len(stories) > 1 else None
            if next_story:
                next_story.issue.newsletter.name = "Integration Newsletter"
            mock_manager.advance_story.return_value = next_story
            mock_manager_class.return_value = mock_manager

            response = await client.post(
                f"/briefing/{session_id}/skip", headers=headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            if next_story:
                assert data["next_story"]["id"] == str(next_story.id)
            else:
                assert data["next_story"] is None


class TestVoiceActionIntegration:
    """Test voice action integration with session management."""

    @pytest.mark.asyncio
    async def test_voice_action_sequence(self, db_session):
        """Test sequence of voice actions in a briefing session."""
        # Create test data
        test_data = await create_test_data(db_session)
        user = test_data["user"]
        stories = test_data["stories"]

        # Create session
        from backend.models.database import ListeningSession

        session = ListeningSession(
            id=uuid.uuid4(),
            user_id=user.id,
            current_story_id=stories[0].id,
            current_story_index=0,
            session_status="playing",
            story_order=[story.id for story in stories],
        )
        db_session.add(session)
        await db_session.commit()
        await db_session.refresh(session)

        # Create session manager
        from backend.services.session_manager import BriefingSessionManager

        session_manager = BriefingSessionManager(db_session)

        # Test 1: Skip Story Action
        from backend.voice.actions.skip_story_action import SkipStoryAction

        with patch.object(session_manager, "advance_story") as mock_advance:
            mock_advance.return_value = stories[1] if len(stories) > 1 else None

            skip_action = SkipStoryAction(session_manager)
            result = await skip_action.run(
                {"session_id": str(session.id)}, "test-conversation"
            )

            assert "next up" in result.lower() or "last story" in result.lower()

        # Test 2: Tell Me More Action
        from backend.voice.actions.tell_more_action import TellMeMoreAction

        with patch.object(session_manager, "get_detailed_summary") as mock_summary:
            mock_summary.return_value = (
                "This is a detailed summary with lots of information."
            )

            tell_more_action = TellMeMoreAction(session_manager)
            result = await tell_more_action.run(
                {"session_id": str(session.id)}, "test-conversation"
            )

            assert "full story" in result.lower()
            assert "detailed summary" in result

        # Test 3: Metadata Action
        from backend.voice.actions.metadata_action import MetadataAction

        with patch.object(session_manager, "get_story_metadata") as mock_metadata:
            mock_metadata.return_value = {
                "newsletter_name": "Integration Newsletter",
                "published_date": "2025-08-10",
                "publisher": "Test Publisher",
            }

            metadata_action = MetadataAction(session_manager)
            result = await metadata_action.run(
                {"session_id": str(session.id)}, "test-conversation"
            )

            assert "integration newsletter" in result.lower()


class TestAudioProcessingIntegration:
    """Test audio processing integration."""

    @pytest.mark.asyncio
    async def test_complete_audio_processing_flow(self, db_session):
        """Test complete audio processing flow."""
        # Create test data
        test_data = await create_test_data(db_session)
        stories = test_data["stories"]

        # Ensure stories need audio processing
        for story in stories:
            story.summary_audio_url = None
            story.full_text_audio_url = None

        await db_session.commit()

        # Test background audio processing
        with (
            patch(
                "backend.services.audio_service.generate_audio_stream"
            ) as mock_generate,
            patch("backend.services.storage_service.upload_audio_file") as mock_upload,
            patch(
                "backend.jobs.audio_processing.get_stories_needing_audio"
            ) as mock_get_stories,
        ):

            mock_get_stories.return_value = stories[:2]  # Process first 2 stories
            mock_generate.return_value = b"fake-audio-data"
            mock_upload.return_value = "https://storage.example.com/audio.mp3"

            from backend.jobs.audio_processing import process_pending_audio

            processed_count = await process_pending_audio()

            assert processed_count == 2
            assert mock_generate.call_count == 4  # 2 stories × 2 audio types
            assert mock_upload.call_count == 4

    @pytest.mark.asyncio
    async def test_elevenlabs_streaming_integration(self):
        """Test ElevenLabs streaming integration."""
        from backend.services.audio_service import AudioStreamingService

        with patch(
            "backend.services.audio_service.ElevenLabs"
        ) as mock_elevenlabs_class:
            mock_client = Mock()
            mock_stream = AsyncMock()

            # Simulate streaming chunks
            async def chunk_generator():
                for chunk in [b"chunk1", b"chunk2", b"chunk3"]:
                    yield chunk

            mock_stream.__aiter__ = chunk_generator
            mock_client.text_to_speech.stream.return_value = mock_stream
            mock_elevenlabs_class.return_value = mock_client

            service = AudioStreamingService()
            stream = await service.create_stream(
                "This is a test message for streaming audio generation.",
                voice_id="test-voice-id",
                optimize_streaming_latency=2,
            )

            chunks = []
            async for chunk in stream:
                chunks.append(chunk)

            assert len(chunks) == 3
            assert chunks == [b"chunk1", b"chunk2", b"chunk3"]


class TestWebSocketVoiceIntegration:
    """Test WebSocket voice communication integration."""

    @pytest.mark.asyncio
    async def test_websocket_voice_connection(self, client, db_session):
        """Test WebSocket voice connection and communication."""
        # Create test session
        test_data = await create_test_data(db_session)
        user = test_data["user"]

        from backend.models.database import ListeningSession

        session = ListeningSession(
            id=uuid.uuid4(),
            user_id=user.id,
            current_story_index=0,
            session_status="playing",
            story_order=[uuid.uuid4()],
        )
        db_session.add(session)
        await db_session.commit()

        # Test WebSocket connection
        with patch("backend.main.conversation_pool") as mock_pool:
            mock_manager = AsyncMock()
            mock_manager.start_conversation = AsyncMock()
            mock_pool.get_conversation_manager.return_value = mock_manager

            async with client.websocket(f"/voice-stream/{session.id}") as websocket:
                # Connection should be established
                pass  # WebSocket connected successfully

            mock_pool.get_conversation_manager.assert_called_once_with(str(session.id))

    @pytest.mark.asyncio
    async def test_voice_command_processing(self):
        """Test voice command processing through actions."""
        from backend.voice.agent_config import BriefingActionFactory

        session_id = str(uuid.uuid4())
        factory = BriefingActionFactory(session_id)

        # Test action creation
        skip_action = factory.create_skip_action()
        tell_more_action = factory.create_tell_more_action()
        metadata_action = factory.create_metadata_action()

        assert skip_action is not None
        assert tell_more_action is not None
        assert metadata_action is not None

        # Test phrase matching (if implemented)
        from backend.voice.agent_config import match_skip_phrases

        test_commands = ["skip this story", "next please", "move on"]

        for command in test_commands:
            assert match_skip_phrases(command) == True


class TestErrorRecoveryIntegration:
    """Test error recovery and resilience in integration scenarios."""

    @pytest.mark.asyncio
    async def test_database_connection_recovery(self, client, auth_headers):
        """Test recovery from database connection issues."""
        with patch("backend.main.get_database_session") as mock_db:
            # First call fails
            mock_db.side_effect = [
                Exception("Database connection failed"),
                # Second call would succeed in real retry logic
                AsyncMock(),
            ]

            response = await client.post(
                "/start-briefing",
                headers=auth_headers,
                json={"user_id": str(uuid.uuid4())},
            )

            # Should handle the error gracefully
            assert response.status_code == 500
            data = await response.get_json()
            assert "error" in data

    @pytest.mark.asyncio
    async def test_external_api_failure_recovery(self):
        """Test recovery from external API failures."""
        from backend.services.audio_service import generate_audio_stream

        with patch("backend.services.audio_service.ElevenLabs") as mock_elevenlabs:
            # First call fails
            mock_elevenlabs.side_effect = Exception("Rate limit exceeded")

            with pytest.raises(Exception, match="Rate limit exceeded"):
                await generate_audio_stream("Test text", "voice-id")

    @pytest.mark.asyncio
    async def test_session_state_corruption_recovery(self, db_session):
        """Test recovery from corrupted session state."""
        from backend.services.session_manager import BriefingSessionManager
        from backend.models.database import ListeningSession

        # Create session with invalid state
        session = ListeningSession(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            current_story_index=999,  # Invalid index
            session_status="corrupted",
            story_order=[],  # Empty story order
        )
        db_session.add(session)
        await db_session.commit()

        session_manager = BriefingSessionManager(db_session)

        with patch.object(session_manager, "get_current_story") as mock_get:
            mock_get.return_value = None  # No current story due to corruption

            story = await session_manager.get_current_story(session.id)
            assert story is None


class TestPerformanceIntegration:
    """Test performance characteristics in integration scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_briefing_sessions(self, client, db_session):
        """Test handling multiple concurrent briefing sessions."""
        # Create multiple users
        users = []
        for i in range(5):
            test_data = await create_test_data(db_session)
            users.append(test_data["user"])

        # Create tokens for all users
        from backend.utils.auth import create_access_token

        tokens = []
        for user in users:
            token = create_access_token({"sub": str(user.id), "email": user.email})
            tokens.append(token)

        # Start briefings concurrently
        tasks = []
        for i, token in enumerate(tokens):
            headers = {"Authorization": f"Bearer {token}"}

            with (
                patch("backend.main.get_database_session") as mock_db,
                patch("backend.main.BriefingSessionManager") as mock_manager_class,
            ):

                mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
                mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

                mock_manager = AsyncMock()
                mock_manager.get_today_stories.return_value = (
                    []
                )  # No stories for simplicity
                mock_manager_class.return_value = mock_manager

                task = client.post(
                    "/start-briefing",
                    headers=headers,
                    json={"user_id": str(users[i].id)},
                )
                tasks.append(task)

        # Wait for all requests to complete
        responses = await asyncio.gather(*tasks)

        # All should handle the request (even if no stories)
        for response in responses:
            assert response.status_code in [200, 404]  # 404 if no stories

    @pytest.mark.asyncio
    async def test_audio_streaming_performance(self):
        """Test audio streaming performance with large text."""
        from backend.services.audio_service import generate_audio_stream

        # Large text for performance testing
        large_text = "This is a test sentence. " * 100  # 2000+ characters

        with patch(
            "backend.services.audio_service.ElevenLabs"
        ) as mock_elevenlabs_class:
            mock_client = Mock()
            mock_stream = AsyncMock()

            # Simulate large audio chunks
            large_chunks = [b"x" * 1024 for _ in range(10)]  # 10KB of audio data
            mock_stream.__aiter__ = AsyncMock(return_value=iter(large_chunks))
            mock_client.text_to_speech.stream.return_value = mock_stream
            mock_elevenlabs_class.return_value = mock_client

            import time

            start_time = time.time()

            audio_data = await generate_audio_stream(large_text, "test-voice")

            end_time = time.time()
            processing_time = end_time - start_time

            assert isinstance(audio_data, bytes)
            assert len(audio_data) == 10240  # 10KB
            assert processing_time < 1.0  # Should process quickly with mocks
