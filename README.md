# My Newsletters Voice Assistant 🎙️

An AI-powered voice assistant that delivers daily newsletter briefings with real-time interruption capability, conversational interaction, and dynamic content processing.

## 🚀 Features

- **Voice-First Experience**: Natural voice commands to control briefing playback
- **Real-Time Interruptions**: Say "skip", "tell me more", or ask questions anytime
- **Gmail Integration**: Automatically ingests newsletters from your Gmail account
- **AI-Powered Parsing**: Extracts and summarizes stories using OpenAI GPT
- **High-Quality Audio**: ElevenLabs text-to-speech with streaming optimization
- **Session Management**: Seamless pause/resume across interruptions
- **Mobile Ready**: React Native frontend for iOS and Android

## 📋 Prerequisites

### System Requirements
- **Python 3.13** (with virtual environment)
- **Node.js 18+** (for React Native frontend)
- **Rust Compiler** (required for vocode/tiktoken compatibility)

### External Services
- [Supabase](https://supabase.com) - Database and storage
- [ElevenLabs](https://elevenlabs.io) - Text-to-speech API
- [OpenAI](https://platform.openai.com) - Newsletter parsing
- [Google Cloud Console](https://console.developers.google.com) - Gmail OAuth

## 🛠️ Installation

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd my-newsletters

# Create and activate virtual environment
python3.13 -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate
```

### 2. Install Rust Compiler (Required for Vocode)

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source ~/.cargo/env
rustup default stable

# Set Python 3.13 compatibility flag
export PATH="$HOME/.cargo/bin:$PATH"
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
```

### 3. Install Python Dependencies

```bash
# Install the application
pip install -e .

# Or install manually with dependencies
pip install tiktoken==0.7.0  # Must be installed first with Rust
pip install vocode elevenlabs openai supabase
pip install quart quart-cors sqlalchemy asyncpg pydantic
pip install python-dotenv google-api-python-client google-auth-oauthlib
pip install pytest pytest-asyncio pytest-mock pytest-cov
pip install ruff black mypy
```

## 🔑 Configuration

### 1. Environment Variables

Copy the example environment file and configure:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:

```bash
# Database Configuration (Supabase)
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key-here
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key-here
DATABASE_URL=postgresql://postgres.your-ref:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# ElevenLabs API
ELEVENLABS_API_KEY=your-elevenlabs-api-key-here

# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key-here

# Gmail OAuth
GMAIL_CLIENT_ID=your-gmail-client-id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your-gmail-client-secret

# JWT Authentication
JWT_SECRET=your-strong-random-jwt-secret-here

# Application
APP_HOST=localhost
APP_PORT=5000
APP_DEBUG=true
```

### 2. API Keys Setup Guide

#### Supabase Setup
1. Go to [supabase.com](https://supabase.com) and create an account
2. Create a new project
3. Go to Settings → API to get your keys:
   - `SUPABASE_URL` - Your project URL
   - `SUPABASE_ANON_KEY` - Anonymous/public key
   - `SUPABASE_SERVICE_ROLE_KEY` - Service role key (keep secret)
4. Go to Settings → Database to get connection string for `DATABASE_URL`

#### ElevenLabs Setup
1. Sign up at [elevenlabs.io](https://elevenlabs.io)
2. Go to Profile → API Keys
3. Generate and copy your API key for `ELEVENLABS_API_KEY`

#### OpenAI Setup
1. Sign up at [platform.openai.com](https://platform.openai.com)
2. Go to API Keys section
3. Create new secret key for `OPENAI_API_KEY`

#### Gmail OAuth Setup
1. Go to [console.developers.google.com](https://console.developers.google.com)
2. Create a new project or select existing
3. Enable Gmail API
4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
5. Configure OAuth consent screen
6. Set authorized redirect URI: `http://localhost:5000/auth/google/callback`
7. Copy Client ID and Client Secret

## 🏃‍♂️ Running the Application

### Backend API Server

```bash
# Activate virtual environment and set required environment variables
source myenv/bin/activate
export PATH="$HOME/.cargo/bin:$PATH"
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Run the backend server
python -m backend.main

# Server will start at http://localhost:5000
```

### Frontend Mobile App

```bash
# Install React Native dependencies
cd frontend
npm install

# For iOS (requires macOS and Xcode)
npx react-native run-ios

# For Android (requires Android Studio and SDK)
npx react-native run-android
```

## 🧪 Testing

### Run Core Tests

```bash
# Activate environment with required flags
source myenv/bin/activate
export PATH="$HOME/.cargo/bin:$PATH"
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Run the core test suite (40 tests)
python -m pytest tests/test_minimal_auth.py tests/test_services_unit.py tests/test_schemas.py -v

# Run all tests (requires API keys for integration tests)
python -m pytest tests/ -v --asyncio-mode=auto
```

### Code Quality

```bash
# Format code
black backend/

# Check linting
ruff check backend/ --fix

# Type checking (may have external dependency warnings)
mypy backend/
```

## 📊 API Endpoints

### Authentication
- `POST /auth/gmail-oauth` - Start Gmail OAuth flow
- `GET /auth/google/callback` - OAuth callback
- `GET /auth/user` - Get current user info
- `POST /auth/refresh` - Refresh JWT token
- `POST /auth/logout` - Logout user

### Briefing
- `POST /start-briefing` - Start new briefing session
- `GET /sessions/{session_id}/progress` - Get session progress
- `POST /sessions/{session_id}/control` - Control playback (pause/resume/skip)
- `WS /voice-stream/{session_id}` - WebSocket for voice interaction

### Health
- `GET /health` - System health check

## 🎙️ Voice Commands

During a briefing, you can say:
- **"Skip"** or **"Next"** - Skip to the next story
- **"Tell me more"** - Get detailed story summary
- **"What newsletter is this from?"** - Get source information
- **"Pause"** - Pause the briefing
- **"Resume"** - Resume playback

## 🏗️ Architecture

### Backend Stack
- **Framework**: Quart (async Flask-compatible)
- **Database**: PostgreSQL via Supabase with SQLAlchemy ORM
- **Authentication**: JWT tokens with OAuth 2.0
- **Voice Processing**: Vocode with phrase-triggered actions
- **Text-to-Speech**: ElevenLabs with streaming optimization
- **Validation**: Pydantic v2 schemas

### Frontend Stack
- **Framework**: React Native with TypeScript
- **Navigation**: React Navigation
- **Audio**: react-native-audio-recorder-player
- **State Management**: React Context
- **API Communication**: WebSocket + REST

### External Integrations
- **Supabase**: Database, file storage, real-time subscriptions
- **ElevenLabs**: High-quality text-to-speech synthesis
- **OpenAI GPT**: Newsletter content parsing and summarization
- **Gmail API**: Newsletter email ingestion
- **Vocode**: Real-time voice conversation management

## 🔧 Development

### Project Structure
```
my-newsletters/
├── backend/                 # Python backend
│   ├── models/             # Database models and schemas
│   ├── services/           # Business logic services
│   ├── voice/              # Vocode voice actions
│   ├── routes/             # API route handlers
│   ├── jobs/               # Background processing
│   └── main.py             # Application entry point
├── frontend/               # React Native frontend
│   ├── components/         # UI components
│   ├── services/           # API and service clients
│   └── App.tsx             # Application entry point
├── tests/                  # Test suites
└── PRPs/                   # Product Requirements Prompts
```

### Key Files
- `backend/main.py` - Main API server with routes and WebSocket
- `backend/models/database.py` - SQLAlchemy ORM models
- `backend/voice/conversation_manager.py` - Vocode integration
- `frontend/App.tsx` - React Native main application
- `.env.example` - Environment variables template
- `pyproject.toml` - Python dependencies and configuration

## 🐛 Troubleshooting

### Common Issues

#### Rust/Tiktoken Build Errors
```bash
# Ensure Rust is installed and in PATH
rustup default stable
export PATH="$HOME/.cargo/bin:$PATH"
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
```

#### Import Errors
```bash
# Ensure all dependencies are installed in the virtual environment
source myenv/bin/activate
pip install -e .
```

#### Database Connection Issues
- Verify Supabase credentials in `.env`
- Check database URL format and permissions
- Ensure Supabase project is active

#### Voice/Audio Issues
- Verify ElevenLabs API key and quota
- Check microphone permissions on mobile device
- Ensure WebSocket connection is established

### Development Tips

1. **Use Environment Variables**: Never commit API keys to version control
2. **Test Incrementally**: Start with unit tests, then integration tests
3. **Monitor API Quotas**: ElevenLabs and OpenAI have usage limits
4. **Debug WebSockets**: Use browser dev tools to monitor WebSocket connections
5. **Check Logs**: Both backend and frontend log important debugging information

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass: `python -m pytest tests/ -v`
5. Submit a pull request

---

**Note**: This application requires several external API keys to function fully. The core architecture and unit tests work without them, but end-to-end functionality requires proper configuration of all external services.