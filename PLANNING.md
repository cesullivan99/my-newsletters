# My Newsletters Voice Assistant - Architecture & Planning

## Project Overview
AI-powered voice assistant that delivers personalized daily newsletter briefings with real-time interruption capability, conversational interaction, and dynamic content processing.

## Architecture & Tech Stack

### Core Technologies
- **Backend**: Python 3.13 + Quart (async Flask) + SQLAlchemy
- **Database**: Supabase PostgreSQL with asyncpg driver
- **Voice Processing**: Vocode + ElevenLabs TTS streaming
- **Email Integration**: Gmail API with OAuth 2.0
- **Storage**: Supabase Storage for audio files
- **Frontend**: React Native with audio processing
- **AI**: OpenAI GPT for content processing + Vocode ChatGPT agent

### Key Architecture Decisions

#### Voice Processing Approach
- **Vocode-only architecture** (no LangChain) for real-time voice processing
- **Phrase-triggered actions** for natural voice commands (skip, tell me more)
- **Pre-processed audio** stored in cloud to eliminate TTS latency
- **Streaming TTS** with optimize_streaming_latency for real-time responses
- **Simple session management** via database (not complex state machines)

#### Data Flow
1. Gmail API fetches newsletters → Parse with BeautifulSoup + OpenAI
2. Background job generates TTS audio → Store in Supabase Storage  
3. User starts briefing → Create session with story order in database
4. Vocode handles voice stream → Actions update session state in real-time
5. React Native app manages UI state → WebSocket connection for voice

#### File Organization
```
backend/
├── models/          # Database ORM + Pydantic schemas
├── services/        # Gmail, Audio, Storage, Newsletter parsing
├── voice/           # Vocode conversation + actions
├── jobs/           # Background audio processing
└── main.py         # Quart API + WebSocket endpoints

frontend/
├── components/     # Voice interface, briefing player, auth
└── services/       # API client, audio handling
```

## Key Constraints & Patterns

### From CLAUDE.md Rules
- **500-line file limit** → Split large modules into focused components
- **Async/await throughout** → All voice processing must be non-blocking
- **Pydantic validation** → Type safety for all API schemas
- **Pytest unit tests** → Required for all new functions/classes
- **Environment variables** → Use python-dotenv with load_env()

### Voice Assistant Specific
- **No sync functions in voice context** → Blocks real-time processing  
- **Audio pre-processing essential** → Real-time TTS causes unacceptable latency
- **Session state coordination** → Pass session_id to all Vocode actions
- **Gmail rate limit handling** → Exponential backoff required
- **Mobile performance** → React Native async patterns + loading states

## Integration Points

### Database Schema (Supabase PostgreSQL)
- **Users**: Authentication + voice preferences
- **Newsletters**: Publisher metadata + categorization
- **Issues/Stories**: Parsed content + audio URLs
- **ListeningSessions**: Current briefing state + story order
- **ChatLogs**: Conversation history for context

### External APIs
- **Gmail API**: OAuth 2.0 + email parsing (rate limited)
- **ElevenLabs**: Streaming TTS + voice management
- **OpenAI**: Content summarization + story extraction
- **Supabase**: Database + file storage + real-time subscriptions

### Voice Processing Flow
1. **Briefing Mode**: Play pre-generated audio stories in sequence
2. **Interrupt Detection**: Vocode phrase triggers pause briefing
3. **Action Processing**: Skip/TellMore/Metadata actions update session
4. **Response Generation**: ChatGPT agent handles conversational queries
5. **Resume Briefing**: Continue from updated session state

## Style Conventions

### Code Patterns
- **UUID primary keys** for all database models
- **PostgresUUID(as_uuid=True)** in SQLAlchemy columns  
- **Async functions** with proper error handling
- **Google-style docstrings** for all functions
- **Relative imports** within packages
- **Type hints** throughout (mypy validation)

### Error Handling
- **Rate limiting** with exponential backoff for external APIs
- **Retry logic** for network failures and temporary errors
- **Graceful degradation** when optional services fail
- **Comprehensive logging** for debugging voice processing issues

### Testing Strategy
- **Unit tests** for all services and voice actions
- **Mock external APIs** (Gmail, ElevenLabs, OpenAI) in tests  
- **Integration tests** for complete voice conversation flows
- **pytest-asyncio** for async test execution

## Success Criteria
- Real-time voice interruption with <500ms response latency
- Natural conversation flow with phrase-triggered commands
- Seamless briefing resume after interruptions
- Pre-processed audio eliminates TTS delays
- Gmail newsletters automatically ingested daily
- React Native app provides clean voice-first UX