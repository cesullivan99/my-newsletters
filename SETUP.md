# My Newsletters Voice Assistant - Setup Guide

## 🚀 Quick Start

This guide will help you set up the My Newsletters Voice Assistant from scratch to production deployment.

## 📋 Prerequisites

### Required Software
- Python 3.13+
- Node.js 18+ and npm
- Docker and Docker Compose
- PostgreSQL 15+ (or Supabase account)
- Git

### Platform-Specific Requirements

#### iOS Development
- macOS with Xcode 14+
- CocoaPods (`sudo gem install cocoapods`)
- Apple Developer Account (for distribution)

#### Android Development
- Android Studio
- Android SDK (API level 31+)
- Java Development Kit (JDK) 17
- Set `ANDROID_HOME` environment variable

## 🔑 API Keys Setup

You'll need to obtain the following API keys:

### 1. Supabase Setup
1. Create account at [supabase.com](https://supabase.com)
2. Create new project
3. Go to Settings → API
4. Copy:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
5. Go to Settings → Database
6. Copy connection string for `DATABASE_URL`

### 2. ElevenLabs Setup
1. Create account at [elevenlabs.io](https://elevenlabs.io)
2. Go to Profile → API Keys
3. Generate and copy API key
4. Note your voice ID preferences

### 3. OpenAI Setup
1. Create account at [platform.openai.com](https://platform.openai.com)
2. Go to API Keys
3. Create new secret key
4. Copy the key (you won't see it again!)

### 4. Gmail OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create new project or select existing
3. Enable Gmail API:
   - Go to APIs & Services → Library
   - Search for "Gmail API"
   - Click Enable
4. Create OAuth 2.0 credentials:
   - Go to APIs & Services → Credentials
   - Click "Create Credentials" → OAuth client ID
   - Application type: Web application
   - Add authorized redirect URIs:
     - `http://localhost:5001/auth/google/callback` (development)
     - `https://yourdomain.com/auth/google/callback` (production)
   - Copy Client ID and Client Secret

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/my-newsletters.git
cd my-newsletters
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

Required environment variables:
```env
# Supabase (Required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql://...

# ElevenLabs (Required)
ELEVENLABS_API_KEY=your-api-key

# OpenAI (Required)
OPENAI_API_KEY=sk-...

# Gmail OAuth (Required)
GMAIL_CLIENT_ID=....apps.googleusercontent.com
GMAIL_CLIENT_SECRET=...

# JWT (Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET=your-generated-secret
```

### 3. Backend Setup

#### Option A: Docker Setup (Recommended)
```bash
# Build and start services
docker-compose up -d

# Run database migrations
docker-compose exec app python backend/migrations/migrate.py migrate

# Verify health
curl http://localhost:5001/health
```

#### Option B: Local Setup
```bash
# Create virtual environment
python -m venv myenv
source myenv/bin/activate  # On Windows: myenv\Scripts\activate

# Install dependencies
pip install -e .

# Run database migrations
python backend/migrations/migrate.py migrate

# Start application
python -m backend.main
```

### 4. Frontend Setup (React Native)

```bash
cd frontend

# Install dependencies
npm install

# iOS setup
cd ios && pod install && cd ..

# Start Metro bundler
npm start

# Run on iOS simulator
npm run ios

# Run on Android emulator
npm run android
```

## 🗄️ Database Setup

### Using Supabase (Recommended)
1. Migrations are automatically applied when you run the migration script
2. Verify tables in Supabase Dashboard → Table Editor

### Using Local PostgreSQL
1. Create database:
```sql
CREATE DATABASE my_newsletters;
```

2. Run migrations:
```bash
python backend/migrations/migrate.py migrate
```

## 🧪 Testing

### Run Unit Tests
```bash
# Backend tests
pytest tests/unit -v

# Frontend tests
cd frontend && npm test
```

### Run Integration Tests
```bash
# Requires real API keys
pytest tests/integration -v
```

### Test Voice Assistant
```bash
# Start the application
docker-compose up

# In another terminal, test endpoints
curl http://localhost:5001/health
curl -X POST http://localhost:5001/auth/gmail-oauth
```

## 🚀 Deployment

### Production Deployment with Docker

1. **Prepare production environment:**
```bash
# Update .env for production
APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=WARNING
```

2. **Deploy with Docker Compose:**
```bash
# Run deployment script
./scripts/deploy.sh production

# Or manually:
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

3. **Setup SSL/TLS:**
- Place SSL certificates in `ssl/` directory
- Update `nginx.conf` with your domain

### Cloud Deployment Options

#### Deploy to AWS
```bash
# Build Docker image
docker build -t my-newsletters .

# Tag for ECR
docker tag my-newsletters:latest $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/my-newsletters:latest

# Push to ECR
docker push $AWS_ACCOUNT.dkr.ecr.$REGION.amazonaws.com/my-newsletters:latest

# Deploy with ECS/Fargate or EC2
```

#### Deploy to Google Cloud
```bash
# Build and push to Container Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/my-newsletters

# Deploy to Cloud Run
gcloud run deploy my-newsletters \
  --image gcr.io/$PROJECT_ID/my-newsletters \
  --platform managed \
  --allow-unauthenticated
```

#### Deploy to Heroku
```bash
# Create Heroku app
heroku create my-newsletters

# Set environment variables
heroku config:set $(cat .env | grep -v '^#' | xargs)

# Deploy
git push heroku main
```

## 📱 Mobile App Deployment

### iOS App Store
1. **Build release version:**
```bash
./scripts/build-mobile.sh ios release
```

2. **Upload to App Store Connect:**
- Open Xcode
- Product → Archive
- Distribute App → App Store Connect

### Google Play Store
1. **Generate signing key:**
```bash
./scripts/build-mobile.sh sign-android
```

2. **Build release bundle:**
```bash
./scripts/build-mobile.sh android release
```

3. **Upload AAB file to Play Console**

## 🔍 Monitoring

### Check Application Health
```bash
# Health endpoint
curl http://localhost:5001/health

# Metrics endpoint
curl http://localhost:5001/metrics
```

### View Logs
```bash
# Application logs
docker-compose logs -f app

# Database logs
docker-compose logs -f postgres

# All services
docker-compose logs -f
```

### Database Monitoring
```sql
-- Check active sessions
SELECT * FROM v_active_sessions;

-- Check processing queue
SELECT * FROM v_user_briefing_queue;

-- Check recent activity
SELECT * FROM activity_log ORDER BY created_at DESC LIMIT 10;
```

## 🐛 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Find process using port 5001
lsof -i :5001
# Kill the process
kill -9 <PID>
```

#### Database Connection Failed
- Verify `DATABASE_URL` is correct
- Check Supabase project is active
- Ensure network connectivity

#### Audio Generation Fails
- Verify ElevenLabs API key
- Check account has sufficient credits
- Test with shorter text first

#### Gmail Authentication Issues
- Verify OAuth credentials
- Check redirect URI matches exactly
- Ensure Gmail API is enabled

#### Docker Build Fails
```bash
# Clean Docker cache
docker system prune -a
# Rebuild without cache
docker-compose build --no-cache
```

### Debug Mode
```bash
# Enable debug logging
export APP_DEBUG=true
export LOG_LEVEL=DEBUG

# Run with verbose output
docker-compose up
```

## 📚 Additional Resources

- [API Documentation](http://localhost:5001/docs) (when running)
- [Supabase Documentation](https://supabase.com/docs)
- [ElevenLabs API Reference](https://docs.elevenlabs.io)
- [React Native Documentation](https://reactnative.dev)
- [Vocode Documentation](https://docs.vocode.dev)

## 🤝 Support

For issues or questions:
1. Check existing [GitHub Issues](https://github.com/yourusername/my-newsletters/issues)
2. Review logs for error messages
3. Create new issue with:
   - Error messages
   - Steps to reproduce
   - Environment details

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.