"""
Vocode agent configuration for newsletter briefing system.

Sets up ChatGPT agent with phrase-triggered actions for handling voice
interruptions during newsletter briefings.
"""

import logging

from vocode.streaming.models.actions import (
    ActionConfig,
    PhraseBasedActionTrigger,
    PhraseBasedActionTriggerConfig,
    PhraseTrigger
)
from vocode.streaming.models.agent import AgentConfig
from vocode.streaming.agent.chat_gpt_agent import ChatGPTAgentConfig

# Import our custom action configs (we'll need to create these)

logger = logging.getLogger(__name__)


class BriefingActionConfig(ActionConfig):
    """Base configuration for briefing actions."""

    session_id: str


class SkipStoryActionConfig(BriefingActionConfig, type="action_skip_story"):
    """Configuration for skip story action."""

    pass


class TellMoreActionConfig(BriefingActionConfig, type="action_tell_more"):
    """Configuration for tell me more action."""

    pass


class MetadataActionConfig(BriefingActionConfig, type="action_metadata"):
    """Configuration for metadata action."""

    pass


class ConversationalQueryActionConfig(
    BriefingActionConfig, type="action_conversational_query"
):
    """Configuration for conversational query action."""

    pass


def create_briefing_agent_config(session_id: str) -> ChatGPTAgentConfig:
    """
    Create Vocode ChatGPT agent configuration with all briefing actions.

    Args:
        session_id: ID of the active briefing session

    Returns:
        Configured ChatGPT agent with phrase-triggered actions
    """

    # Define phrase triggers for skip story action
    skip_triggers = PhraseBasedActionTrigger(
        type="action_trigger_phrase_based",
        config=PhraseBasedActionTriggerConfig(
            phrase_triggers=[
                PhraseTrigger(
                    phrase="skip", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="next", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="move on", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="skip this", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="next story", condition="phrase_condition_type_contains"
                ),
            ]
        ),
    )

    # Define phrase triggers for tell me more action
    tell_more_triggers = PhraseBasedActionTrigger(
        type="action_trigger_phrase_based",
        config=PhraseBasedActionTriggerConfig(
            phrase_triggers=[
                PhraseTrigger(
                    phrase="tell me more", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="go deeper", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="full story", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="more details", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="expand", condition="phrase_condition_type_contains"
                ),
            ]
        ),
    )

    # Define phrase triggers for metadata action
    metadata_triggers = PhraseBasedActionTrigger(
        type="action_trigger_phrase_based",
        config=PhraseBasedActionTriggerConfig(
            phrase_triggers=[
                PhraseTrigger(
                    phrase="what newsletter", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="when published", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="what source", condition="phrase_condition_type_contains"
                ),
                PhraseTrigger(
                    phrase="where is this from",
                    condition="phrase_condition_type_contains",
                ),
                PhraseTrigger(
                    phrase="publication date",
                    condition="phrase_condition_type_contains",
                ),
            ]
        ),
    )

    # System prompt for the briefing agent
    system_prompt = f"""You are a voice assistant delivering daily newsletter briefings. Your role is to:

1. Present newsletter stories clearly and engagingly
2. Handle user interruptions naturally and helpfully
3. Keep users engaged with conversational transitions
4. Provide context when switching between stories

Current session: {session_id}

When delivering a story:
- Start with a clear headline
- Provide the one-sentence summary
- Wait for user interaction before continuing to next story

When users ask questions not covered by your actions:
- Provide helpful responses based on story content
- Keep responses concise and natural
- Always offer to continue the briefing

Remember: This is a voice conversation, so speak naturally and conversationally."""

    # Create agent configuration
    agent_config = ChatGPTAgentConfig(
        system_message=system_prompt,
        model_name="gpt-4o-mini",  # Fast and cost-effective for conversation
        temperature=0.7,  # Balanced creativity and consistency
        max_tokens=150,  # Keep responses concise for voice
        actions=[
            SkipStoryActionConfig(session_id=session_id, action_trigger=skip_triggers),
            TellMoreActionConfig(
                session_id=session_id, action_trigger=tell_more_triggers
            ),
            MetadataActionConfig(
                session_id=session_id, action_trigger=metadata_triggers
            ),
            # Note: Conversational queries don't need phrase triggers
            # as they handle general questions
        ],
    )

    logger.info(f"Created briefing agent config for session {session_id}")
    return agent_config


def get_briefing_system_prompt(session_id: str, story_count: int = 0) -> str:
    """
    Get system prompt for briefing agent with dynamic context.

    Args:
        session_id: Active session ID
        story_count: Number of stories in the briefing

    Returns:
        Formatted system prompt
    """
    base_prompt = f"""You are a friendly voice assistant delivering personalized newsletter briefings.

Session: {session_id}
Stories in briefing: {story_count}

Your personality:
- Warm and conversational, like a knowledgeable friend
- Professional but not stiff
- Helpful and responsive to user needs
- Good at smooth transitions between topics

Guidelines:
- Speak naturally for voice interaction
- Keep responses concise (1-2 sentences typically)
- Ask if users want to continue or have questions
- Handle interruptions gracefully
- Provide context when jumping between stories

Available actions for user requests:
- Skip to next story (triggered by "skip", "next", etc.)
- Get more details (triggered by "tell me more", "go deeper", etc.)
- Get story metadata (triggered by "what newsletter", "when published", etc.)

For other questions, provide helpful conversational responses and offer to continue the briefing."""

    return base_prompt
