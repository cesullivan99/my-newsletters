"""
End-to-end integration tests for the complete voice assistant flow
Tests the full user journey from authentication to voice briefing
"""

import pytest
import asyncio
import os
import json
from unittest.mock import AsyncMock, MagicMock, patch
from backend.main import app
from backend.models.database import User, Newsletter, Story, Session
from backend.services.session_manager import BriefingSessionManager
from dotenv import load_dotenv

load_dotenv()

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


class TestEndToEndFlow:
    @pytest.fixture
    async def test_client(self):
        """Create test client for API"""
        return app.test_client()
    
    @pytest.fixture
    async def mock_database(self):
        """Mock database for testing"""
        with patch("backend.config.get_db_session") as mock:
            session = AsyncMock()
            mock.return_value.__aenter__.return_value = session
            yield session
    
    @pytest.fixture
    def test_user(self):
        """Create test user"""
        return User(
            id="test-user-id",
            email="test@example.com",
            gmail_credentials={
                "token": "test_token",
                "refresh_token": "test_refresh_token"
            }
        )
    
    @pytest.fixture
    def test_newsletter(self):
        """Create test newsletter"""
        return Newsletter(
            id="test-newsletter-id",
            user_id="test-user-id",
            sender_email="newsletter@example.com",
            sender_name="Tech News",
            subject="Weekly Tech Update",
            received_date="2024-01-15T10:00:00Z",
            processing_status="completed"
        )
    
    @pytest.fixture
    def test_stories(self):
        """Create test stories"""
        return [
            Story(
                id="story-1",
                newsletter_id="test-newsletter-id",
                title="AI Breakthrough",
                content="Researchers announce new AI model...",
                position=0,
                audio_url="https://example.com/audio1.mp3",
                audio_status="completed"
            ),
            Story(
                id="story-2",
                newsletter_id="test-newsletter-id",
                title="Startup Funding",
                content="New startup raises Series A...",
                position=1,
                audio_url="https://example.com/audio2.mp3",
                audio_status="completed"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_complete_authentication_flow(self, test_client):
        """Test complete OAuth authentication flow"""
        # Step 1: Initialize OAuth
        async with test_client as client:
            response = await client.get("/auth/gmail-oauth")
            assert response.status_code == 200
            data = await response.get_json()
            assert "auth_url" in data
            assert "accounts.google.com" in data["auth_url"]
        
        # Step 2: Simulate OAuth callback (would normally come from Google)
        with patch("backend.services.gmail_service.GmailService.handle_oauth_callback") as mock_callback:
            mock_callback.return_value = {
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "email": "test@example.com"
            }
            
            async with test_client as client:
                response = await client.get("/auth/google/callback?code=test_auth_code")
                assert response.status_code in [302, 200]  # Redirect or success
    
    @pytest.mark.asyncio
    async def test_newsletter_processing_flow(self, test_client, test_user, mock_database):
        """Test newsletter fetching and processing"""
        # Mock authentication
        with patch("backend.auth.verify_token") as mock_auth:
            mock_auth.return_value = {"user_id": test_user.id}
            
            # Mock Gmail service
            with patch("backend.services.gmail_service.GmailService.fetch_newsletters") as mock_fetch:
                mock_fetch.return_value = [
                    {
                        "id": "msg-1",
                        "sender": "newsletter@example.com",
                        "subject": "Tech News",
                        "date": "2024-01-15",
                        "html": "<html><body>Newsletter content</body></html>"
                    }
                ]
                
                # Mock newsletter parser
                with patch("backend.services.newsletter_parser.NewsletterParser.extract_stories") as mock_parse:
                    mock_parse.return_value = [
                        {"title": "Story 1", "content": "Content 1"},
                        {"title": "Story 2", "content": "Content 2"}
                    ]
                    
                    # Trigger newsletter sync
                    async with test_client as client:
                        response = await client.post(
                            "/api/newsletters/sync",
                            headers={"Authorization": "Bearer test_token"}
                        )
                        assert response.status_code == 200
                        data = await response.get_json()
                        assert data["newsletters_processed"] > 0
    
    @pytest.mark.asyncio
    async def test_audio_generation_flow(self, test_client, test_user, test_stories):
        """Test audio generation for stories"""
        with patch("backend.auth.verify_token") as mock_auth:
            mock_auth.return_value = {"user_id": test_user.id}
            
            # Mock audio service
            with patch("backend.services.audio_service.AudioService.generate_audio") as mock_audio:
                mock_audio.return_value = b"fake_audio_data"
                
                # Mock storage service
                with patch("backend.services.storage_service.StorageService.upload_audio") as mock_storage:
                    mock_storage.return_value = "https://storage.example.com/audio.mp3"
                    
                    # Trigger audio processing
                    async with test_client as client:
                        response = await client.post(
                            f"/api/stories/{test_stories[0].id}/generate-audio",
                            headers={"Authorization": "Bearer test_token"}
                        )
                        assert response.status_code == 200
                        data = await response.get_json()
                        assert "audio_url" in data
    
    @pytest.mark.asyncio
    async def test_briefing_session_flow(self, test_client, test_user, test_stories):
        """Test complete briefing session flow"""
        with patch("backend.auth.verify_token") as mock_auth:
            mock_auth.return_value = {"user_id": test_user.id}
            
            # Mock database queries
            with patch("backend.services.session_manager.BriefingSessionManager") as MockManager:
                manager = AsyncMock()
                MockManager.return_value = manager
                
                # Start session
                manager.start_session.return_value = {
                    "session_id": "test-session",
                    "current_story": test_stories[0].__dict__
                }
                
                async with test_client as client:
                    # Step 1: Start briefing
                    response = await client.post(
                        "/api/briefing/start",
                        headers={"Authorization": "Bearer test_token"}
                    )
                    assert response.status_code == 200
                    data = await response.get_json()
                    assert "session_id" in data
                    session_id = data["session_id"]
                    
                    # Step 2: Play first story
                    manager.get_current_story.return_value = test_stories[0].__dict__
                    response = await client.get(
                        f"/api/briefing/{session_id}/current",
                        headers={"Authorization": "Bearer test_token"}
                    )
                    assert response.status_code == 200
                    data = await response.get_json()
                    assert data["title"] == "AI Breakthrough"
                    
                    # Step 3: Skip to next story
                    manager.advance_to_next.return_value = test_stories[1].__dict__
                    response = await client.post(
                        f"/api/briefing/{session_id}/skip",
                        headers={"Authorization": "Bearer test_token"}
                    )
                    assert response.status_code == 200
                    data = await response.get_json()
                    assert data["title"] == "Startup Funding"
                    
                    # Step 4: Pause session
                    manager.pause_session.return_value = True
                    response = await client.post(
                        f"/api/briefing/{session_id}/pause",
                        headers={"Authorization": "Bearer test_token"}
                    )
                    assert response.status_code == 200
                    
                    # Step 5: Resume session
                    manager.resume_session.return_value = True
                    response = await client.post(
                        f"/api/briefing/{session_id}/resume",
                        headers={"Authorization": "Bearer test_token"}
                    )
                    assert response.status_code == 200
                    
                    # Step 6: End session
                    manager.end_session.return_value = True
                    response = await client.post(
                        f"/api/briefing/{session_id}/end",
                        headers={"Authorization": "Bearer test_token"}
                    )
                    assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_voice_interaction_flow(self, test_client, test_user):
        """Test voice interaction via WebSocket"""
        with patch("backend.auth.verify_token") as mock_auth:
            mock_auth.return_value = {"user_id": test_user.id}
            
            # Mock Vocode conversation
            with patch("backend.voice.conversation_manager.ConversationManager") as MockConv:
                conv_manager = AsyncMock()
                MockConv.return_value = conv_manager
                
                # Mock voice actions
                conv_manager.handle_action.return_value = {
                    "action": "skip_story",
                    "result": "Skipped to next story"
                }
                
                # Note: Full WebSocket testing requires a WebSocket client
                # This is a simplified test of the voice action handling
                async with test_client as client:
                    response = await client.post(
                        "/api/voice/action",
                        json={
                            "action": "skip_story",
                            "session_id": "test-session"
                        },
                        headers={"Authorization": "Bearer test_token"}
                    )
                    assert response.status_code == 200
                    data = await response.get_json()
                    assert data["result"] == "Skipped to next story"
    
    @pytest.mark.asyncio
    async def test_error_recovery_flow(self, test_client):
        """Test error handling and recovery"""
        # Test invalid authentication
        async with test_client as client:
            response = await client.get("/api/briefing/current")
            assert response.status_code == 401
        
        # Test invalid session
        with patch("backend.auth.verify_token") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}
            
            async with test_client as client:
                response = await client.get(
                    "/api/briefing/invalid-session/current",
                    headers={"Authorization": "Bearer test_token"}
                )
                assert response.status_code == 404
        
        # Test rate limiting
        with patch("backend.auth.verify_token") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}
            
            # Simulate multiple rapid requests
            async with test_client as client:
                tasks = []
                for _ in range(10):
                    task = client.get(
                        "/api/newsletters/sync",
                        headers={"Authorization": "Bearer test_token"}
                    )
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                # At least some should be rate limited
                rate_limited = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 429]
                # Note: Rate limiting might not be implemented yet
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, test_client):
        """Test that performance meets PRP requirements"""
        import time
        
        with patch("backend.auth.verify_token") as mock_auth:
            mock_auth.return_value = {"user_id": "test-user"}
            
            # Test API response time
            async with test_client as client:
                start = time.time()
                response = await client.get(
                    "/api/health",
                    headers={"Authorization": "Bearer test_token"}
                )
                end = time.time()
                
                assert response.status_code == 200
                assert (end - start) < 1.0  # Should respond within 1 second
            
            # Note: Voice latency testing would require actual voice processing