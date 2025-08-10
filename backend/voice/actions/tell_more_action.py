"""
Tell Me More action for voice briefings.

Provides detailed summaries of the current story when users request
more information using phrases like "tell me more", "go deeper", etc.
"""

import logging

from backend.config import get_database_session
from backend.services.session_manager import BriefingSessionManager
from .base_briefing_action import BaseBriefingAction, BriefingActionInput

logger = logging.getLogger(__name__)


class TellMeMoreAction(BaseBriefingAction):
    """
    Vocode action to provide detailed story summary.
    
    This action retrieves and returns the full text summary of the current
    story when users want more detailed information.
    """
    
    def __init__(self):
        """Initialize the tell me more action."""
        super().__init__(
            action_name="tell_me_more",
            description="Provide a detailed summary of the current newsletter story"
        )
    
    async def run(self, action_input: BriefingActionInput, conversation_id: str) -> str:
        """
        Execute tell me more action.
        
        Args:
            action_input: Action input containing session_id
            conversation_id: Vocode conversation ID
            
        Returns:
            Detailed summary text for the current story
        """
        try:
            session_id = self._extract_session_id(action_input)
            self._log_action("tell_me_more", str(session_id))
            
            # Get session manager with fresh database connection
            async with get_database_session() as db_session:
                session_manager = BriefingSessionManager(db_session)
                
                # Get current story
                current_story = await session_manager.get_current_story(session_id)
                if not current_story:
                    logger.warning(f"No current story found for session {session_id}")
                    return "I don't seem to have a current story to tell you more about. Let me continue with your briefing."
                
                # Get detailed summary
                detailed_summary = current_story.full_text_summary
                if not detailed_summary or detailed_summary.strip() == "":
                    logger.warning(f"No detailed summary available for story {current_story.id}")
                    return "I don't have a detailed version of this story available. Let me move to the next story."
                
                # Construct response with context
                response = f"Here's the full story: {detailed_summary}"
                
                # Add transition back to briefing
                response += " Would you like me to continue with the next story, or do you have any questions about this one?"
                
                logger.info(f"Provided detailed summary for story {current_story.id} in session {session_id}")
                return response
            
        except Exception as e:
            return self._handle_action_error(e, action_input.session_id)