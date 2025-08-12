"""
Base class for all briefing actions.

Provides common functionality and session management integration
for all voice actions during newsletter briefings.
"""

import logging
from uuid import UUID

from pydantic import BaseModel, Field
from vocode.streaming.action.base_action import BaseAction
from vocode.streaming.models.actions import ActionConfig, ActionInput, ActionOutput

from backend.config import get_database_session
from backend.services.session_manager import BriefingSessionManager

logger = logging.getLogger(__name__)


class BriefingActionConfig(ActionConfig, type="action_briefing_base"):
    """Base configuration for briefing actions."""
    
    session_id: str = Field(description="ID of the active briefing session")


class BriefingActionInput(BaseModel):
    """Base input model for briefing actions."""

    session_id: str = Field(description="ID of the active briefing session")
    user_query: str | None = Field(default=None, description="Optional user query text")


class BriefingActionResponse(BaseModel):
    """Base response model for briefing actions."""
    
    message: str = Field(description="Response message to be spoken")
    success: bool = Field(default=True, description="Whether the action succeeded")


class BaseBriefingAction(BaseAction[BriefingActionConfig, BriefingActionInput, BriefingActionResponse]):
    """
    Base class for all briefing actions.

    Provides shared session_id handling and common utilities for all
    voice actions during newsletter briefings.
    """

    def __init__(self, action_config: BriefingActionConfig):
        """
        Initialize base briefing action.

        Args:
            action_config: Configuration for the action
        """
        super().__init__(action_config=action_config)
        self._session_managers = {}  # Cache session managers by session

    async def get_session_manager(self, session_id: str) -> BriefingSessionManager:
        """
        Get or create session manager for the given session.

        Args:
            session_id: ID of the briefing session

        Returns:
            BriefingSessionManager instance
        """
        if session_id not in self._session_managers:
            # Create new session manager with database session
            async with get_database_session() as db_session:
                self._session_managers[session_id] = BriefingSessionManager(db_session)

        return self._session_managers[session_id]

    async def run(self, action_input: ActionInput[BriefingActionInput]) -> ActionOutput[BriefingActionResponse]:
        """
        Execute the briefing action.

        This method should be overridden by subclasses to implement specific
        action logic.

        Args:
            action_input: Input parameters for the action

        Returns:
            ActionOutput containing the response
        """
        raise NotImplementedError("Subclasses must implement the run method")

    def _extract_session_id(self, action_input: BriefingActionInput) -> UUID:
        """
        Extract and validate session ID from action input.

        Args:
            action_input: Action input containing session_id

        Returns:
            UUID of the session

        Raises:
            ValueError: If session_id is invalid
        """
        try:
            return UUID(action_input.session_id)
        except (ValueError, TypeError) as e:
            logger.error(
                f"Invalid session_id in action input: {action_input.session_id}"
            )
            raise ValueError(f"Invalid session ID: {action_input.session_id}") from e

    def _log_action(self, action_name: str, session_id: str, details: str = "") -> None:
        """
        Log action execution for debugging and monitoring.

        Args:
            action_name: Name of the action being executed
            session_id: Session ID for the action
            details: Additional details to log
        """
        log_msg = f"Action '{action_name}' executed for session {session_id}"
        if details:
            log_msg += f" - {details}"
        logger.info(log_msg)

    def _handle_action_error(self, error: Exception, session_id: str) -> ActionOutput[BriefingActionResponse]:
        """
        Handle errors that occur during action execution.

        Args:
            error: Exception that occurred
            session_id: Session ID where error occurred

        Returns:
            ActionOutput with user-friendly error message to be spoken
        """
        logger.error(f"Action error in session {session_id}: {error}")

        # Return user-friendly error messages
        if "session" in str(error).lower():
            error_msg = "I'm having trouble accessing your briefing session. Let me try to restart it."
        elif "story" in str(error).lower():
            error_msg = "I couldn't find that story. Let me continue with the next one."
        elif "database" in str(error).lower() or "connection" in str(error).lower():
            error_msg = "I'm having a temporary connection issue. Please try again in a moment."
        else:
            error_msg = "I encountered an issue processing your request. Let me continue with your briefing."
        
        return ActionOutput(
            action_type="action_briefing_base",
            response=BriefingActionResponse(message=error_msg, success=False)
        )
