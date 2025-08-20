## Purpose
Complete implementation of an AI-powered voice assistant that delivers daily newsletter briefings with real-time interruption capability, conversational interaction, and dynamic content processing.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Build a complete AI voice assistant system that delivers personalized daily newsletter briefings with:
- Real-time voice interruption and conversation capability
- Dynamic story summarization (brief → detailed on request)
- Gmail newsletter ingestion and processing
- Audio pre-processing for efficient streaming
- Vocode conversational AI agent with phrase-triggered actions
- Clean, minimalistic React Native mobile interface

## Why
- **User Value**: Transform lengthy newsletter reading into efficient, interactive audio briefings
- **Conversational Experience**: Enable natural interruption and follow-up questions during briefings
- **Efficiency**: Pre-processed audio eliminates real-time TTS latency for smooth listening
- **Personalization**: Curated content from user's actual newsletter subscriptions
- **Modern UX**: Voice-first interface with intelligent pause/resume and context awareness

## What
Interactive voice assistant mobile app that:
1. Authenticates with user's Gmail to extract newsletters
2. Processes newsletter content into structured stories with summaries
3. Pre-generates audio for all content using ElevenLabs TTS
4. Delivers personalized daily briefings with voice control
5. Handles real-time interruptions with intelligent intent recognition
6. Provides conversational responses using Vocode agents with actions
7. Maintains session state for seamless briefing experience

### Success Criteria
- [ ] User can authenticate with Gmail and newsletters are automatically ingested
- [ ] Daily briefings are generated with one-sentence summaries for each story
- [ ] User can interrupt briefing at any time with voice commands
- [ ] AI correctly interprets user intent ("skip", "tell me more", questions)
- [ ] Audio pre-processing job converts all text to speech and stores in cloud
- [ ] Real-time conversation flows seamlessly without blocking or delays
- [ ] Session state is maintained across interruptions and resume
- [ ] React Native app provides clean, voice-first user interface

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
  
- url: https://elevenlabs.io/docs/api-reference/streaming
  why: Real-time TTS streaming and audio processing
  
- url: https://elevenlabs.io/docs/cookbooks/text-to-speech/streaming
  why: Python streaming implementation patterns
  
- url: https://docs.vocode.dev/
  why: Real-time voice conversation setup and STT/TTS integration.
  
- url: https://supabase.com/docs
  why: PostgreSQL setup, authentication, and real-time subscriptions
  
- url: https://developers.google.com/gmail/api/guides
  why: OAuth 2.0 authentication and email parsing
  
- url: https://quart.palletsprojects.com/en/latest/
  why: Async API endpoint patterns and native WebSocket support
  
- url: https://flask.palletsprojects.com/
  why: Reference for Flask patterns (Quart is Flask-compatible)
  
- file: examples/db-schema.md
  why: Database structure for users, newsletters, stories, sessions
  
- file: examples/interrupt_handling_flow.md
  why: State machine for briefing → listening → briefing transitions
  
- file: examples/agent-tools.md
  why: Tool definitions for skip, tell-me-more, conversational query
  
- file: examples/sample_conversations.json
  why: Expected conversation patterns and response formats
  
- file: examples/audio-processing-job.md
  why: Background job flow for TTS and cloud storage

- docfile: CLAUDE.md
  why: Project rules, testing patterns, code structure requirements

- url: https://docs.vocode.dev/open-source/agents-with-actions
  why: Vocode agent actions for tool calling and interrupt handling
  
- url: https://docs.vocode.dev/open-source/action-phrase-triggers
  why: Phrase triggers for voice commands (skip, tell me more)
  
- url: https://docs.vocode.dev/open-source/external-action
  why: External actions for database and API integration

  - url: https://docs.vocode.dev/open-source/create-your-own-agent
  why: Creating an agent in vocode.

  - url: https://docs.vocode.dev/open-source/agent-factory
  why: More information on creating an agent in vocode.
```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase
```bash
my-newsletters/
├── CLAUDE.md
├── INITIAL.md
├── LICENSE
├── PRPs/
│   ├── EXAMPLE_multi_agent_prp.md
│   └── templates/
│       └── prp_base.md
├── README.md
├── examples/
│   ├── agent-tools.md
│   ├── audio-processing-job.md
│   ├── db-schema.md
│   ├── interrupt_handling_flow.md
│   └── sample_conversations.json
└── myenv/
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
my-newsletters/
├── backend/
│   ├── __init__.py
│   ├── main.py                           # Quart app entry point, async API routes
│   ├── config.py                         # Configuration management (DB, APIs)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── database.py                   # SQLAlchemy ORM models for Supabase
│   │   └── schemas.py                    # Pydantic models for API validation
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gmail_service.py              # Gmail API integration, OAuth flow
│   │   ├── newsletter_parser.py          # Extract and parse newsletter content
│   │   ├── audio_service.py              # ElevenLabs TTS integration
│   │   └── storage_service.py            # Cloud storage for audio files
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gmail_service.py              # Gmail API integration, OAuth flow
│   │   ├── newsletter_parser.py          # Extract and parse newsletter content
│   │   ├── audio_service.py              # ElevenLabs TTS integration
│   │   ├── storage_service.py            # Cloud storage for audio files
│   │   └── session_manager.py            # Briefing session state management
│   ├── voice/
│   │   ├── __init__.py
│   │   ├── conversation_manager.py       # Vocode conversation setup and management
│   │   ├── actions/
│   │   │   ├── __init__.py
│   │   │   ├── skip_story_action.py      # Skip story voice action
│   │   │   ├── tell_more_action.py       # Tell me more voice action
│   │   │   ├── metadata_action.py        # Story metadata voice action
│   │   │   └── base_briefing_action.py   # Base class for briefing actions
│   │   └── agent_config.py               # Vocode agent configuration
│   ├── jobs/
│   │   ├── __init__.py
│   │   └── audio_processing.py           # Background job for TTS pre-processing
│   └── utils/
│       ├── __init__.py
│       ├── auth.py                       # JWT and OAuth utilities
│       └── helpers.py                    # Common utility functions
├── frontend/
│   ├── App.tsx                           # Main React Native app
│   ├── package.json                      # React Native dependencies
│   ├── components/
│   │   ├── VoiceInterface.tsx            # Voice recording/playback component
│   │   ├── BriefingPlayer.tsx            # Audio briefing player
│   │   └── AuthScreen.tsx                # Gmail authentication UI
│   ├── services/
│   │   ├── api.ts                        # Backend API client
│   │   ├── audio.ts                      # Audio recording/playback service
│   │   └── auth.ts                       # Authentication service
│   └── utils/
│       └── constants.ts                  # App constants and config
├── tests/
│   ├── test_gmail_service.py
│   ├── test_newsletter_parser.py
│   ├── test_audio_service.py
│   ├── test_vocode_actions.py
│   └── conftest.py                       # Pytest configuration
├── pyproject.toml                        # Python dependencies and project config
├── .env.example                          # Environment variables template
└── requirements.txt                      # Python dependencies (generated)
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Vocode actions system for all agent functionality
# Example: Use BaseAction classes for skip, tell-me-more, metadata tools
# Example: Phrase triggers enable natural voice commands with flexible matching

# CRITICAL: ElevenLabs streaming requires chunked processing
# Example: Use client.text_to_speech.stream() for real-time audio
# Example: optimize_streaming_latency parameter (0-4) balances quality vs speed

# CRITICAL: Vocode external actions for database integration
# Example: External actions can call your Quart API for database operations
# Example: Actions handle session state updates and story retrieval

# CRITICAL: Simple session management outside Vocode
# Example: BriefingSessionManager class handles all briefing state
# Example: Pass session_id to actions for state coordination

# CRITICAL: Supabase requires connection pooling for performance
# Example: Use asyncpg with connection pools for concurrent operations

# CRITICAL: Gmail API has strict rate limits and OAuth flow
# Example: Implement exponential backoff for rate limiting
# Example: Refresh tokens expire and need rotation handling

# CRITICAL: React Native audio requires platform-specific setup
# Example: Use react-native-audio-recorder-player v4.x with NitroModules
# Example: Implement loading states for background processing

# CRITICAL: Use Quart for full async support throughout the application
# Example: Quart provides native async/await and WebSocket support
# Example: All routes and handlers should be async for voice latency requirements

# CRITICAL: We use Python 3.13, pydantic v2, and async/await patterns
# Example: All new code should be async-first for voice latency requirements
```

## Implementation Blueprint

### Data models and structure

Create the core data models to ensure type safety and consistency.
```python
# SQLAlchemy ORM Models (database.py)
class User(Base):
    id: UUID
    email: str
    name: str
    default_voice_type: str
    default_playback_speed: float

class Newsletter(Base):
    id: UUID
    name: str
    publisher: str
    description: str

class Story(Base):
    id: UUID
    issue_id: UUID
    headline: str
    one_sentence_summary: str
    full_text_summary: str
    audio_url: str  # Pre-generated audio file URL

class ListeningSession(Base):
    id: UUID
    user_id: UUID
    current_story_id: UUID
    current_story_index: int
    session_status: str  # 'playing', 'paused', 'completed'
    story_order: List[UUID]  # Array of story IDs

# Pydantic Schemas (schemas.py)
class BriefingRequest(BaseModel):
    user_id: UUID
    voice_type: Optional[str] = None

class VoiceActionInput(BaseModel):
    session_id: UUID
    action_type: str  # 'skip', 'tell_more', 'metadata'

class ActionResult(BaseModel):
    action: str  # 'skip', 'tell_more', 'metadata'
    message: str
    next_story_id: Optional[UUID] = None
    
class SessionStateUpdate(BaseModel):
    session_id: UUID
    current_story_id: UUID
    current_story_index: int
```

### list of tasks to be completed to fullfill the PRP in the order they should be completed

```yaml
Task 1: Project Setup and Dependencies
CREATE pyproject.toml:
  - INCLUDE: Python 3.13, Quart, SQLAlchemy, asyncpg, elevenlabs, vocode
  - INCLUDE: pydantic v2, python-dotenv, pytest, black, ruff, mypy
  - INCLUDE: quart-cors for CORS support, asyncio for concurrent processing
  - FOLLOW: CLAUDE.md dependency patterns

CREATE .env.example:
  - INCLUDE: Database connection, API keys, OAuth secrets
  - PATTERN: Use descriptive variable names with defaults

Task 2: Database Models and Configuration
CREATE backend/models/database.py:
  - MIRROR: examples/db-schema.md table structure
  - USE: SQLAlchemy async patterns with UUID primary keys
  - INCLUDE: Relationships between users, newsletters, stories, sessions

CREATE backend/config.py:
  - PATTERN: python-dotenv with load_dotenv()
  - INCLUDE: Supabase connection, API keys, environment validation

Task 3: Gmail Integration Service
CREATE backend/services/gmail_service.py:
  - IMPLEMENT: OAuth 2.0 flow with token refresh
  - INCLUDE: Newsletter search and email parsing
  - ERROR HANDLING: Rate limiting with exponential backoff
  - PATTERN: Async/await throughout, connection pooling

CREATE backend/services/newsletter_parser.py:
  - IMPLEMENT: HTML email parsing and story extraction
  - USE: BeautifulSoup or similar for content extraction
  - INCLUDE: AI-powered story separation using OpenAI API

Task 4: Audio Processing Service
CREATE backend/services/audio_service.py:
  - IMPLEMENT: ElevenLabs streaming integration
  - USE: client.text_to_speech.stream() with optimize_streaming_latency
  - INCLUDE: Audio format handling (MP3, PCM)
  - ERROR HANDLING: TTS failures and retry logic

CREATE backend/services/storage_service.py:
  - IMPLEMENT: Cloud storage for audio files (Supabase Storage)
  - PATTERN: Async upload/download with progress tracking
  - INCLUDE: URL generation and file management

Task 5: Background Audio Processing Job
CREATE backend/jobs/audio_processing.py:
  - MIRROR: examples/audio-processing-job.md flow
  - IMPLEMENT: Fetch stories without audio, convert with TTS, upload
  - USE: Async task queue or simple cron-like scheduler
  - INCLUDE: Error handling and retry logic

Task 6: Session State Management
CREATE backend/services/session_manager.py:
  - IMPLEMENT: BriefingSessionManager class for session state
  - INCLUDE: get_current_story, advance_story, get_detailed_summary methods
  - PATTERN: Simple async database operations without complex state management
  - USE: Direct Supabase queries for session updates

Task 7: Vocode Actions Implementation
CREATE backend/voice/actions/base_briefing_action.py:
  - IMPLEMENT: Base class for all briefing actions
  - INCLUDE: Session manager integration and common utilities
  - PATTERN: Shared session_id handling across all actions

CREATE backend/voice/actions/skip_story_action.py:
  - MIRROR: examples/agent-tools.md Skip Story Tool definition
  - IMPLEMENT: Phrase triggers for "skip", "next", "move on"
  - USE: External action pattern to call session manager
  - INCLUDE: Database update to advance story index

CREATE backend/voice/actions/tell_more_action.py:
  - MIRROR: examples/agent-tools.md Tell Me More Tool definition
  - IMPLEMENT: Phrase triggers for "tell me more", "go deeper", "full story"
  - USE: External action to retrieve detailed summary
  - INCLUDE: Return full text for TTS synthesis

CREATE backend/voice/actions/metadata_action.py:
  - MIRROR: examples/agent-tools.md Story Metadata Tool definition
  - IMPLEMENT: Phrase triggers for "what newsletter", "when published"
  - USE: Fast database retrieval for story metadata
  - INCLUDE: Direct factual responses

Task 8: Vocode Conversation Setup
CREATE backend/voice/conversation_manager.py:
  - IMPLEMENT: Vocode StreamingConversation setup and management
  - INCLUDE: ChatGPT agent configuration with all actions
  - INCLUDE: STT/TTS provider configuration (ElevenLabs integration)
  - PATTERN: Conversation lifecycle with phrase-triggered interruptions

CREATE backend/voice/agent_config.py:
  - IMPLEMENT: Vocode agent configuration with all actions
  - INCLUDE: ChatGPT agent setup with phrase triggers
  - PATTERN: Action registration and trigger phrase configuration

Task 9: Quart API Layer
CREATE backend/main.py:
  - IMPLEMENT: Quart app with async API routes
  - INCLUDE: /start-briefing, /voice-stream WebSocket endpoint
  - USE: Native async/await throughout all routes
  - INTEGRATE: Vocode conversation manager with actions
  - PATTERN: WebSocket lifecycle management for voice sessions

Task 10: React Native Frontend Core
CREATE frontend/App.tsx:
  - IMPLEMENT: Main app structure with navigation
  - USE: React Native 2025 patterns
  - INCLUDE: Authentication flow and voice interface

CREATE frontend/components/VoiceInterface.tsx:
  - USE: react-native-audio-recorder-player v4.x with NitroModules
  - IMPLEMENT: Voice recording with intelligent voice detection
  - INCLUDE: Real-time audio visualization
  - PATTERN: Loading states for background processing

CREATE frontend/components/BriefingPlayer.tsx:
  - IMPLEMENT: Audio playback with pause/resume
  - INCLUDE: Story navigation and progress tracking
  - USE: Real-time communication with backend

Task 11: Authentication Integration
CREATE backend/utils/auth.py:
  - IMPLEMENT: JWT token management
  - INCLUDE: OAuth token refresh for Gmail
  - PATTERN: Async token validation and renewal

CREATE frontend/components/AuthScreen.tsx:
  - IMPLEMENT: Gmail OAuth flow
  - USE: React Native OAuth libraries
  - INCLUDE: Token storage and automatic refresh

Task 12: Testing Implementation
CREATE tests/ with comprehensive test suite:
  - INCLUDE: Unit tests for all services, actions, and voice integration
  - PATTERN: Mock external APIs (Gmail, ElevenLabs, Vocode)
  - USE: pytest-asyncio for async testing
  - INCLUDE: Integration tests for Vocode actions and session management
  - INCLUDE: End-to-end voice conversation flow tests
```

### Per task pseudocode as needed added to each task

```python
# Task 6: Session State Management
# Pseudocode for session_manager.py

from backend.models.database import ListeningSession, Story
from sqlalchemy.ext.asyncio import AsyncSession

class BriefingSessionManager:
    """Simple session state management without complex frameworks"""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_current_story(self, session_id: str) -> Story:
        """Get the current story for the session"""
        # PATTERN: Simple database query for current story
        session = await self.db.get(ListeningSession, session_id)
        current_story = await self.db.get(Story, session.current_story_id)
        return current_story
    
    async def advance_story(self, session_id: str) -> Story:
        """Move to next story in the session"""
        # CRITICAL: Update session state and return next story
        session = await self.db.get(ListeningSession, session_id)
        session.current_story_index += 1
        
        if session.current_story_index < len(session.story_order):
            next_story_id = session.story_order[session.current_story_index]
            session.current_story_id = next_story_id
            await self.db.commit()
            return await self.db.get(Story, next_story_id)
        else:
            # End of briefing
            session.session_status = 'completed'
            await self.db.commit()
            return None
    
    async def get_detailed_summary(self, session_id: str) -> str:
        """Get full text summary for current story"""
        current_story = await self.get_current_story(session_id)
        return current_story.full_text_summary

# Task 4: Audio Processing Service
# Pseudocode for audio_service.py

from elevenlabs import ElevenLabs
import asyncio

async def generate_audio_stream(text: str, voice_id: str) -> bytes:
    """Generate streaming audio using ElevenLabs"""
    client = ElevenLabs()
    
    # CRITICAL: Use streaming for real-time performance
    audio_stream = client.text_to_speech.stream(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
        # GOTCHA: Balance quality vs latency
        optimize_streaming_latency=2  # 0-4 scale
    )
    
    # PATTERN: Collect chunks into complete audio
    audio_chunks = []
    async for chunk in audio_stream:
        if isinstance(chunk, bytes):
            audio_chunks.append(chunk)
    
    return b''.join(audio_chunks)

# Task 9: Quart API Layer
# Pseudocode for main.py

from quart import Quart, request, jsonify, websocket
from quart_cors import cors
from vocode.streaming.streaming_conversation import StreamingConversation
from backend.voice.conversation_manager import ConversationManager

app = Quart(__name__)
app = cors(app, allow_origin="*")

@app.route('/start-briefing', methods=['POST'])
async def start_briefing():
    """Initialize daily briefing session"""
    # PATTERN: Validate input with Pydantic
    data = await request.get_json()
    request_data = BriefingRequest(**data)
    
    # CRITICAL: Create session state in database
    session = await create_listening_session(request_data.user_id)
    
    # GOTCHA: Return session ID for real-time communication
    return jsonify({"session_id": session.id, "first_story": session.story_order[0]})

@app.websocket('/voice-stream/<session_id>')
async def voice_stream(session_id):
    """Handle real-time voice communication with Vocode actions"""
    # CRITICAL: Initialize Vocode conversation with actions
    conversation_manager = ConversationManager(session_id)
    conversation = await conversation_manager.create_conversation()
    
    # PATTERN: Simple Vocode conversation with phrase-triggered actions
    # Actions automatically handle database operations and session state
    await conversation.start()

# Task 7: Vocode Actions Implementation
# Pseudocode for skip_story_action.py

from vocode.streaming.action.base_action import BaseAction
from backend.services.session_manager import BriefingSessionManager

class SkipStoryAction(BaseAction):
    """Vocode action to skip current story and advance to next"""
    
    description: str = "Skip the current newsletter story and move to the next one"
    
    def __init__(self, session_manager: BriefingSessionManager):
        super().__init__()
        self.session_manager = session_manager
    
    async def run(self, action_input, conversation_id: str) -> str:
        """Execute skip story action"""
        # PATTERN: Extract session_id from conversation context
        session_id = action_input.get("session_id")
        
        # CRITICAL: Use session manager to advance story
        next_story = await self.session_manager.advance_story(session_id)
        
        if next_story:
            # GOTCHA: Return next story summary for immediate TTS
            return f"Skipping this story. Next up: {next_story.headline}. {next_story.one_sentence_summary}"
        else:
            return "That was the last story in your briefing. Have a great day!"

# Pseudocode for tell_more_action.py

class TellMeMoreAction(BaseAction):
    """Vocode action to provide detailed story summary"""
    
    description: str = "Provide a detailed summary of the current newsletter story"
    
    async def run(self, action_input, conversation_id: str) -> str:
        """Execute tell me more action"""
        session_id = action_input.get("session_id")
        
        # CRITICAL: Get detailed summary from session manager
        detailed_summary = await self.session_manager.get_detailed_summary(session_id)
        
        # PATTERN: Return full content for TTS
        return f"Here's the full story: {detailed_summary}"

# Pseudocode for agent_config.py

from vocode.streaming.agent.chat_gpt_agent import ChatGPTAgent
from vocode.streaming.action.phrase_based_action_trigger import PhraseBasedActionTrigger

def create_briefing_agent(session_id: str) -> ChatGPTAgent:
    """Create Vocode ChatGPT agent with all briefing actions"""
    
    # CRITICAL: Configure all actions with phrase triggers
    skip_action = SkipStoryAction(session_manager)
    skip_trigger = PhraseBasedActionTrigger(
        phrase_triggers=[
            PhraseTrigger(phrase="skip", condition="phrase_condition_type_contains"),
            PhraseTrigger(phrase="next", condition="phrase_condition_type_contains"),
            PhraseTrigger(phrase="move on", condition="phrase_condition_type_contains")
        ]
    )
    
    tell_more_action = TellMeMoreAction(session_manager)
    tell_more_trigger = PhraseBasedActionTrigger(
        phrase_triggers=[
            PhraseTrigger(phrase="tell me more", condition="phrase_condition_type_contains"),
            PhraseTrigger(phrase="go deeper", condition="phrase_condition_type_contains"),
            PhraseTrigger(phrase="full story", condition="phrase_condition_type_contains")
        ]
    )
    
    # PATTERN: ChatGPT agent handles conversational queries naturally
    agent = ChatGPTAgent(
        actions=[
            (skip_action, skip_trigger),
            (tell_more_action, tell_more_trigger),
            (metadata_action, metadata_trigger)
        ]
    )
    
    return agent
```

### Integration Points
```yaml
DATABASE:
  - setup: Supabase PostgreSQL with connection pooling
  - migrations: "Use Supabase CLI for schema management"
  - realtime: "Enable real-time subscriptions for session updates"
  
CONFIG:
  - add to: backend/config.py
  - pattern: "SUPABASE_URL = os.getenv('SUPABASE_URL')"
  - include: "Gmail OAuth, ElevenLabs API, cloud storage credentials"
  
AUTHENTICATION:
  - gmail: "OAuth 2.0 flow with refresh token rotation"
  - jwt: "Session tokens for mobile app authentication"
  - supabase: "User management and Row Level Security"
  
REAL_TIME:
  - websockets: "Quart native WebSocket for voice communication"
  - streaming: "ElevenLabs + Vocode coordinated audio streaming"
  - persistence: "Simple database session state management"
  - actions: "Vocode phrase-triggered actions for all interruptions"

VOICE_PROCESSING:
  - frontend: "react-native-audio-recorder-player for recording"
  - backend: "Vocode handles real-time STT/TTS streaming"
  - actions: "Vocode BaseAction classes handle all interrupt processing"
  - ai: "ChatGPT agent processes conversational queries naturally"
  - state: "BriefingSessionManager coordinates session state across actions"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
uv run ruff check backend/ --fix       # Auto-fix what's possible
uv run mypy backend/                    # Type checking
uv run black backend/                   # Code formatting

# Expected: No errors. If errors, READ the error and fix.

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```python
# For example, CREATE test_vocode_actions.py would contain test cases such as:
async def test_skip_story_action():
    """Skip action correctly advances session state"""
    skip_action = SkipStoryAction(session_manager)
    result = await skip_action.run({"session_id": "test-session"}, "conv-123")
    assert "skipping" in result.lower()
    assert "next up" in result.lower()

async def test_audio_streaming():
    """ElevenLabs streaming produces valid audio"""
    audio = await generate_audio_stream("Test message", "test_voice_id")
    assert isinstance(audio, bytes)
    assert len(audio) > 0
```

```bash
# Run and iterate until passing:
uv run pytest tests/ -v --asyncio-mode=auto
# If failing: Read error, understand root cause, fix code, re-run (never mock to pass)
```

### Level 3: Integration Test
```bash
# Start the Quart application
uv run python -m backend.main

# Test the complete flow
curl -X POST http://localhost:5001/start-briefing \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test-uuid"}'

# Test WebSocket voice stream
# Use WebSocket client to connect to /voice-stream/{session_id}
# Send audio data and verify agent responses

# Expected: Session created, voice streaming works, agent responds
# If error: Check logs for Vocode action integration issues
```

## Final validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v --asyncio-mode=auto`
- [ ] No linting errors: `uv run ruff check backend/`
- [ ] No type errors: `uv run mypy backend/`
- [ ] Gmail OAuth flow works: Authentication and newsletter fetching
- [ ] Audio processing job runs: TTS generation and cloud storage
- [ ] Agent interruption works: Real-time voice command processing
- [ ] React Native app builds: Frontend compilation and device testing
- [ ] End-to-end briefing: Complete user journey from login to briefing
- [ ] Voice quality acceptable: Audio clarity and streaming performance
- [ ] Error cases handled gracefully: Network failures, API errors, edge cases
- [ ] Documentation updated: README with setup instructions

---

## Anti-Patterns to Avoid
- ❌ Don't use sync functions in async voice processing context
- ❌ Don't skip audio pre-processing - real-time TTS causes unacceptable latency
- ❌ Don't ignore Gmail API rate limits - implement proper backoff
- ❌ Don't block UI thread in React Native - use background processing
- ❌ Don't hardcode voice settings - make them user-configurable
- ❌ Don't lose session state on interrupts - use database persistence
- ❌ Don't mix sync/async patterns - Quart enables full async throughout
- ❌ Don't overcomplicate action handling - use Vocode's native phrase triggers
- ❌ Don't ignore session state coordination - pass session_id to all actions
- ❌ Don't skip error handling for external APIs - they will fail

## CRITICAL SUCCESS FACTORS

1. **Audio Latency**: Pre-processing is essential for real-time feel
2. **Interrupt Handling**: Must be seamless and preserve context
3. **Session State**: Simple database state management prevents conversation loss
4. **Voice Quality**: ElevenLabs streaming with optimal settings
5. **Mobile Performance**: React Native async patterns and loading states
6. **API Reliability**: Robust error handling and retry logic for all external services
7. **Phrase Triggers**: Natural voice command recognition via Vocode phrase matching
8. **Action Coordination**: Session state synchronized across all Vocode actions