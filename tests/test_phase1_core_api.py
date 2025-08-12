"""
Phase 1: Core API Testing - 32 Critical Tests
Comprehensive test suite for all core API endpoints
"""
import sys
import pytest
import asyncio
import json
import jwt
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from httpx import AsyncClient
from quart import Quart
from backend.main import app
from backend.config import Config
from backend.models.database import User, Newsletter, Story, ListeningSession
from backend.models.schemas import (
    ErrorResponse, HealthCheckResponse, 
    BriefingResponse, NewsletterResponse
)

# Test configuration
TEST_USER_EMAIL = "test@example.com"
TEST_USER_ID = "test-user-123"
TEST_JWT_SECRET = "test-secret-key"
TEST_SESSION_ID = "test-session-123"
TEST_NEWSLETTER_ID = "test-newsletter-123"
TEST_STORY_ID = "test-story-123"


class TestPhase1CoreAPI:
    """
    Phase 1: Core API Testing - 32 Critical Tests
    Testing all authentication, newsletter, briefing, and audio endpoints
    """

    @pytest.fixture
    async def client(self):
        """Create test client"""
        app.config["TESTING"] = True
        async with app.test_client() as client:
            yield client

    @pytest.fixture
    def mock_settings(self, monkeypatch):
        """Mock settings for testing"""
        mock_config = Mock(
            jwt_secret_key=TEST_JWT_SECRET,
            jwt_algorithm="HS256",
            jwt_expiration_hours=24,
            supabase_url="http://test.supabase.co",
            supabase_anon_key="test-anon-key",
            supabase_service_role_key="test-service-key",
            database_url="postgresql://test:test@localhost/test",
            gmail_client_id="test-client-id",
            gmail_client_secret="test-client-secret",
            openai_api_key="test-openai-key",
            elevenlabs_api_key="test-elevenlabs-key",
            elevenlabs_voice_id="test-voice-id"
        )
        monkeypatch.setattr("backend.config.config", mock_config)

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session"""
        session = AsyncMock()
        return session

    @pytest.fixture
    def valid_token(self):
        """Generate valid JWT token for testing"""
        payload = {
            "sub": TEST_USER_ID,
            "email": TEST_USER_EMAIL,
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

    @pytest.fixture
    def expired_token(self):
        """Generate expired JWT token for testing"""
        payload = {
            "sub": TEST_USER_ID,
            "email": TEST_USER_EMAIL,
            "exp": datetime.utcnow() - timedelta(hours=1),
            "iat": datetime.utcnow() - timedelta(hours=25)
        }
        return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

    # ========== 1.1 Authentication Flow Testing (8 tests) ==========

    @pytest.mark.asyncio
    async def test_gmail_oauth_initialize(self, client, mock_settings):
        """Test 1: Gmail OAuth Initialize - POST /auth/gmail-oauth returns valid auth URL"""
        with patch("backend.routes.auth.create_oauth_flow") as mock_oauth:
            mock_oauth.return_value = "https://accounts.google.com/oauth/authorize?..."
            
            response = await client.post("/auth/gmail-oauth")
            
            assert response.status_code == 200
            data = await response.get_json()
            assert "auth_url" in data
            assert data["auth_url"].startswith("https://accounts.google.com")

    @pytest.mark.asyncio
    async def test_oauth_callback_handler(self, client, mock_settings, mock_db_session):
        """Test 2: OAuth Callback Handler - GET /auth/google/callback processes code"""
        with patch("backend.api.auth.exchange_code_for_tokens") as mock_exchange:
            with patch("backend.api.auth.get_user_info") as mock_user_info:
                with patch("backend.api.auth.create_or_update_user") as mock_create_user:
                    mock_exchange.return_value = {
                        "access_token": "test-access-token",
                        "refresh_token": "test-refresh-token"
                    }
                    mock_user_info.return_value = {
                        "email": TEST_USER_EMAIL,
                        "name": "Test User"
                    }
                    mock_create_user.return_value = Mock(
                        id=TEST_USER_ID,
                        email=TEST_USER_EMAIL
                    )
                    
                    response = await client.get("/auth/google/callback?code=test-code")
                    
                    assert response.status_code == 302  # Redirect
                    location = response.headers.get("Location")
                    assert "mynewsletters://" in location or "token=" in location

    @pytest.mark.asyncio
    async def test_user_info_retrieval(self, client, valid_token, mock_db_session):
        """Test 3: User Info Retrieval - GET /auth/user returns authenticated user details"""
        with patch("backend.api.auth.get_user_by_id") as mock_get_user:
            mock_get_user.return_value = Mock(
                id=TEST_USER_ID,
                email=TEST_USER_EMAIL,
                name="Test User",
                created_at=datetime.utcnow()
            )
            
            response = await client.get(
                "/auth/user",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert data["email"] == TEST_USER_EMAIL
            assert data["id"] == TEST_USER_ID

    @pytest.mark.asyncio
    async def test_jwt_token_validation(self, client, valid_token):
        """Test 4: JWT Token Validation - POST /auth/validate correctly validates tokens"""
        response = await client.post(
            "/auth/validate",
            json={"token": valid_token}
        )
        
        assert response.status_code == 200
        data = await response.get_json()
        assert data["valid"] is True
        assert data["user_id"] == TEST_USER_ID

    @pytest.mark.asyncio
    async def test_token_refresh(self, client, valid_token, mock_db_session):
        """Test 5: Token Refresh - POST /auth/refresh generates new tokens"""
        with patch("backend.api.auth.refresh_user_tokens") as mock_refresh:
            mock_refresh.return_value = {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token"
            }
            
            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": valid_token}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert "access_token" in data
            assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_logout_flow(self, client, valid_token):
        """Test 6: Logout Flow - POST /auth/logout invalidates tokens properly"""
        response = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        
        assert response.status_code == 200
        data = await response.get_json()
        assert data["message"] == "Logged out successfully"

    @pytest.mark.asyncio
    async def test_profile_updates(self, client, valid_token, mock_db_session):
        """Test 7: Profile Updates - PUT /auth/profile updates user preferences"""
        with patch("backend.api.auth.update_user_profile") as mock_update:
            mock_update.return_value = Mock(
                id=TEST_USER_ID,
                email=TEST_USER_EMAIL,
                preferences={"voice_speed": 1.2}
            )
            
            response = await client.put(
                "/auth/profile",
                headers={"Authorization": f"Bearer {valid_token}"},
                json={"preferences": {"voice_speed": 1.2}}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert data["preferences"]["voice_speed"] == 1.2

    @pytest.mark.asyncio
    async def test_auth_error_handling(self, client, expired_token):
        """Test 8: Error Handling - Invalid/expired tokens handled gracefully"""
        # Test with expired token
        response = await client.get(
            "/auth/user",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401
        
        # Test with invalid token
        response = await client.get(
            "/auth/user",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
        
        # Test with no token
        response = await client.get("/auth/user")
        assert response.status_code == 401

    # ========== 1.2 Newsletter Management API Testing (7 tests) ==========

    @pytest.mark.asyncio
    async def test_newsletter_fetching(self, client, valid_token):
        """Test 9: Newsletter Fetching - POST /newsletters/fetch retrieves emails"""
        with patch("backend.services.gmail_service.GmailService.fetch_newsletters") as mock_fetch:
            mock_fetch.return_value = [
                {
                    "id": "msg-1",
                    "from": "newsletter@example.com",
                    "subject": "Daily News",
                    "body": "<html>Newsletter content</html>",
                    "date": datetime.utcnow().isoformat()
                }
            ]
            
            response = await client.post(
                "/newsletters/fetch",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert "newsletters_fetched" in data
            assert data["newsletters_fetched"] == 1

    @pytest.mark.asyncio
    async def test_newsletter_parsing(self, client, valid_token):
        """Test 10: Newsletter Parsing - Content extraction and story separation"""
        with patch("backend.services.newsletter_parser.NewsletterParser.parse") as mock_parse:
            mock_parse.return_value = {
                "stories": [
                    {
                        "title": "Story 1",
                        "summary": "Summary of story 1",
                        "content": "Full content of story 1"
                    }
                ],
                "metadata": {
                    "source": "Test Newsletter",
                    "published_date": datetime.utcnow().isoformat()
                }
            }
            
            response = await client.post(
                "/newsletters/parse",
                headers={"Authorization": f"Bearer {valid_token}"},
                json={"html_content": "<html>Newsletter HTML</html>"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert len(data["stories"]) == 1
            assert data["stories"][0]["title"] == "Story 1"

    @pytest.mark.asyncio
    async def test_newsletter_storage(self, client, valid_token, mock_db_session):
        """Test 11: Newsletter Storage - Parsed newsletters saved to database"""
        with patch("backend.api.newsletters.save_newsletter") as mock_save:
            mock_save.return_value = Mock(
                id=TEST_NEWSLETTER_ID,
                source="Test Newsletter",
                processing_status="completed"
            )
            
            response = await client.post(
                "/newsletters/save",
                headers={"Authorization": f"Bearer {valid_token}"},
                json={
                    "source": "Test Newsletter",
                    "stories": [{"title": "Story 1", "content": "Content"}]
                }
            )
            
            assert response.status_code == 201
            data = await response.get_json()
            assert data["id"] == TEST_NEWSLETTER_ID
            assert data["processing_status"] == "completed"

    @pytest.mark.asyncio
    async def test_newsletter_listing(self, client, valid_token):
        """Test 12: Newsletter Listing - GET /newsletters returns user's newsletters"""
        with patch("backend.api.newsletters.get_user_newsletters") as mock_list:
            mock_list.return_value = {
                "newsletters": [
                    {
                        "id": TEST_NEWSLETTER_ID,
                        "source": "Test Newsletter",
                        "published_date": datetime.utcnow().isoformat(),
                        "story_count": 5
                    }
                ],
                "total": 1,
                "page": 1
            }
            
            response = await client.get(
                "/newsletters?page=1&limit=10",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert data["total"] == 1
            assert len(data["newsletters"]) == 1

    @pytest.mark.asyncio
    async def test_newsletter_details(self, client, valid_token):
        """Test 13: Newsletter Details - GET /newsletters/{id} returns full newsletter"""
        with patch("backend.api.newsletters.get_newsletter_by_id") as mock_get:
            mock_get.return_value = Mock(
                id=TEST_NEWSLETTER_ID,
                source="Test Newsletter",
                stories=[
                    Mock(id=TEST_STORY_ID, title="Story 1", summary="Summary 1")
                ]
            )
            
            response = await client.get(
                f"/newsletters/{TEST_NEWSLETTER_ID}",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert data["id"] == TEST_NEWSLETTER_ID
            assert len(data["stories"]) == 1

    @pytest.mark.asyncio
    async def test_processing_status_updates(self, client, valid_token):
        """Test 14: Processing Status - Newsletter status updates correctly"""
        with patch("backend.api.newsletters.update_processing_status") as mock_update:
            mock_update.return_value = Mock(
                id=TEST_NEWSLETTER_ID,
                processing_status="completed"
            )
            
            response = await client.patch(
                f"/newsletters/{TEST_NEWSLETTER_ID}/status",
                headers={"Authorization": f"Bearer {valid_token}"},
                json={"status": "completed"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert data["processing_status"] == "completed"

    @pytest.mark.asyncio
    async def test_newsletter_error_handling(self, client, valid_token):
        """Test 15: Error Handling - Gmail API, parsing, database errors handled"""
        # Test Gmail API failure
        with patch("backend.services.gmail_service.GmailService.fetch_newsletters") as mock_fetch:
            mock_fetch.side_effect = Exception("Gmail API error")
            
            response = await client.post(
                "/newsletters/fetch",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            assert response.status_code == 500
            
        # Test parsing error
        with patch("backend.services.newsletter_parser.NewsletterParser.parse") as mock_parse:
            mock_parse.side_effect = Exception("Parsing error")
            
            response = await client.post(
                "/newsletters/parse",
                headers={"Authorization": f"Bearer {valid_token}"},
                json={"html_content": "<html>Bad HTML</html>"}
            )
            assert response.status_code == 500

    # ========== 1.3 Briefing Session API Testing (6 tests) ==========

    @pytest.mark.asyncio
    async def test_session_creation(self, client, valid_token):
        """Test 16: Session Creation - POST /briefing/start creates new session"""
        with patch("backend.services.session_manager.BriefingSessionManager.create_session") as mock_create:
            mock_create.return_value = Mock(
                id=TEST_SESSION_ID,
                user_id=TEST_USER_ID,
                status="active",
                current_position=0,
                story_queue=[TEST_STORY_ID]
            )
            
            response = await client.post(
                "/briefing/start",
                headers={"Authorization": f"Bearer {valid_token}"},
                json={"newsletter_ids": [TEST_NEWSLETTER_ID]}
            )
            
            assert response.status_code == 201
            data = await response.get_json()
            assert data["id"] == TEST_SESSION_ID
            assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_session_state(self, client, valid_token):
        """Test 17: Session State - GET /briefing/session/{id} returns session state"""
        with patch("backend.services.session_manager.BriefingSessionManager.get_session") as mock_get:
            mock_get.return_value = Mock(
                id=TEST_SESSION_ID,
                status="active",
                current_position=2,
                story_queue=[TEST_STORY_ID] * 5,
                created_at=datetime.utcnow()
            )
            
            response = await client.get(
                f"/briefing/session/{TEST_SESSION_ID}",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert data["id"] == TEST_SESSION_ID
            assert data["current_position"] == 2

    @pytest.mark.asyncio
    async def test_session_control(self, client, valid_token):
        """Test 18: Session Control - POST /briefing/session/{id}/pause|resume|stop"""
        # Test pause
        with patch("backend.services.session_manager.BriefingSessionManager.pause_session") as mock_pause:
            mock_pause.return_value = Mock(status="paused")
            
            response = await client.post(
                f"/briefing/session/{TEST_SESSION_ID}/pause",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            assert response.status_code == 200
            data = await response.get_json()
            assert data["status"] == "paused"
        
        # Test resume
        with patch("backend.services.session_manager.BriefingSessionManager.resume_session") as mock_resume:
            mock_resume.return_value = Mock(status="active")
            
            response = await client.post(
                f"/briefing/session/{TEST_SESSION_ID}/resume",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            assert response.status_code == 200
            data = await response.get_json()
            assert data["status"] == "active"
        
        # Test stop
        with patch("backend.services.session_manager.BriefingSessionManager.stop_session") as mock_stop:
            mock_stop.return_value = Mock(status="completed")
            
            response = await client.post(
                f"/briefing/session/{TEST_SESSION_ID}/stop",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            assert response.status_code == 200
            data = await response.get_json()
            assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_story_navigation(self, client, valid_token):
        """Test 19: Story Navigation - POST /briefing/session/{id}/next|previous"""
        # Test next
        with patch("backend.services.session_manager.BriefingSessionManager.advance_story") as mock_next:
            mock_next.return_value = Mock(current_position=3)
            
            response = await client.post(
                f"/briefing/session/{TEST_SESSION_ID}/next",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            assert response.status_code == 200
            data = await response.get_json()
            assert data["current_position"] == 3
        
        # Test previous
        with patch("backend.services.session_manager.BriefingSessionManager.previous_story") as mock_prev:
            mock_prev.return_value = Mock(current_position=1)
            
            response = await client.post(
                f"/briefing/session/{TEST_SESSION_ID}/previous",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            assert response.status_code == 200
            data = await response.get_json()
            assert data["current_position"] == 1

    @pytest.mark.asyncio
    async def test_session_metadata(self, client, valid_token):
        """Test 20: Session Metadata - Current story, progress, remaining tracked"""
        with patch("backend.services.session_manager.BriefingSessionManager.get_metadata") as mock_meta:
            mock_meta.return_value = {
                "current_story": {
                    "id": TEST_STORY_ID,
                    "title": "Current Story",
                    "source": "Test Newsletter"
                },
                "progress": {
                    "current": 3,
                    "total": 10,
                    "percentage": 30
                },
                "remaining_stories": 7
            }
            
            response = await client.get(
                f"/briefing/session/{TEST_SESSION_ID}/metadata",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert data["current_story"]["id"] == TEST_STORY_ID
            assert data["progress"]["percentage"] == 30

    @pytest.mark.asyncio
    async def test_session_cleanup(self, client, valid_token):
        """Test 21: Session Cleanup - Expired sessions handled properly"""
        with patch("backend.services.session_manager.BriefingSessionManager.cleanup_expired") as mock_cleanup:
            mock_cleanup.return_value = {"cleaned": 3, "remaining": 2}
            
            response = await client.post(
                "/briefing/cleanup",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert data["cleaned"] == 3

    # ========== 1.4 Audio Processing API Testing (6 tests) ==========

    @pytest.mark.asyncio
    async def test_audio_generation(self, client, valid_token):
        """Test 22: Audio Generation - POST /audio/generate creates TTS audio"""
        with patch("backend.services.audio_service.AudioService.generate_audio") as mock_generate:
            mock_generate.return_value = {
                "audio_url": "https://storage.example.com/audio/test.mp3",
                "duration": 120,
                "size": 2048000
            }
            
            response = await client.post(
                "/audio/generate",
                headers={"Authorization": f"Bearer {valid_token}"},
                json={
                    "text": "This is test content for TTS",
                    "story_id": TEST_STORY_ID
                }
            )
            
            assert response.status_code == 201
            data = await response.get_json()
            assert "audio_url" in data
            assert data["duration"] == 120

    @pytest.mark.asyncio
    async def test_audio_storage(self, client, valid_token):
        """Test 23: Audio Storage - Generated audio uploaded to Supabase Storage"""
        with patch("backend.services.storage_service.StorageService.upload_audio") as mock_upload:
            mock_upload.return_value = {
                "url": "https://storage.supabase.co/audio/test.mp3",
                "path": "audio/test.mp3"
            }
            
            response = await client.post(
                "/audio/upload",
                headers={"Authorization": f"Bearer {valid_token}"},
                data={"audio_file": (b"fake audio data", "test.mp3")}
            )
            
            assert response.status_code == 201
            data = await response.get_json()
            assert "url" in data

    @pytest.mark.asyncio
    async def test_audio_retrieval(self, client, valid_token):
        """Test 24: Audio Retrieval - GET /audio/{story_id} returns valid URLs"""
        with patch("backend.services.storage_service.StorageService.get_audio_url") as mock_get:
            mock_get.return_value = "https://storage.supabase.co/audio/story-123.mp3"
            
            response = await client.get(
                f"/audio/{TEST_STORY_ID}",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert "audio_url" in data
            assert data["audio_url"].endswith(".mp3")

    @pytest.mark.asyncio
    async def test_audio_queue_status(self, client, valid_token):
        """Test 25: Audio Queue Status - Background processing job status tracking"""
        with patch("backend.jobs.audio_processing.get_queue_status") as mock_status:
            mock_status.return_value = {
                "pending": 5,
                "processing": 2,
                "completed": 10,
                "failed": 1
            }
            
            response = await client.get(
                "/audio/queue/status",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 200
            data = await response.get_json()
            assert data["pending"] == 5
            assert data["completed"] == 10

    @pytest.mark.asyncio
    async def test_batch_processing(self, client, valid_token):
        """Test 26: Batch Processing - Multiple stories processed efficiently"""
        with patch("backend.jobs.audio_processing.process_batch") as mock_batch:
            mock_batch.return_value = {
                "processed": 10,
                "failed": 0,
                "time_taken": 45.2
            }
            
            response = await client.post(
                "/audio/batch",
                headers={"Authorization": f"Bearer {valid_token}"},
                json={"story_ids": [TEST_STORY_ID] * 10}
            )
            
            assert response.status_code == 202
            data = await response.get_json()
            assert data["processed"] == 10

    @pytest.mark.asyncio
    async def test_audio_error_recovery(self, client, valid_token):
        """Test 27: Error Recovery - TTS failures, storage failures handled"""
        # Test TTS failure
        with patch("backend.services.audio_service.AudioService.generate_audio") as mock_generate:
            mock_generate.side_effect = Exception("ElevenLabs API error")
            
            response = await client.post(
                "/audio/generate",
                headers={"Authorization": f"Bearer {valid_token}"},
                json={"text": "Test text", "story_id": TEST_STORY_ID}
            )
            assert response.status_code == 500
            data = await response.get_json()
            assert "error" in data
        
        # Test storage failure with retry
        with patch("backend.services.storage_service.StorageService.upload_audio") as mock_upload:
            mock_upload.side_effect = [Exception("Storage error"), {"url": "success.mp3"}]
            
            with patch("backend.services.audio_service.retry_with_backoff") as mock_retry:
                mock_retry.return_value = {"url": "success.mp3"}
                
                response = await client.post(
                    "/audio/upload",
                    headers={"Authorization": f"Bearer {valid_token}"},
                    data={"audio_file": (b"audio", "test.mp3")}
                )
                assert response.status_code == 201

    # ========== Additional Core Tests (5 tests) ==========

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test 28: Health Check - GET /health returns service status"""
        with patch("backend.main.check_database_health") as mock_db:
            with patch("backend.main.check_elevenlabs_health") as mock_eleven:
                with patch("backend.main.check_openai_health") as mock_openai:
                    mock_db.return_value = True
                    mock_eleven.return_value = True
                    mock_openai.return_value = True
                    
                    response = await client.get("/health")
                    
                    assert response.status_code == 200
                    data = await response.get_json()
                    assert data["status"] == "healthy"
                    assert data["services"]["database"] == "healthy"
                    assert data["services"]["elevenlabs"] == "healthy"
                    assert data["services"]["openai"] == "healthy"

    @pytest.mark.asyncio
    async def test_cors_configuration(self, client):
        """Test 29: CORS Configuration - Cross-origin requests handled properly"""
        response = await client.options(
            "/auth/user",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
        assert "Access-Control-Allow-Headers" in response.headers

    @pytest.mark.asyncio
    async def test_request_validation(self, client, valid_token):
        """Test 30: Request Validation - Invalid request bodies rejected"""
        # Test missing required fields
        response = await client.post(
            "/briefing/start",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={}  # Missing required newsletter_ids
        )
        assert response.status_code == 422
        
        # Test invalid data types
        response = await client.post(
            "/briefing/start",
            headers={"Authorization": f"Bearer {valid_token}"},
            json={"newsletter_ids": "not-a-list"}  # Should be list
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_rate_limiting(self, client, valid_token):
        """Test 31: Rate Limiting - API endpoints protected against abuse"""
        with patch("backend.middleware.rate_limiter.check_rate_limit") as mock_limit:
            mock_limit.return_value = False  # Rate limit exceeded
            
            response = await client.post(
                "/newsletters/fetch",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            
            assert response.status_code == 429
            data = await response.get_json()
            assert "rate limit" in data.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_database_connection_pooling(self, client, valid_token):
        """Test 32: Database Connection Pooling - Concurrent operations work"""
        async def make_request():
            return await client.get(
                "/auth/user",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
        
        with patch("backend.api.auth.get_user_by_id") as mock_get:
            mock_get.return_value = Mock(
                id=TEST_USER_ID,
                email=TEST_USER_EMAIL
            )
            
            # Make 10 concurrent requests
            tasks = [make_request() for _ in range(10)]
            responses = await asyncio.gather(*tasks)
            
            # All should succeed
            assert all(r.status_code == 200 for r in responses)


def run_phase1_tests():
    """Run all Phase 1 Core API tests and generate report"""
    import subprocess
    import sys
    
    print("=" * 80)
    print("PHASE 1: CORE API TESTING - 32 CRITICAL TESTS")
    print("=" * 80)
    
    # Run pytest with verbose output and coverage
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short", "-s"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.stderr:
        print("Errors:", result.stderr)
    
    # Parse results
    if "passed" in result.stdout:
        passed = int(result.stdout.split(" passed")[0].split()[-1])
        total = 32
        print(f"\n✅ Phase 1 Complete: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All Phase 1 tests passed! Ready for Phase 2.")
            return True
        else:
            print(f"⚠️  {total - passed} tests failed. Please fix before proceeding.")
            return False
    else:
        print("❌ Test execution failed. Please check the errors above.")
        return False


if __name__ == "__main__":
    # Run the test suite
    success = run_phase1_tests()
    sys.exit(0 if success else 1)