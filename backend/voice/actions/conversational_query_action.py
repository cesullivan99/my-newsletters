"""
Conversational Query action for voice briefings.

Handles complex user questions about stories using AI/LLM processing
to provide context-aware, intelligent responses during briefings.
"""

import logging

import openai
from openai import AsyncOpenAI

from backend.config import get_database_session, settings
from backend.services.session_manager import BriefingSessionManager

from .base_briefing_action import BaseBriefingAction, BriefingActionInput

logger = logging.getLogger(__name__)


class ConversationalQueryAction(BaseBriefingAction):
    """
    Vocode action for dynamic AI-powered responses to user queries.

    This action uses an LLM to provide intelligent, context-aware answers
    to complex questions about the current story or related topics.
    """

    def __init__(self):
        """Initialize the conversational query action."""
        super().__init__(
            action_name="conversational_query",
            description="Handle complex questions about stories using AI-powered responses with full context",
        )
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def run(self, action_input: BriefingActionInput, conversation_id: str) -> str:
        """
        Execute conversational query action.

        Args:
            action_input: Action input containing session_id and user_query
            conversation_id: Vocode conversation ID

        Returns:
            AI-generated response to the user's question
        """
        try:
            session_id = self._extract_session_id(action_input)
            user_query = action_input.user_query or "Can you tell me more about this?"

            self._log_action(
                "conversational_query", str(session_id), f"Query: {user_query}"
            )

            # Get session manager with fresh database connection
            async with get_database_session() as db_session:
                session_manager = BriefingSessionManager(db_session)

                # Get current story and metadata
                current_story = await session_manager.get_current_story(session_id)
                if not current_story:
                    return "I don't have a current story to answer questions about. Let me continue with your briefing."

                metadata = await session_manager.get_story_metadata(session_id)

                # Build context for the LLM
                story_context = self._build_story_context(
                    current_story, metadata, user_query
                )

                # Get AI response
                ai_response = await self._get_ai_response(story_context, user_query)

                # Format response for voice
                response = ai_response
                if not response.endswith(("?", ".", "!")):
                    response += "."

                # Add transition back to briefing if appropriate
                if len(response) > 200:  # For longer responses, add explicit transition
                    response += " Would you like me to continue with the next story?"

                logger.info(f"Generated AI response for query in session {session_id}")
                return response

        except Exception as e:
            logger.error(f"Error in conversational query: {e}")
            return "I'm having trouble processing your question right now. Let me continue with your briefing."

    def _build_story_context(
        self, story, metadata: dict | None, user_query: str
    ) -> str:
        """
        Build comprehensive context for the LLM prompt.

        Args:
            story: Current story object
            metadata: Story metadata dictionary
            user_query: User's question

        Returns:
            Formatted context string
        """
        context_parts = []

        # Story content
        context_parts.append(f"HEADLINE: {story.headline}")
        context_parts.append(f"BRIEF SUMMARY: {story.one_sentence_summary}")

        if story.full_text_summary:
            context_parts.append(f"DETAILED SUMMARY: {story.full_text_summary}")

        # Metadata context
        if metadata:
            context_parts.append(
                f"SOURCE: {metadata.get('newsletter_name', 'Unknown Newsletter')}"
            )
            if metadata.get("publisher"):
                context_parts.append(f"PUBLISHER: {metadata['publisher']}")
            if metadata.get("issue_date"):
                context_parts.append(f"PUBLISHED: {metadata['issue_date']}")
            if metadata.get("issue_subject"):
                context_parts.append(f"ISSUE TITLE: {metadata['issue_subject']}")

        return "\n".join(context_parts)

    async def _get_ai_response(self, story_context: str, user_query: str) -> str:
        """
        Get AI response using OpenAI API.

        Args:
            story_context: Full story context
            user_query: User's question

        Returns:
            AI-generated response
        """
        system_prompt = """You are an AI assistant helping users understand newsletter stories during an audio briefing. 

Your role is to:
- Answer questions about the current story with accuracy and clarity
- Provide relevant context and explanations
- Keep responses concise but informative (ideally 1-3 sentences)
- Speak naturally as if in a conversation
- Stay focused on the story content provided

Guidelines:
- If asked about external context, provide what you know but acknowledge limitations
- If the question can't be answered from the story content, say so honestly
- Keep the tone conversational and helpful
- Don't make up facts not present in the story"""

        user_prompt = f"""Story Context:
{story_context}

User Question: {user_query}

Please provide a helpful, accurate response to the user's question based on the story context above. Keep it conversational and concise."""

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Use cost-effective model for quick responses
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=200,  # Keep responses concise for voice
                temperature=0.7,  # Balanced creativity and consistency
            )

            return response.choices[0].message.content.strip()

        except openai.RateLimitError:
            logger.warning("OpenAI rate limit exceeded")
            return "I'm experiencing high demand right now. Let me continue with your briefing instead."
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return "I'm having trouble accessing my knowledge right now. Let me continue with your briefing."
        except Exception as e:
            logger.error(f"Unexpected error in AI response: {e}")
            return "I couldn't process your question right now. Let me continue with your briefing."
