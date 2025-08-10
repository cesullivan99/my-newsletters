"""
Skip Story action for voice briefings.

Allows users to skip the current story and advance to the next one
using natural voice commands like "skip", "next", or "move on".
"""

import logging
from typing import Optional

from backend.config import get_database_session
from backend.services.session_manager import BriefingSessionManager
from .base_briefing_action import BaseBriefingAction, BriefingActionInput

logger = logging.getLogger(__name__)


class SkipStoryAction(BaseBriefingAction):
    """
    Vocode action to skip current story and advance to next.
    
    This action handles phrase triggers for skipping content and updates
    the session state to move to the next story in the briefing.
    """
    
    def __init__(self):
        """Initialize the skip story action."""
        super().__init__(
            action_name="skip_story",
            description="Skip the current newsletter story and move to the next one"
        )
    
    async def run(self, action_input: BriefingActionInput, conversation_id: str) -> str:
        """
        Execute skip story action.
        
        Args:
            action_input: Action input containing session_id
            conversation_id: Vocode conversation ID
            
        Returns:
            Response text to announce the next story or end of briefing
        """
        try:
            session_id = self._extract_session_id(action_input)
            self._log_action("skip_story", str(session_id))
            
            # Get session manager with fresh database connection
            async with get_database_session() as db_session:
                session_manager = BriefingSessionManager(db_session)
                
                # Advance to next story
                next_story = await session_manager.advance_story(session_id)
                
                if next_story:
                    # Get progress info for context
                    progress = await session_manager.get_session_progress(session_id)
                    remaining = progress.get("stories_remaining", 0) if progress else 0
                    
                    # Return next story summary for immediate TTS
                    response = f"Skipping to the next story. {next_story.headline}. {next_story.one_sentence_summary}"
                    
                    if remaining > 0:
                        response += f" That's {remaining} more stories after this one."
                    
                    logger.info(f"Session {session_id} skipped to story: {next_story.headline}")
                    return response
                else:
                    # End of briefing
                    logger.info(f"Session {session_id} completed - no more stories")
                    return "That was the last story in your briefing. Hope you have a great day! Your newsletter briefing is complete."
            
        except Exception as e:
            return self._handle_action_error(e, action_input.session_id)