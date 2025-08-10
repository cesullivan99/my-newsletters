"""
Application configuration management.

Handles loading environment variables, API keys, and database connections
with proper validation and error handling.
"""

import os
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker


class Config:
    """
    Application configuration loaded from environment variables.
    
    Provides centralized access to all configuration settings with
    validation and default values.
    """

    def __init__(self):
        """Load configuration from environment variables."""
        load_dotenv()

        # Database Configuration
        self.database_url = self._get_required("DATABASE_URL")
        self.supabase_url = self._get_required("SUPABASE_URL")
        self.supabase_anon_key = self._get_required("SUPABASE_ANON_KEY")
        self.supabase_service_role_key = self._get_required("SUPABASE_SERVICE_ROLE_KEY")

        # API Keys
        self.elevenlabs_api_key = self._get_required("ELEVENLABS_API_KEY")
        self.openai_api_key = self._get_required("OPENAI_API_KEY")
        self.deepgram_api_key = os.getenv("DEEPGRAM_API_KEY", "")  # Optional

        # Gmail OAuth Configuration
        self.gmail_client_id = self._get_required("GMAIL_CLIENT_ID")
        self.gmail_client_secret = self._get_required("GMAIL_CLIENT_SECRET")
        self.gmail_redirect_uri = self._get_required("GMAIL_REDIRECT_URI")

        # JWT Configuration
        self.jwt_secret = self._get_required("JWT_SECRET")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        self.jwt_expiration_hours = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

        # Application Configuration
        self.app_host = os.getenv("APP_HOST", "localhost")
        self.app_port = int(os.getenv("APP_PORT", "5000"))
        self.app_debug = os.getenv("APP_DEBUG", "false").lower() == "true"
        self.app_env = os.getenv("APP_ENV", "development")

        # Audio Processing Configuration
        self.audio_processing_batch_size = int(os.getenv("AUDIO_PROCESSING_BATCH_SIZE", "10"))
        self.audio_processing_interval_minutes = int(
            os.getenv("AUDIO_PROCESSING_INTERVAL_MINUTES", "15")
        )

        # Voice Configuration
        self.default_voice_id = os.getenv("DEFAULT_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
        self.DEFAULT_VOICE_ID = self.default_voice_id  # Alias for convenience
        self.default_voice_model = os.getenv("DEFAULT_VOICE_MODEL", "eleven_multilingual_v2")
        self.audio_streaming_latency = int(os.getenv("AUDIO_STREAMING_LATENCY", "2"))

        # Storage Configuration
        self.storage_bucket_name = os.getenv("STORAGE_BUCKET_NAME", "newsletter-audio")
        self.audio_base_url = os.getenv("AUDIO_BASE_URL", f"{self.supabase_url}/storage/v1/object/public/{self.storage_bucket_name}/")

        # Rate Limiting Configuration
        self.gmail_api_rate_limit = int(os.getenv("GMAIL_API_RATE_LIMIT", "100"))
        self.elevenlabs_rate_limit = int(os.getenv("ELEVENLABS_RATE_LIMIT", "20"))

        # Frontend Configuration
        self.frontend_api_base_url = os.getenv("FRONTEND_API_BASE_URL", f"http://{self.app_host}:{self.app_port}")
        self.websocket_url = os.getenv("WEBSOCKET_URL", f"ws://{self.app_host}:{self.app_port}")

        # Logging Configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_file = os.getenv("LOG_FILE", "logs/app.log")

        # Vocode Configuration (if needed)
        self.vocode_api_key = os.getenv("VOCODE_API_KEY", "")

    def _get_required(self, key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Required environment variable {key} is not set")
        return value

    def _get_optional(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get optional environment variable with default."""
        return os.getenv(key, default)

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env.lower() == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.app_env.lower() == "testing"

    def validate_config(self) -> None:
        """
        Validate configuration settings.
        
        Raises:
            ValueError: If any configuration is invalid.
        """
        # Validate database URL format
        if not self.database_url.startswith(("postgresql://", "sqlite://")):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL or SQLite URL")

        # Validate Supabase URL format
        if not self.supabase_url.startswith("https://"):
            raise ValueError("SUPABASE_URL must be a valid HTTPS URL")

        # Validate JWT configuration
        if len(self.jwt_secret) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")

        # Validate audio configuration
        if not 0 <= self.audio_streaming_latency <= 4:
            raise ValueError("AUDIO_STREAMING_LATENCY must be between 0 and 4")

        # Validate rate limits
        if self.gmail_api_rate_limit <= 0:
            raise ValueError("GMAIL_API_RATE_LIMIT must be positive")

        if self.elevenlabs_rate_limit <= 0:
            raise ValueError("ELEVENLABS_RATE_LIMIT must be positive")

    def get_database_url(self, async_driver: bool = True) -> str:
        """
        Get database URL with appropriate driver.
        
        Args:
            async_driver: Whether to use async driver (asyncpg vs psycopg2).
            
        Returns:
            Database URL with correct driver.
        """
        if async_driver and self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url

    def get_cors_origins(self) -> list[str]:
        """Get allowed CORS origins based on environment."""
        if self.is_development:
            return [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                f"http://{self.app_host}:{self.app_port}",
                "http://localhost:8081",  # React Native development
                "exp://localhost:19000",  # Expo development
            ]
        elif self.is_production:
            # Add production domains here
            return ["https://your-production-domain.com"]
        else:
            return ["*"]  # Allow all for testing

    def get_gmail_scopes(self) -> list[str]:
        """Get required Gmail API scopes."""
        return [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
        ]

    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary (excluding secrets).
        
        Returns:
            Dictionary of non-sensitive configuration values.
        """
        return {
            "app_host": self.app_host,
            "app_port": self.app_port,
            "app_debug": self.app_debug,
            "app_env": self.app_env,
            "default_voice_id": self.default_voice_id,
            "default_voice_model": self.default_voice_model,
            "audio_streaming_latency": self.audio_streaming_latency,
            "storage_bucket_name": self.storage_bucket_name,
            "log_level": self.log_level,
            "is_production": self.is_production,
            "is_development": self.is_development,
        }


# Global configuration instance
config = Config()

# Global database engine and session maker
_engine = None
_session_maker = None


def get_config() -> Config:
    """Get global configuration instance."""
    return config


def get_database_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            config.get_database_url(async_driver=True),
            echo=config.is_development,
            future=True,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _engine


def get_session_maker():
    """Get or create session maker."""
    global _session_maker
    if _session_maker is None:
        _session_maker = async_sessionmaker(
            get_database_engine(),
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _session_maker


@asynccontextmanager
async def get_database_session():
    """Get async database session context manager."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Create a settings alias for convenience (matches PRP pseudocode)
settings = config


def validate_environment() -> None:
    """
    Validate environment configuration on startup.
    
    Raises:
        ValueError: If any required configuration is missing or invalid.
    """
    try:
        config.validate_config()
        print(f"✅ Configuration loaded successfully for {config.app_env} environment")
        print(f"📊 Database: {config.database_url.split('@')[1] if '@' in config.database_url else 'Local'}")
        print(f"🎵 Audio: ElevenLabs ({config.default_voice_model})")
        print(f"🚀 Server: {config.app_host}:{config.app_port}")
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        raise