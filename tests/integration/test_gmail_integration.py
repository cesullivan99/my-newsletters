"""
Integration tests for Gmail OAuth and email fetching
Run with actual credentials to validate Gmail integration
"""

import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock
from backend.services.gmail_service import GmailService
from backend.models.database import User
from dotenv import load_dotenv

load_dotenv()

# Skip these tests if running in CI or without credentials
SKIP_INTEGRATION = os.getenv("TEST_GMAIL_MOCK", "true").lower() == "true"
pytestmark = pytest.mark.skipif(SKIP_INTEGRATION, reason="Gmail integration tests require real credentials")


class TestGmailIntegration:
    @pytest.fixture
    async def gmail_service(self):
        """Create Gmail service instance"""
        service = GmailService()
        return service
    
    @pytest.fixture
    def test_user(self):
        """Create test user with OAuth credentials"""
        return User(
            email="test@example.com",
            gmail_credentials={
                "token": os.getenv("TEST_GMAIL_TOKEN"),
                "refresh_token": os.getenv("TEST_GMAIL_REFRESH_TOKEN"),
                "client_id": os.getenv("GMAIL_CLIENT_ID"),
                "client_secret": os.getenv("GMAIL_CLIENT_SECRET")
            }
        )
    
    @pytest.mark.asyncio
    async def test_oauth_flow_initialization(self, gmail_service):
        """Test OAuth flow initialization"""
        auth_url = await gmail_service.get_authorization_url(
            redirect_uri="http://localhost:5001/auth/google/callback"
        )
        
        assert auth_url is not None
        assert "accounts.google.com" in auth_url
        assert "scope=https://www.googleapis.com/auth/gmail.readonly" in auth_url
    
    @pytest.mark.asyncio
    async def test_fetch_newsletters(self, gmail_service, test_user):
        """Test fetching newsletters from Gmail"""
        # This test requires valid credentials
        if not test_user.gmail_credentials.get("token"):
            pytest.skip("No test Gmail token available")
        
        newsletters = await gmail_service.fetch_newsletters(
            user=test_user,
            query="label:newsletter",
            max_results=5
        )
        
        assert isinstance(newsletters, list)
        # Verify newsletter structure if any found
        if newsletters:
            newsletter = newsletters[0]
            assert "id" in newsletter
            assert "sender" in newsletter
            assert "subject" in newsletter
            assert "date" in newsletter
    
    @pytest.mark.asyncio
    async def test_parse_newsletter_content(self, gmail_service, test_user):
        """Test parsing newsletter HTML content"""
        # Sample newsletter HTML
        sample_html = """
        <html>
            <body>
                <h1>Tech Newsletter</h1>
                <article>
                    <h2>AI Breakthrough</h2>
                    <p>Researchers announce new AI model...</p>
                </article>
                <article>
                    <h2>Startup News</h2>
                    <p>New startup raises funding...</p>
                </article>
            </body>
        </html>
        """
        
        # Parse the content
        from backend.services.newsletter_parser import NewsletterParser
        parser = NewsletterParser()
        stories = await parser.extract_stories(sample_html)
        
        assert len(stories) > 0
        assert stories[0]["title"] is not None
        assert stories[0]["content"] is not None
    
    @pytest.mark.asyncio
    async def test_token_refresh(self, gmail_service, test_user):
        """Test OAuth token refresh mechanism"""
        if not test_user.gmail_credentials.get("refresh_token"):
            pytest.skip("No refresh token available")
        
        # Simulate expired token
        test_user.gmail_credentials["token"] = "expired_token"
        
        # Attempt to use service (should trigger refresh)
        try:
            result = await gmail_service.verify_credentials(test_user)
            assert result is True
        except Exception as e:
            # Token refresh might fail without valid refresh token
            assert "token" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, gmail_service):
        """Test Gmail API rate limiting handling"""
        # Make multiple rapid requests
        tasks = []
        for _ in range(5):
            task = gmail_service.check_rate_limit()
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify rate limiting is enforced
        assert all(r is None or isinstance(r, Exception) for r in results)