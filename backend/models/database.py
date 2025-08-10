"""
SQLAlchemy ORM models for MyNewsletters database.

This module defines all database tables and relationships based on the schema
defined in examples/db-schema.md, optimized for Supabase PostgreSQL.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


class User(Base):
    """
    User account information and preferences.

    Stores user authentication data and personalization settings for
    newsletter briefing preferences.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    default_voice_type: Mapped[str | None] = mapped_column(
        String(50), default="default"
    )
    default_playback_speed: Mapped[float] = mapped_column(Float, default=1.0)
    summarization_depth: Mapped[str] = mapped_column(String(50), default="high-level")

    # Google OAuth fields
    google_access_token: Mapped[str | None] = mapped_column(Text)
    google_refresh_token: Mapped[str | None] = mapped_column(Text)
    google_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    # Relationships
    subscriptions: Mapped[list["UserSubscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    listening_sessions: Mapped[list["ListeningSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Newsletter(Base):
    """
    Newsletter publication information.

    Stores metadata about newsletters that users can subscribe to.
    """

    __tablename__ = "newsletters"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    publisher: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Relationships
    subscriptions: Mapped[list["UserSubscription"]] = relationship(
        back_populates="newsletter", cascade="all, delete-orphan"
    )
    issues: Mapped[list["Issue"]] = relationship(
        back_populates="newsletter", cascade="all, delete-orphan"
    )


class UserSubscription(Base):
    """
    Junction table linking users to their newsletter subscriptions.
    """

    __tablename__ = "user_subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    newsletter_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("newsletters.id", ondelete="CASCADE"),
        primary_key=True,
    )
    subscribed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="subscriptions")
    newsletter: Mapped["Newsletter"] = relationship(back_populates="subscriptions")


class Issue(Base):
    """
    Individual newsletter issues/editions.

    Represents a single published edition of a newsletter with its metadata.
    """

    __tablename__ = "issues"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    newsletter_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("newsletters.id", ondelete="CASCADE")
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    newsletter: Mapped["Newsletter"] = relationship(back_populates="issues")
    stories: Mapped[list["Story"]] = relationship(
        back_populates="issue", cascade="all, delete-orphan"
    )


class Story(Base):
    """
    Individual stories extracted from newsletter issues.

    Contains the story content, summaries, and associated audio file URLs.
    """

    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("issues.id", ondelete="CASCADE")
    )
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    one_sentence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    full_text_summary: Mapped[str] = mapped_column(Text, nullable=False)
    full_article: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    summary_audio_url: Mapped[str | None] = mapped_column(Text)
    full_text_audio_url: Mapped[str | None] = mapped_column(Text)

    # Relationships
    issue: Mapped["Issue"] = relationship(back_populates="stories")


class ListeningSession(Base):
    """
    User's daily briefing session state.

    Tracks the progress through stories in a briefing session to enable
    seamless interruption and resumption.
    """

    __tablename__ = "listening_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    current_story_id: Mapped[uuid.UUID | None] = mapped_column(
        PostgresUUID(as_uuid=True), ForeignKey("stories.id")
    )
    current_story_index: Mapped[int] = mapped_column(Integer, default=0)
    session_status: Mapped[str] = mapped_column(
        String(50), default="playing"
    )  # 'playing', 'paused', 'completed'
    story_order: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(PostgresUUID(as_uuid=True)), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="listening_sessions")
    chat_logs: Mapped[list["ChatLog"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatLog(Base):
    """
    Conversation history for briefing sessions.

    Stores all user interactions and AI responses to maintain context
    across interruptions and provide conversation history.
    """

    __tablename__ = "chat_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PostgresUUID(as_uuid=True),
        ForeignKey("listening_sessions.id", ondelete="CASCADE"),
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    role: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(50))  # 'skip', 'tell_more', etc.

    # Relationships
    session: Mapped["ListeningSession"] = relationship(back_populates="chat_logs")


# Database utility functions


def get_database_url() -> str:
    """Get database URL from environment variables."""
    import os

    from dotenv import load_dotenv

    load_dotenv()
    return os.getenv("DATABASE_URL", "sqlite:///./newsletters.db")


def create_database_engine(database_url: str = None):
    """Create async database engine."""
    if database_url is None:
        database_url = get_database_url()

    return create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        future=True,
        pool_pre_ping=True,  # Validate connections before use
        pool_recycle=3600,  # Recycle connections after 1 hour
    )


async def init_database(engine) -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_async_session():
    """Get async database session factory."""
    from backend.config import get_session_maker

    return get_session_maker()
