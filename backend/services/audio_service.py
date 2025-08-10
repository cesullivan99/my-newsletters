"""
ElevenLabs audio generation service for newsletter story narration.

Provides text-to-speech conversion with streaming, voice management,
and optimized audio processing for real-time briefings.
"""

import asyncio
import io
import logging
import uuid
from datetime import datetime
from typing import AsyncIterator, Dict, List, Optional, Tuple

import aiohttp
from elevenlabs import AsyncElevenLabs, Voice, VoiceSettings
from elevenlabs.types import Model

from ..config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class AudioService:
    """
    ElevenLabs audio generation and streaming service.
    
    Handles text-to-speech conversion with real-time streaming capabilities,
    voice customization, and audio file management for newsletter briefings.
    """

    def __init__(self):
        """Initialize audio service with ElevenLabs client."""
        self.elevenlabs_client = AsyncElevenLabs(api_key=config.elevenlabs_api_key)
        self.default_voice_id = config.default_voice_id
        self.default_model = config.default_voice_model
        self.streaming_latency = config.audio_streaming_latency
        self.rate_limit = config.elevenlabs_rate_limit
        
        # Rate limiting state
        self._requests_made = 0
        self._window_start = datetime.utcnow()
        self._request_lock = asyncio.Lock()
        
        # Voice cache
        self._voice_cache = {}
        self._model_cache = {}

    async def initialize(self) -> None:
        """Initialize audio service and cache available voices/models."""
        try:
            # Cache available voices
            await self._cache_voices()
            
            # Cache available models
            await self._cache_models()
            
            logger.info("Audio service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize audio service: {e}")
            raise

    async def generate_story_audio(
        self,
        story_text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        voice_settings: Optional[Dict] = None,
    ) -> bytes:
        """
        Generate audio for a story using ElevenLabs TTS.
        
        Args:
            story_text: Text content to convert to audio.
            voice_id: ElevenLabs voice ID (defaults to configured voice).
            model_id: ElevenLabs model ID (defaults to configured model).
            voice_settings: Custom voice settings for generation.
            
        Returns:
            Audio data as bytes.
        """
        await self._check_rate_limit()
        
        try:
            # Use defaults if not specified
            voice_id = voice_id or self.default_voice_id
            model_id = model_id or self.default_model
            
            # Prepare voice settings
            settings = VoiceSettings(
                stability=voice_settings.get("stability", 0.71) if voice_settings else 0.71,
                similarity_boost=voice_settings.get("similarity_boost", 0.5) if voice_settings else 0.5,
                style=voice_settings.get("style", 0.0) if voice_settings else 0.0,
                use_speaker_boost=voice_settings.get("use_speaker_boost", True) if voice_settings else True,
            )
            
            # Generate audio
            logger.info(f"Generating audio for {len(story_text)} characters using voice {voice_id}")
            
            audio_generator = await self.elevenlabs_client.generate(
                text=story_text,
                voice=voice_id,
                model=model_id,
                voice_settings=settings,
                stream=False,  # Get complete audio
                optimize_streaming_latency=self.streaming_latency,
            )
            
            # Collect audio data
            audio_data = b""
            async for chunk in audio_generator:
                audio_data += chunk
            
            logger.info(f"Generated {len(audio_data)} bytes of audio")
            return audio_data
            
        except Exception as e:
            logger.error(f"Failed to generate story audio: {e}")
            raise

    async def stream_story_audio(
        self,
        story_text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        voice_settings: Optional[Dict] = None,
    ) -> AsyncIterator[bytes]:
        """
        Stream audio generation for real-time playback.
        
        Args:
            story_text: Text content to convert to audio.
            voice_id: ElevenLabs voice ID.
            model_id: ElevenLabs model ID.
            voice_settings: Custom voice settings.
            
        Yields:
            Audio chunks as bytes for streaming.
        """
        await self._check_rate_limit()
        
        try:
            # Use defaults if not specified
            voice_id = voice_id or self.default_voice_id
            model_id = model_id or self.default_model
            
            # Prepare voice settings
            settings = VoiceSettings(
                stability=voice_settings.get("stability", 0.71) if voice_settings else 0.71,
                similarity_boost=voice_settings.get("similarity_boost", 0.5) if voice_settings else 0.5,
                style=voice_settings.get("style", 0.0) if voice_settings else 0.0,
                use_speaker_boost=voice_settings.get("use_speaker_boost", True) if voice_settings else True,
            )
            
            logger.info(f"Streaming audio for {len(story_text)} characters using voice {voice_id}")
            
            # Generate streaming audio
            audio_generator = await self.elevenlabs_client.generate(
                text=story_text,
                voice=voice_id,
                model=model_id,
                voice_settings=settings,
                stream=True,  # Enable streaming
                optimize_streaming_latency=self.streaming_latency,
            )
            
            chunk_count = 0
            async for chunk in audio_generator:
                chunk_count += 1
                yield chunk
            
            logger.info(f"Streamed audio in {chunk_count} chunks")
            
        except Exception as e:
            logger.error(f"Failed to stream story audio: {e}")
            raise

    async def generate_briefing_intro(
        self,
        user_name: str,
        story_count: int,
        date: datetime,
        voice_id: Optional[str] = None,
    ) -> bytes:
        """
        Generate audio for briefing introduction.
        
        Args:
            user_name: User's name for personalization.
            story_count: Number of stories in briefing.
            date: Briefing date.
            voice_id: Voice to use for intro.
            
        Returns:
            Audio data for briefing intro.
        """
        # Create personalized intro text
        intro_text = await self._create_intro_text(user_name, story_count, date)
        
        # Generate audio
        return await self.generate_story_audio(
            story_text=intro_text,
            voice_id=voice_id,
        )

    async def generate_transition_audio(
        self,
        transition_type: str,
        story_index: Optional[int] = None,
        total_stories: Optional[int] = None,
        voice_id: Optional[str] = None,
    ) -> bytes:
        """
        Generate audio for transitions between stories.
        
        Args:
            transition_type: Type of transition ('next', 'skip', 'conclusion').
            story_index: Current story index.
            total_stories: Total number of stories.
            voice_id: Voice to use.
            
        Returns:
            Audio data for transition.
        """
        # Create transition text
        transition_text = await self._create_transition_text(
            transition_type, story_index, total_stories
        )
        
        # Generate audio
        return await self.generate_story_audio(
            story_text=transition_text,
            voice_id=voice_id,
        )

    async def get_available_voices(self) -> List[Dict]:
        """
        Get list of available ElevenLabs voices.
        
        Returns:
            List of voice information dictionaries.
        """
        if not self._voice_cache:
            await self._cache_voices()
        
        return list(self._voice_cache.values())

    async def get_voice_info(self, voice_id: str) -> Optional[Dict]:
        """
        Get information about a specific voice.
        
        Args:
            voice_id: ElevenLabs voice ID.
            
        Returns:
            Voice information or None if not found.
        """
        if not self._voice_cache:
            await self._cache_voices()
        
        return self._voice_cache.get(voice_id)

    async def clone_voice_from_sample(
        self,
        name: str,
        description: str,
        audio_files: List[bytes],
    ) -> str:
        """
        Clone a voice from audio samples.
        
        Args:
            name: Name for the cloned voice.
            description: Description of the voice.
            audio_files: List of audio samples as bytes.
            
        Returns:
            ID of the cloned voice.
        """
        await self._check_rate_limit()
        
        try:
            # Note: This would require implementing file upload to ElevenLabs
            # For now, return a placeholder
            logger.warning("Voice cloning not implemented yet")
            return self.default_voice_id
            
        except Exception as e:
            logger.error(f"Failed to clone voice: {e}")
            raise

    async def _check_rate_limit(self) -> None:
        """Enforce ElevenLabs API rate limiting."""
        async with self._request_lock:
            from datetime import timedelta
            
            now = datetime.utcnow()
            
            # Reset window if an hour has passed
            if now - self._window_start > timedelta(hours=1):
                self._requests_made = 0
                self._window_start = now
            
            # Check if we've exceeded the rate limit
            if self._requests_made >= self.rate_limit:
                # Calculate wait time until window resets
                wait_time = 3600 - (now - self._window_start).total_seconds()
                if wait_time > 0:
                    logger.warning(f"ElevenLabs rate limit exceeded, waiting {wait_time:.1f} seconds")
                    await asyncio.sleep(wait_time)
                    # Reset counters
                    self._requests_made = 0
                    self._window_start = datetime.utcnow()
            
            self._requests_made += 1

    async def _cache_voices(self) -> None:
        """Cache available ElevenLabs voices."""
        try:
            voices = await self.elevenlabs_client.voices.get_all()
            
            for voice in voices.voices:
                self._voice_cache[voice.voice_id] = {
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "category": voice.category,
                    "description": getattr(voice, 'description', ''),
                    "preview_url": getattr(voice, 'preview_url', ''),
                    "settings": {
                        "stability": getattr(voice.settings, 'stability', 0.71) if voice.settings else 0.71,
                        "similarity_boost": getattr(voice.settings, 'similarity_boost', 0.5) if voice.settings else 0.5,
                        "style": getattr(voice.settings, 'style', 0.0) if voice.settings else 0.0,
                        "use_speaker_boost": getattr(voice.settings, 'use_speaker_boost', True) if voice.settings else True,
                    }
                }
            
            logger.info(f"Cached {len(self._voice_cache)} voices")
            
        except Exception as e:
            logger.error(f"Failed to cache voices: {e}")
            # Use default voice as fallback
            self._voice_cache[self.default_voice_id] = {
                "voice_id": self.default_voice_id,
                "name": "Default Voice",
                "category": "premade",
                "description": "Default ElevenLabs voice",
                "preview_url": "",
                "settings": {
                    "stability": 0.71,
                    "similarity_boost": 0.5,
                    "style": 0.0,
                    "use_speaker_boost": True,
                }
            }

    async def _cache_models(self) -> None:
        """Cache available ElevenLabs models."""
        try:
            models = await self.elevenlabs_client.models.get_all()
            
            for model in models:
                self._model_cache[model.model_id] = {
                    "model_id": model.model_id,
                    "name": model.name,
                    "description": getattr(model, 'description', ''),
                    "languages": getattr(model, 'languages', []),
                }
            
            logger.info(f"Cached {len(self._model_cache)} models")
            
        except Exception as e:
            logger.error(f"Failed to cache models: {e}")
            # Use default model as fallback
            self._model_cache[self.default_model] = {
                "model_id": self.default_model,
                "name": "Default Model",
                "description": "Default ElevenLabs model",
                "languages": ["en"],
            }

    async def _create_intro_text(
        self, user_name: str, story_count: int, date: datetime
    ) -> str:
        """Create personalized briefing introduction text."""
        date_str = date.strftime("%A, %B %d")
        
        intro_templates = [
            f"Good morning, {user_name}! Welcome to your daily newsletter briefing for {date_str}. "
            f"I have {story_count} stories lined up for you today. Let's dive in!",
            
            f"Hello {user_name}, and welcome to your personalized news briefing for {date_str}. "
            f"Today I'll be sharing {story_count} key stories from your subscribed newsletters. Here we go!",
            
            f"Hi {user_name}! It's {date_str}, and I'm here with your daily newsletter roundup. "
            f"We have {story_count} interesting stories to cover today. Let's get started!"
        ]
        
        # Choose based on story count to add variety
        template_index = story_count % len(intro_templates)
        return intro_templates[template_index]

    async def _create_transition_text(
        self,
        transition_type: str,
        story_index: Optional[int],
        total_stories: Optional[int],
    ) -> str:
        """Create transition text between stories."""
        if transition_type == "next":
            if story_index and total_stories:
                remaining = total_stories - story_index
                if remaining > 1:
                    return f"Next up, story {story_index + 1} of {total_stories}."
                else:
                    return "And now, our final story."
            return "Moving on to our next story."
        
        elif transition_type == "skip":
            return "Alright, let's skip ahead to the next story."
        
        elif transition_type == "conclusion":
            return "And that wraps up your newsletter briefing for today. Have a great day!"
        
        else:
            return "Let's continue."

    async def optimize_for_streaming(self, text: str) -> str:
        """
        Optimize text for streaming audio generation.
        
        Args:
            text: Original text content.
            
        Returns:
            Optimized text for better streaming performance.
        """
        # Break long sentences for better streaming
        optimized_text = text.replace(". ", ".\n")
        
        # Add pauses for better pacing
        optimized_text = optimized_text.replace(":", ":...")
        optimized_text = optimized_text.replace(";", ";...")
        
        # Ensure proper pronunciation of common abbreviations
        abbreviations = {
            "CEO": "C-E-O",
            "AI": "A-I",
            "API": "A-P-I",
            "URL": "U-R-L",
            "FAQ": "F-A-Q",
        }
        
        for abbr, pronunciation in abbreviations.items():
            optimized_text = optimized_text.replace(abbr, pronunciation)
        
        return optimized_text


# Service instance
audio_service = AudioService()


def get_audio_service() -> AudioService:
    """Get audio service instance."""
    return audio_service