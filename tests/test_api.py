"""
Tests for API endpoints and briefing functionality.
"""

import pytest
import uuid
from unittest.mock import patch, Mock, AsyncMock

from backend.models.schemas import BriefingRequest


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint returns correct status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = await response.get_json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data
        assert data["version"] == "1.0.0"


class TestBriefingEndpoints:
    """Test briefing-related API endpoints."""

    @pytest.mark.asyncio
    async def test_start_briefing_success(
        self, client, test_user, auth_headers, test_story
    ):
        """Test successful briefing start."""
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            # Setup database mock
            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            # Setup session manager mock
            mock_manager = AsyncMock()
            mock_manager.get_today_stories.return_value = [test_story]

            mock_session = Mock()
            mock_session.id = uuid.uuid4()
            mock_manager.create_session.return_value = mock_session

            mock_manager_class.return_value = mock_manager

            request_data = {"user_id": str(test_user.id)}
            response = await client.post(
                "/start-briefing", headers=auth_headers, json=request_data
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert "session_id" in data
            assert "first_story_id" in data
            assert "total_stories" in data
            assert "websocket_url" in data
            assert data["total_stories"] == 1

    @pytest.mark.asyncio
    async def test_start_briefing_no_stories(self, client, test_user, auth_headers):
        """Test briefing start when no stories available."""
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            mock_manager.get_today_stories.return_value = []
            mock_manager_class.return_value = mock_manager

            request_data = {"user_id": str(test_user.id)}
            response = await client.post(
                "/start-briefing", headers=auth_headers, json=request_data
            )

            assert response.status_code == 404
            data = await response.get_json()
            assert data["error"] == "no_stories"

    @pytest.mark.asyncio
    async def test_start_briefing_unauthenticated(self, client):
        """Test briefing start without authentication."""
        request_data = {"user_id": "test-user-id"}
        response = await client.post("/start-briefing", json=request_data)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_briefing_state(self, client, auth_headers, test_session):
        """Test getting briefing session state."""
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            mock_manager.get_session.return_value = test_session
            mock_manager_class.return_value = mock_manager

            response = await client.get(
                f"/briefing/{test_session.id}/state", headers=auth_headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["session_id"] == str(test_session.id)
            assert data["session_status"] == test_session.session_status
            assert data["current_story_index"] == test_session.current_story_index

    @pytest.mark.asyncio
    async def test_get_current_story(
        self, client, auth_headers, test_session, test_story
    ):
        """Test getting current story in session."""
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            # Setup story with relationships
            test_story.issue.newsletter.name = "Test Newsletter"
            test_story.issue.date = test_story.issue.date

            mock_manager = AsyncMock()
            mock_manager.get_current_story.return_value = test_story
            mock_manager_class.return_value = mock_manager

            response = await client.get(
                f"/briefing/{test_session.id}/current-story", headers=auth_headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["id"] == str(test_story.id)
            assert data["headline"] == test_story.headline
            assert data["one_sentence_summary"] == test_story.one_sentence_summary

    @pytest.mark.asyncio
    async def test_pause_briefing(self, client, auth_headers, test_session):
        """Test pausing briefing session."""
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
                f"/briefing/{test_session.id}/pause", headers=auth_headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["status"] == "paused"

    @pytest.mark.asyncio
    async def test_resume_briefing(self, client, auth_headers, test_session):
        """Test resuming briefing session."""
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            mock_manager.resume_session.return_value = True
            mock_manager_class.return_value = mock_manager

            response = await client.post(
                f"/briefing/{test_session.id}/resume", headers=auth_headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["status"] == "playing"

    @pytest.mark.asyncio
    async def test_skip_story(self, client, auth_headers, test_session, test_story):
        """Test skipping to next story."""
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            # Setup story with relationships
            test_story.issue.newsletter.name = "Test Newsletter"
            test_story.issue.date = test_story.issue.date

            mock_manager = AsyncMock()
            mock_manager.advance_story.return_value = test_story
            mock_manager_class.return_value = mock_manager

            response = await client.post(
                f"/briefing/{test_session.id}/skip", headers=auth_headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert "next_story" in data
            assert data["next_story"]["id"] == str(test_story.id)

    @pytest.mark.asyncio
    async def test_skip_story_end_of_briefing(self, client, auth_headers, test_session):
        """Test skipping story at end of briefing."""
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            mock_manager.advance_story.return_value = None  # No more stories
            mock_manager_class.return_value = mock_manager

            response = await client.post(
                f"/briefing/{test_session.id}/skip", headers=auth_headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["next_story"] is None

    @pytest.mark.asyncio
    async def test_get_detailed_summary(self, client, auth_headers, test_session):
        """Test getting detailed summary."""
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            mock_manager.get_detailed_summary.return_value = (
                "This is a detailed summary of the story."
            )
            mock_manager_class.return_value = mock_manager

            response = await client.get(
                f"/briefing/{test_session.id}/detailed-summary", headers=auth_headers
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert (
                data["detailed_summary"] == "This is a detailed summary of the story."
            )

    @pytest.mark.asyncio
    async def test_session_progress(self, client, auth_headers, test_session):
        """Test getting session progress."""
        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            progress_data = {
                "session_id": str(test_session.id),
                "current_story_index": 0,
                "total_stories": 3,
                "session_status": "playing",
                "progress_percentage": 33.33,
            }

            mock_manager = AsyncMock()
            mock_manager.get_session_progress.return_value = progress_data
            mock_manager_class.return_value = mock_manager

            response = await client.get(f"/session/{test_session.id}/progress")

            assert response.status_code == 200
            data = await response.get_json()
            assert data["session_id"] == str(test_session.id)
            assert data["current_story_index"] == 0
            assert data["total_stories"] == 3


class TestUserEndpoints:
    """Test user-related API endpoints."""

    @pytest.mark.asyncio
    async def test_get_user_newsletters(self, client, test_user, auth_headers):
        """Test getting user newsletters."""
        response = await client.get(
            f"/users/{test_user.id}/newsletters", headers=auth_headers
        )

        assert response.status_code == 200
        data = await response.get_json()
        assert "newsletters" in data
        assert isinstance(data["newsletters"], list)

    @pytest.mark.asyncio
    async def test_update_user_preferences(self, client, test_user, auth_headers):
        """Test updating user preferences."""
        preferences = {"default_voice_type": "new_voice", "default_playback_speed": 1.5}

        response = await client.put(
            f"/users/{test_user.id}/preferences", headers=auth_headers, json=preferences
        )

        assert response.status_code == 200
        data = await response.get_json()
        assert data["status"] == "updated"


class TestSessionControlEndpoints:
    """Test session control endpoints."""

    @pytest.mark.asyncio
    async def test_session_control_pause(self, client, test_session):
        """Test session control pause action."""
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
                f"/session/{test_session.id}/control", json={"action": "pause"}
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["status"] == "success"
            assert data["action"] == "pause"

    @pytest.mark.asyncio
    async def test_session_control_invalid_action(self, client, test_session):
        """Test session control with invalid action."""
        response = await client.post(
            f"/session/{test_session.id}/control", json={"action": "invalid_action"}
        )

        assert response.status_code == 400
        data = await response.get_json()
        assert data["error"] == "invalid_action"

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, client):
        """Test getting active sessions."""
        response = await client.get("/sessions/active")

        assert response.status_code == 200
        data = await response.get_json()
        assert "active_sessions" in data
        assert "total_count" in data
        assert isinstance(data["active_sessions"], list)


class TestAPIErrorHandling:
    """Test API error handling."""

    @pytest.mark.asyncio
    async def test_invalid_session_id_format(self, client, auth_headers):
        """Test handling of invalid session ID format."""
        response = await client.get(
            "/briefing/invalid-uuid/state", headers=auth_headers
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_nonexistent_session(self, client, auth_headers):
        """Test handling of non-existent session."""
        fake_uuid = str(uuid.uuid4())

        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            mock_manager.get_session.return_value = None
            mock_manager_class.return_value = mock_manager

            response = await client.get(
                f"/briefing/{fake_uuid}/state", headers=auth_headers
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_validation_error_handling(self, client, auth_headers):
        """Test validation error handling."""
        # Send invalid JSON data
        response = await client.post(
            "/start-briefing", headers=auth_headers, json={"invalid_field": "test"}
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_internal_server_error_handling(self, client, auth_headers):
        """Test internal server error handling."""
        with patch("backend.main.get_database_session") as mock_db:
            # Make database session raise an exception
            mock_db.side_effect = Exception("Database connection failed")

            response = await client.post(
                "/start-briefing", headers=auth_headers, json={"user_id": "test-id"}
            )

            assert response.status_code == 500


class TestAPISchemaValidation:
    """Test API schema validation."""

    @pytest.mark.asyncio
    async def test_briefing_request_validation(self, client, auth_headers):
        """Test BriefingRequest schema validation."""
        # Valid request
        valid_data = {"user_id": str(uuid.uuid4())}

        with (
            patch("backend.main.get_database_session") as mock_db,
            patch("backend.main.BriefingSessionManager") as mock_manager_class,
        ):

            mock_db.return_value.__aenter__ = AsyncMock(return_value=Mock())
            mock_db.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_manager = AsyncMock()
            mock_manager.get_today_stories.return_value = []
            mock_manager_class.return_value = mock_manager

            response = await client.post(
                "/start-briefing", headers=auth_headers, json=valid_data
            )

            # Should get 404 (no stories) not validation error
            assert response.status_code == 404

    def test_pydantic_models_validation(self):
        """Test Pydantic model validation directly."""
        # Test valid BriefingRequest
        valid_request = BriefingRequest(user_id=str(uuid.uuid4()))
        assert valid_request.user_id is not None

        # Test BriefingRequest with optional voice_type
        request_with_voice = BriefingRequest(
            user_id=str(uuid.uuid4()), voice_type="premium"
        )
        assert request_with_voice.voice_type == "premium"
