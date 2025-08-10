"""
Background audio processing job for newsletter briefings.

This job processes stories that don't have audio files yet, converts them to 
speech using ElevenLabs TTS, and uploads them to cloud storage.
"""

import asyncio
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_database_session, settings
from backend.models.database import Story
from backend.services.audio_service import AudioService
from backend.services.storage_service import StorageService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AudioProcessingJob:
    """
    Background job for processing newsletter stories into audio files.
    
    This job:
    1. Fetches stories without audio files
    2. Converts text to speech using ElevenLabs
    3. Uploads audio files to cloud storage
    4. Updates database with audio URLs
    """
    
    def __init__(self):
        self.audio_service = AudioService()
        self.storage_service = StorageService()
    
    async def run(self) -> None:
        """
        Execute the audio processing job.
        
        Main entry point that orchestrates the entire process.
        """
        logger.info("Starting audio processing job")
        
        try:
            async with get_database_session() as db_session:
                # Fetch stories that need audio processing
                stories = await self._fetch_stories_without_audio(db_session)
                
                if not stories:
                    logger.info("No stories found requiring audio processing")
                    return
                
                logger.info(f"Found {len(stories)} stories to process")
                
                # Process each story
                for story in stories:
                    try:
                        await self._process_story(db_session, story)
                        logger.info(f"Successfully processed story {story.id}")
                    except Exception as e:
                        logger.error(f"Failed to process story {story.id}: {e}")
                        continue
                
                logger.info("Audio processing job completed successfully")
                
        except Exception as e:
            logger.error(f"Audio processing job failed: {e}")
            raise
    
    async def _fetch_stories_without_audio(self, db_session: AsyncSession) -> List[Story]:
        """
        Fetch stories that don't have audio files generated yet.
        
        Args:
            db_session: Database session
            
        Returns:
            List of stories needing audio processing
        """
        query = select(Story).where(
            (Story.summary_audio_url.is_(None)) | 
            (Story.full_text_audio_url.is_(None))
        ).limit(50)  # Process in batches to avoid overwhelming APIs
        
        result = await db_session.execute(query)
        return result.scalars().all()
    
    async def _process_story(self, db_session: AsyncSession, story: Story) -> None:
        """
        Process a single story: convert text to audio and upload.
        
        Args:
            db_session: Database session
            story: Story to process
        """
        logger.info(f"Processing story: {story.headline}")
        
        # Generate audio for summary if missing
        if not story.summary_audio_url and story.one_sentence_summary:
            summary_audio_url = await self._generate_and_upload_audio(
                story.id, 
                story.one_sentence_summary, 
                "summary"
            )
            story.summary_audio_url = summary_audio_url
        
        # Generate audio for full text if missing
        if not story.full_text_audio_url and story.full_text_summary:
            full_text_audio_url = await self._generate_and_upload_audio(
                story.id,
                story.full_text_summary,
                "full_text"
            )
            story.full_text_audio_url = full_text_audio_url
        
        # Update the database
        await db_session.commit()
        logger.info(f"Updated story {story.id} with audio URLs")
    
    async def _generate_and_upload_audio(
        self, 
        story_id: UUID, 
        text: str, 
        audio_type: str
    ) -> str:
        """
        Generate audio from text and upload to cloud storage.
        
        Args:
            story_id: ID of the story
            text: Text to convert to speech
            audio_type: Type of audio ("summary" or "full_text")
            
        Returns:
            Public URL of the uploaded audio file
        """
        try:
            # Generate audio using ElevenLabs
            logger.info(f"Generating {audio_type} audio for story {story_id}")
            audio_data = await self.audio_service.generate_audio(
                text=text,
                voice_id=settings.DEFAULT_VOICE_ID
            )
            
            # Create file path
            file_path = f"stories/{story_id}/{audio_type}.mp3"
            
            # Upload to cloud storage
            logger.info(f"Uploading {audio_type} audio for story {story_id}")
            audio_url = await self.storage_service.upload_audio(
                file_path=file_path,
                audio_data=audio_data,
                content_type="audio/mpeg"
            )
            
            logger.info(f"Successfully uploaded {audio_type} audio: {audio_url}")
            return audio_url
            
        except Exception as e:
            logger.error(f"Failed to generate/upload {audio_type} audio for story {story_id}: {e}")
            raise


async def run_audio_processing_job():
    """
    Convenience function to run the audio processing job.
    
    This can be called from a scheduler or run manually.
    """
    job = AudioProcessingJob()
    await job.run()


if __name__ == "__main__":
    """Run the job directly when script is executed."""
    asyncio.run(run_audio_processing_job())