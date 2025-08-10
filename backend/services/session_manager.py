"""
Briefing session state management service.

This service handles the state of user briefing sessions, tracking the current
story, managing story progression, and providing detailed summaries on request.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import (
    Issue,
    ListeningSession,
    Newsletter,
    Story,
    UserSubscription,
)

logger = logging.getLogger(__name__)


class BriefingSessionManager:
    """
    Simple session state management without complex frameworks.

    Handles briefing session state including story progression, current story
    tracking, and summary retrieval for voice assistant interactions.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize session manager with database session.

        Args:
            db_session: Async SQLAlchemy session for database operations
        """
        self.db = db_session

    async def create_session(
        self, user_id: UUID, story_ids: list[UUID]
    ) -> ListeningSession:
        """
        Create a new briefing session for a user.

        Args:
            user_id: ID of the user starting the session
            story_ids: Ordered list of story IDs for the briefing

        Returns:
            Created listening session
        """
        if not story_ids:
            raise ValueError("Cannot create session without stories")

        session = ListeningSession(
            user_id=user_id,
            current_story_id=story_ids[0],
            current_story_index=0,
            session_status="playing",
            story_order=story_ids,
        )

        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)

        logger.info(
            f"Created new session {session.id} for user {user_id} with {len(story_ids)} stories"
        )
        return session

    async def get_current_story(self, session_id: UUID) -> Story | None:
        """
        Get the current story for the session.

        Args:
            session_id: ID of the listening session

        Returns:
            Current story or None if session not found
        """
        # Get session
        session = await self.db.get(ListeningSession, session_id)
        if not session or not session.current_story_id:
            logger.warning(f"Session {session_id} not found or has no current story")
            return None

        # Get current story
        current_story = await self.db.get(Story, session.current_story_id)
        if not current_story:
            logger.error(
                f"Current story {session.current_story_id} not found for session {session_id}"
            )
            return None

        return current_story

    async def advance_story(self, session_id: UUID) -> Story | None:
        """
        Move to next story in the session.

        Args:
            session_id: ID of the listening session

        Returns:
            Next story or None if at end of briefing
        """
        # Get session
        session = await self.db.get(ListeningSession, session_id)
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None

        # Check if we can advance
        next_index = session.current_story_index + 1
        if next_index >= len(session.story_order):
            # End of briefing
            session.session_status = "completed"
            await self.db.commit()
            logger.info(f"Session {session_id} completed - reached end of stories")
            return None

        # Advance to next story
        next_story_id = session.story_order[next_index]
        session.current_story_index = next_index
        session.current_story_id = next_story_id

        await self.db.commit()

        # Get next story
        next_story = await self.db.get(Story, next_story_id)
        if not next_story:
            logger.error(
                f"Next story {next_story_id} not found for session {session_id}"
            )
            return None

        logger.info(
            f"Session {session_id} advanced to story {next_index + 1}/{len(session.story_order)}: {next_story.headline}"
        )
        return next_story

    async def get_detailed_summary(self, session_id: UUID) -> str | None:
        """
        Get full text summary for current story.

        Args:
            session_id: ID of the listening session

        Returns:
            Detailed summary text or None if not available
        """
        current_story = await self.get_current_story(session_id)
        if not current_story:
            return None

        return current_story.full_text_summary

    async def get_story_metadata(self, session_id: UUID) -> dict | None:
        """
        Get metadata for the current story.

        Args:
            session_id: ID of the listening session

        Returns:
            Dictionary with story metadata or None if not available
        """
        current_story = await self.get_current_story(session_id)
        if not current_story:
            return None

        # Get issue and newsletter information
        issue = await self.db.get(Issue, current_story.issue_id)
        if not issue:
            return None

        newsletter_query = select(Newsletter).where(
            Newsletter.id == issue.newsletter_id
        )
        result = await self.db.execute(newsletter_query)
        newsletter = result.scalar_one_or_none()

        if not newsletter:
            return None

        return {
            "headline": current_story.headline,
            "newsletter_name": newsletter.name,
            "publisher": newsletter.publisher,
            "issue_date": issue.date.isoformat() if issue.date else None,
            "issue_subject": issue.subject,
            "story_url": current_story.url,
        }

    async def get_session_progress(self, session_id: UUID) -> dict | None:
        """
        Get current session progress information.

        Args:
            session_id: ID of the listening session

        Returns:
            Dictionary with progress information or None if session not found
        """
        session = await self.db.get(ListeningSession, session_id)
        if not session:
            return None

        total_stories = len(session.story_order)
        current_index = session.current_story_index

        return {
            "session_id": str(session.id),
            "current_story_index": current_index,
            "total_stories": total_stories,
            "progress_percentage": (
                round((current_index / total_stories) * 100, 1)
                if total_stories > 0
                else 0
            ),
            "session_status": session.session_status,
            "stories_remaining": (
                total_stories - current_index - 1
                if current_index < total_stories
                else 0
            ),
        }

    async def pause_session(self, session_id: UUID) -> bool:
        """
        Pause the current session.

        Args:
            session_id: ID of the listening session

        Returns:
            True if successfully paused, False otherwise
        """
        session = await self.db.get(ListeningSession, session_id)
        if not session:
            return False

        session.session_status = "paused"
        await self.db.commit()

        logger.info(f"Session {session_id} paused")
        return True

    async def resume_session(self, session_id: UUID) -> bool:
        """
        Resume a paused session.

        Args:
            session_id: ID of the listening session

        Returns:
            True if successfully resumed, False otherwise
        """
        session = await self.db.get(ListeningSession, session_id)
        if not session:
            return False

        if session.session_status == "completed":
            logger.warning(f"Cannot resume completed session {session_id}")
            return False

        session.session_status = "playing"
        await self.db.commit()

        logger.info(f"Session {session_id} resumed")
        return True

    async def get_today_stories(self, user_id: UUID) -> list[Story]:
        """
        Get today's stories for a user based on their subscriptions.

        Args:
            user_id: ID of the user

        Returns:
            List of today's stories for the user
        """
        from datetime import datetime, timedelta

        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        # This is a simplified query - in production, you'd want more sophisticated
        # logic to determine "today's" stories based on user preferences and timezones
        query = (
            select(Story)
            .join(Issue)
            .join(Newsletter)
            .join(UserSubscription)
            .where(
                UserSubscription.user_id == user_id,
                Issue.date >= yesterday,
                Issue.date < today + timedelta(days=1),
            )
            .order_by(Issue.date.desc(), Story.id)
        )

        result = await self.db.execute(query)
        stories = result.scalars().all()

        logger.info(f"Found {len(stories)} stories for user {user_id}")
        return stories
