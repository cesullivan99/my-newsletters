"""
Pytest configuration and fixtures for My Newsletters Voice Assistant tests.
"""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Any
from unittest.mock import Mock, AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from quart import Quart

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Mock external services during testing
os.environ.update(
    {
        "DATABASE_URL": TEST_DATABASE_URL,
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
        "ELEVENLABS_API_KEY": "test-elevenlabs-key",
        "OPENAI_API_KEY": "test-openai-key",
        "GMAIL_CLIENT_ID": "test-gmail-client-id",
        "GMAIL_CLIENT_SECRET": "test-gmail-client-secret",
        "GMAIL_REDIRECT_URI": "http://localhost:5001/auth/google/callback",
        "JWT_SECRET": "test-jwt-secret-key-for-testing-only-32-chars-long",
        "APP_ENV": "testing",
        "APP_DEBUG": "false",
    }
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    from backend.models.database import Base

    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    session_maker = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def app() -> Quart:
    """Create test Quart application."""
    # Import after setting test environment variables
    from backend.main import app

    app.config.update({"TESTING": True, "SECRET_KEY": "test-secret-key"})

    return app


@pytest_asyncio.fixture
async def client(app):
    """Create test client."""
    async with app.test_client() as test_client:
        yield test_client


@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user."""
    from backend.models.database import User

    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        name="Test User",
        default_voice_type="test_voice",
        default_playback_speed=1.0,
        google_access_token="test-access-token",
        google_refresh_token="test-refresh-token",
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


@pytest_asyncio.fixture
async def test_newsletter(db_session):
    """Create test newsletter."""
    from backend.models.database import Newsletter

    newsletter = Newsletter(
        id=uuid.uuid4(),
        name="Test Newsletter",
        publisher="Test Publisher",
        description="A test newsletter",
    )

    db_session.add(newsletter)
    await db_session.commit()
    await db_session.refresh(newsletter)

    return newsletter


@pytest_asyncio.fixture
async def test_issue(db_session, test_newsletter):
    """Create test newsletter issue."""
    from backend.models.database import Issue

    issue = Issue(
        id=uuid.uuid4(),
        newsletter_id=test_newsletter.id,
        date=datetime.now(timezone.utc),
        subject="Test Issue",
        raw_content="<html><body>Test content</body></html>",
    )

    db_session.add(issue)
    await db_session.commit()
    await db_session.refresh(issue)

    return issue


@pytest_asyncio.fixture
async def test_story(db_session, test_issue):
    """Create test story."""
    from backend.models.database import Story

    story = Story(
        id=uuid.uuid4(),
        issue_id=test_issue.id,
        headline="Test Story Headline",
        one_sentence_summary="This is a test story summary.",
        full_text_summary="This is a longer test story summary with more details.",
        summary_audio_url="https://test.com/audio.mp3",
        full_text_audio_url="https://test.com/full-audio.mp3",
    )

    db_session.add(story)
    await db_session.commit()
    await db_session.refresh(story)

    return story


@pytest_asyncio.fixture
async def test_session(db_session, test_user, test_story):
    """Create test listening session."""
    from backend.models.database import ListeningSession

    session = ListeningSession(
        id=uuid.uuid4(),
        user_id=test_user.id,
        current_story_id=test_story.id,
        current_story_index=0,
        session_status="playing",
        story_order=[test_story.id],
    )

    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    return session


@pytest.fixture
def mock_elevenlabs():
    """Mock ElevenLabs client."""
    mock_client = Mock()
    mock_stream = AsyncMock()
    mock_stream.__aiter__ = AsyncMock(return_value=iter([b"test", b"audio", b"data"]))

    mock_client.text_to_speech.stream.return_value = mock_stream
    return mock_client


@pytest.fixture
def mock_openai():
    """Mock OpenAI client."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test AI response"))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_gmail():
    """Mock Gmail service."""
    mock_service = Mock()
    mock_messages = Mock()
    mock_messages.list.return_value.execute.return_value = {
        "messages": [{"id": "test-message-id"}]
    }
    mock_messages.get.return_value.execute.return_value = {
        "id": "test-message-id",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Test Newsletter"},
                {"name": "From", "value": "test@newsletter.com"},
                {"name": "Date", "value": "Wed, 10 Aug 2025 10:00:00 -0000"},
            ],
            "body": {"data": "VGVzdCBlbWFpbCBjb250ZW50"},  # base64 "Test email content"
        },
    }

    mock_service.users.return_value.messages.return_value = mock_messages
    return mock_service


@pytest.fixture
def mock_google_oauth():
    """Mock Google OAuth flow."""
    mock_flow = Mock()
    mock_credentials = Mock()
    mock_credentials.token = "test-access-token"
    mock_credentials.refresh_token = "test-refresh-token"
    mock_credentials.expiry = datetime.now(timezone.utc)
    mock_credentials.expired = False

    mock_flow.credentials = mock_credentials
    mock_flow.fetch_token = Mock()
    mock_flow.authorization_url = Mock(
        return_value=("https://test-oauth-url", "test-state")
    )

    return mock_flow


@pytest.fixture
def auth_token(test_user):
    """Create test JWT token."""
    from backend.utils.auth import create_access_token

    token_data = {"sub": str(test_user.id), "email": test_user.email}
    return create_access_token(token_data)


@pytest.fixture
def auth_headers(auth_token):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def mock_vocode_conversation():
    """Mock Vocode conversation."""
    mock_conversation = AsyncMock()
    mock_conversation.start = AsyncMock()
    mock_conversation.terminate = AsyncMock()
    return mock_conversation


@pytest.fixture
def mock_session_manager():
    """Mock session manager."""
    mock_manager = AsyncMock()
    mock_manager.get_current_story = AsyncMock()
    mock_manager.advance_story = AsyncMock()
    mock_manager.get_detailed_summary = AsyncMock(return_value="Detailed test summary")
    mock_manager.pause_session = AsyncMock(return_value=True)
    mock_manager.resume_session = AsyncMock(return_value=True)
    return mock_manager


# Test data constants
TEST_USER_DATA = {
    "email": "test@example.com",
    "name": "Test User",
    "default_voice_type": "test_voice",
    "default_playback_speed": 1.0,
}

TEST_STORY_DATA = {
    "headline": "Test Story",
    "one_sentence_summary": "Test summary",
    "full_text_summary": "Full test summary",
    "audio_url": "https://test.com/audio.mp3",
}

TEST_BRIEFING_REQUEST = {"user_id": "test-user-id", "voice_type": "test_voice"}


# Helper functions for tests
def assert_response_json(response, expected_fields: list):
    """Assert response is JSON and contains expected fields."""
    assert response.headers["Content-Type"] == "application/json"
    data = response.get_json()
    for field in expected_fields:
        assert field in data


async def create_test_data(db_session) -> Dict[str, Any]:
    """Create comprehensive test data set."""
    from backend.models.database import User, Newsletter, Issue, Story, ListeningSession

    # Create test user
    user = User(
        id=uuid.uuid4(),
        email="integration@test.com",
        name="Integration Test User",
        default_voice_type="test_voice",
    )
    db_session.add(user)

    # Create test newsletter
    newsletter = Newsletter(
        id=uuid.uuid4(), name="Integration Newsletter", publisher="Test Publisher"
    )
    db_session.add(newsletter)

    # Create test issue
    issue = Issue(
        id=uuid.uuid4(),
        newsletter_id=newsletter.id,
        date=datetime.now(timezone.utc),
        subject="Integration Test Issue",
        raw_content="<p>Test content</p>",
    )
    db_session.add(issue)

    # Create test stories
    stories = []
    for i in range(3):
        story = Story(
            id=uuid.uuid4(),
            issue_id=issue.id,
            headline=f"Test Story {i+1}",
            one_sentence_summary=f"Summary {i+1}",
            full_text_summary=f"Full summary {i+1}",
            summary_audio_url=f"https://test.com/audio-{i+1}.mp3",
        )
        db_session.add(story)
        stories.append(story)

    await db_session.commit()

    # Refresh all objects
    await db_session.refresh(user)
    await db_session.refresh(newsletter)
    await db_session.refresh(issue)
    for story in stories:
        await db_session.refresh(story)

    return {"user": user, "newsletter": newsletter, "issue": issue, "stories": stories}
