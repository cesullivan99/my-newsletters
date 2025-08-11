"""
Integration tests for ElevenLabs TTS service
Run with actual API key to validate audio generation
"""

import pytest
import os
import asyncio
from pathlib import Path
from backend.services.audio_service import AudioService
from dotenv import load_dotenv

load_dotenv()

# Skip these tests if running in CI or without credentials
SKIP_INTEGRATION = os.getenv("TEST_ELEVENLABS_MOCK", "true").lower() == "true"
pytestmark = pytest.mark.skipif(SKIP_INTEGRATION, reason="ElevenLabs integration tests require real API key")


class TestElevenLabsIntegration:
    @pytest.fixture
    async def audio_service(self):
        """Create audio service instance"""
        return AudioService()
    
    @pytest.fixture
    def test_text(self):
        """Sample text for TTS generation"""
        return "This is a test of the ElevenLabs text to speech integration."
    
    @pytest.fixture
    def long_text(self):
        """Longer text for streaming test"""
        return """
        In today's technology news, artificial intelligence continues to advance
        at an unprecedented pace. Researchers at major institutions have announced
        breakthroughs in natural language processing that promise to revolutionize
        how we interact with computers. These developments could have far-reaching
        implications for industries ranging from healthcare to education.
        """
    
    @pytest.mark.asyncio
    async def test_generate_audio(self, audio_service, test_text):
        """Test basic audio generation"""
        # Generate audio
        audio_data = await audio_service.generate_audio(
            text=test_text,
            voice_id=os.getenv("DEFAULT_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
        )
        
        assert audio_data is not None
        assert len(audio_data) > 0
        
        # Verify it's valid MP3 data (starts with ID3 or FF FB)
        assert audio_data[:3] == b"ID3" or audio_data[:2] == b"\xff\xfb"
    
    @pytest.mark.asyncio
    async def test_streaming_audio(self, audio_service, long_text):
        """Test streaming audio generation"""
        chunks = []
        
        async for chunk in audio_service.generate_audio_stream(
            text=long_text,
            voice_id=os.getenv("DEFAULT_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
        ):
            chunks.append(chunk)
        
        assert len(chunks) > 0
        
        # Combine chunks and verify
        full_audio = b"".join(chunks)
        assert len(full_audio) > 0
    
    @pytest.mark.asyncio
    async def test_voice_settings(self, audio_service, test_text):
        """Test different voice settings"""
        # Test with custom settings
        audio_data = await audio_service.generate_audio(
            text=test_text,
            voice_id=os.getenv("DEFAULT_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),
            stability=0.3,
            similarity_boost=0.9,
            style=0.5
        )
        
        assert audio_data is not None
        assert len(audio_data) > 0
    
    @pytest.mark.asyncio
    async def test_model_selection(self, audio_service, test_text):
        """Test different ElevenLabs models"""
        models = ["eleven_multilingual_v2", "eleven_monolingual_v1"]
        
        for model in models:
            try:
                audio_data = await audio_service.generate_audio(
                    text=test_text,
                    voice_id=os.getenv("DEFAULT_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),
                    model_id=model
                )
                assert audio_data is not None
            except Exception as e:
                # Model might not be available on the account
                assert "model" in str(e).lower() or "not found" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, audio_service, test_text):
        """Test ElevenLabs rate limiting"""
        # Make multiple concurrent requests
        tasks = []
        for i in range(3):
            task = audio_service.generate_audio(
                text=f"{test_text} Version {i}",
                voice_id=os.getenv("DEFAULT_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check if any rate limiting occurred
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0  # At least some should succeed
    
    @pytest.mark.asyncio
    async def test_error_handling(self, audio_service):
        """Test error handling for invalid inputs"""
        # Test with invalid voice ID
        with pytest.raises(Exception) as exc_info:
            await audio_service.generate_audio(
                text="Test",
                voice_id="invalid_voice_id_12345"
            )
        
        assert "voice" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()
        
        # Test with empty text
        with pytest.raises(Exception) as exc_info:
            await audio_service.generate_audio(
                text="",
                voice_id=os.getenv("DEFAULT_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
            )
        
        assert "text" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_save_audio_to_file(self, audio_service, test_text, tmp_path):
        """Test saving generated audio to file"""
        # Generate audio
        audio_data = await audio_service.generate_audio(
            text=test_text,
            voice_id=os.getenv("DEFAULT_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
        )
        
        # Save to file
        output_file = tmp_path / "test_audio.mp3"
        with open(output_file, "wb") as f:
            f.write(audio_data)
        
        # Verify file was created and has content
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        
        # Verify it's a valid MP3 file
        with open(output_file, "rb") as f:
            header = f.read(3)
            assert header == b"ID3" or header[:2] == b"\xff\xfb"