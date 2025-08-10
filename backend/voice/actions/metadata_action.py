"""
Story Metadata action for voice briefings.

Provides information about the current story's source, publication details,
and other metadata when users ask questions like "what newsletter is this from?"
"""

import logging
from datetime import datetime

from backend.config import get_database_session
from backend.services.session_manager import BriefingSessionManager
from .base_briefing_action import BaseBriefingAction, BriefingActionInput

logger = logging.getLogger(__name__)


class MetadataAction(BaseBriefingAction):
    """
    Vocode action to provide story metadata information.
    
    This action retrieves and returns metadata about the current story
    including source newsletter, publication date, and other details.
    """
    
    def __init__(self):
        """Initialize the metadata action."""
        super().__init__(
            action_name="story_metadata",
            description="Provide information about the current story's source, publication date, and other metadata"
        )
    
    async def run(self, action_input: BriefingActionInput, conversation_id: str) -> str:
        """
        Execute story metadata action.
        
        Args:
            action_input: Action input containing session_id and optional user_query
            conversation_id: Vocode conversation ID
            
        Returns:
            Metadata information about the current story
        """
        try:
            session_id = self._extract_session_id(action_input)
            self._log_action("story_metadata", str(session_id), f"Query: {action_input.user_query}")
            
            # Get session manager with fresh database connection
            async with get_database_session() as db_session:
                session_manager = BriefingSessionManager(db_session)
                
                # Get story metadata
                metadata = await session_manager.get_story_metadata(session_id)
                if not metadata:
                    logger.warning(f"No metadata found for session {session_id}")
                    return "I don't have metadata information for the current story. Let me continue with your briefing."
                
                # Format the response based on what was asked
                user_query = (action_input.user_query or "").lower()
                
                if any(word in user_query for word in ["newsletter", "source", "from"]):
                    # User asked about the newsletter source
                    response = f"This story is from {metadata['newsletter_name']}"
                    if metadata.get('publisher'):
                        response += f", published by {metadata['publisher']}"
                    response += "."
                
                elif any(word in user_query for word in ["when", "date", "published"]):
                    # User asked about publication date
                    if metadata.get('issue_date'):
                        try:
                            date_obj = datetime.fromisoformat(metadata['issue_date'].replace('Z', '+00:00'))
                            formatted_date = date_obj.strftime("%B %d, %Y")
                            response = f"This story was published on {formatted_date}."
                        except ValueError:
                            response = f"This story was published on {metadata['issue_date']}."
                    else:
                        response = "I don't have the publication date for this story."
                
                elif any(word in user_query for word in ["headline", "title"]):
                    # User asked about the headline
                    response = f"The headline is: {metadata['headline']}"
                
                elif any(word in user_query for word in ["subject", "issue"]):
                    # User asked about the issue subject
                    if metadata.get('issue_subject'):
                        response = f"This is from the issue titled: {metadata['issue_subject']}"
                    else:
                        response = "I don't have the issue subject information."
                
                else:
                    # General metadata request - provide comprehensive info
                    response = f"This story is from {metadata['newsletter_name']}"
                    
                    if metadata.get('publisher'):
                        response += f", published by {metadata['publisher']}"
                    
                    if metadata.get('issue_date'):
                        try:
                            date_obj = datetime.fromisoformat(metadata['issue_date'].replace('Z', '+00:00'))
                            formatted_date = date_obj.strftime("%B %d, %Y")
                            response += f", from {formatted_date}"
                        except ValueError:
                            response += f", from {metadata['issue_date']}"
                    
                    if metadata.get('issue_subject'):
                        response += f". The issue was titled: {metadata['issue_subject']}"
                    
                    response += "."
                
                logger.info(f"Provided metadata for story in session {session_id}")
                return response
            
        except Exception as e:
            return self._handle_action_error(e, action_input.session_id)