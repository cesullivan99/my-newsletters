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

## 📋 Quick Start

### Prerequisites

#### Required Software
- Python 3.13+
- Node.js 18+ and npm
- Docker and Docker Compose (for production)
- PostgreSQL 15+ (or Supabase account)
- Rust Compiler (for vocode/tiktoken)

#### Platform-Specific (for mobile development)
- **iOS**: macOS with Xcode 14+, CocoaPods
- **Android**: Android Studio, Android SDK (API 31+), JDK 17

### Required API Keys
- [Supabase](https://supabase.com) - Database and storage
- [ElevenLabs](https://elevenlabs.io) - Text-to-speech API
- [OpenAI](https://platform.openai.com) - Newsletter parsing
- [Google Cloud Console](https://console.developers.google.com) - Gmail OAuth

## 🛠️ Installation

> **📖 For detailed setup instructions, deployment options, and troubleshooting, see [SETUP.md](./SETUP.md)**

### Quick Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/my-newsletters.git
cd my-newsletters

# 2. Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys (see API Keys Setup section below)

# 3. Quick start with Docker (Recommended)
docker-compose up -d
docker-compose exec app python backend/migrations/migrate.py migrate

# 4. Verify installation
curl http://localhost:5000/health
```

### Local Development Setup

```bash
# Create and activate virtual environment
python3.13 -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate

# Install Rust (required for vocode/tiktoken)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source ~/.cargo/env
export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Install Python dependencies
pip install -e .

# Run database migrations
python backend/migrations/migrate.py migrate

# Start the application
python -m backend.main
```

## 🔑 API Keys Setup

### Quick Setup Checklist

1. **Supabase** ([supabase.com](https://supabase.com))
   - Create project → Settings → API → Copy keys
   - Get: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `DATABASE_URL`

2. **ElevenLabs** ([elevenlabs.io](https://elevenlabs.io))
   - Profile → API Keys → Generate key
   - Get: `ELEVENLABS_API_KEY`

3. **OpenAI** ([platform.openai.com](https://platform.openai.com))
   - API Keys → Create new secret key
   - Get: `OPENAI_API_KEY`

4. **Gmail OAuth** ([console.cloud.google.com](https://console.cloud.google.com))
   - Enable Gmail API → Create OAuth 2.0 credentials
   - Add redirect URI: `http://localhost:5000/auth/google/callback`
   - Get: `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`

5. **JWT Secret**
   ```bash
   # Generate secure secret
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

See [SETUP.md](./SETUP.md#api-keys-setup) for detailed instructions.

## 🏃‍♂️ Running the Application

### With Docker (Recommended)
```bash
docker-compose up -d
# Application available at http://localhost:5000
```

### Local Development
```bash
# Backend
source myenv/bin/activate
python -m backend.main

# Frontend (in another terminal)
cd frontend
npm start
npm run ios     # For iOS
npm run android # For Android
```

## 🧪 Testing

```bash
# Run unit tests (40+ tests)
pytest tests/unit -v

# Run integration tests (requires API keys)
pytest tests/integration -v

# Code quality checks
black backend/
ruff check backend/ --fix
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

## 🚀 Deployment

### Production with Docker
```bash
./scripts/deploy.sh production
```

### Cloud Deployment
- **AWS**: ECS/Fargate with ECR
- **Google Cloud**: Cloud Run
- **Heroku**: Git push deployment

### Mobile Apps
```bash
# iOS App Store
./scripts/build-mobile.sh ios release

# Google Play Store
./scripts/build-mobile.sh android release
```

See [SETUP.md](./SETUP.md#deployment) for detailed deployment instructions.

## 🐛 Troubleshooting

Common issues and solutions are covered in [SETUP.md](./SETUP.md#troubleshooting):
- Rust/Tiktoken build errors
- Database connection issues
- API key configuration
- Docker build problems
- Mobile app setup

## 📚 Documentation

- **[SETUP.md](./SETUP.md)** - Detailed installation, configuration, and deployment guide
- **[TASK.md](./TASK.md)** - Development progress and task tracking
- **[PLANNING.md](./PLANNING.md)** - Architecture and design decisions
- **API Documentation** - Available at `http://localhost:5000/docs` when running

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all tests pass: `pytest tests/ -v`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This application requires several external API keys to function fully. The core architecture and unit tests work without them, but end-to-end functionality requires proper configuration of all external services. See [SETUP.md](./SETUP.md) for complete setup instructions.