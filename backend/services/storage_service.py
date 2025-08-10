"""
Cloud storage service for audio file management using Supabase Storage.

Provides file upload, download, and management functionality for
newsletter audio files with proper error handling and optimization.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from supabase import AsyncClient, create_async_client

from ..config import get_config

logger = logging.getLogger(__name__)
config = get_config()


class StorageService:
    """
    Supabase Storage service for audio file management.

    Handles upload, download, and lifecycle management of audio files
    with proper error handling, optimization, and cleanup.
    """

    def __init__(self):
        """Initialize storage service with Supabase client."""
        self.supabase_client: AsyncClient | None = None
        self.bucket_name = config.storage_bucket_name
        self.base_url = config.audio_base_url

        # File management settings
        self.max_file_size = 50 * 1024 * 1024  # 50MB max file size
        self.supported_formats = [".mp3", ".wav", ".m4a", ".ogg"]
        self.cleanup_threshold_days = 30  # Clean up old files after 30 days

        # Upload retry settings
        self.max_retries = 3
        self.retry_delay = 1  # seconds

    async def initialize(self) -> None:
        """Initialize Supabase client and ensure bucket exists."""
        try:
            # Create Supabase client
            self.supabase_client = await create_async_client(
                config.supabase_url, config.supabase_service_role_key
            )

            # Ensure bucket exists
            await self._ensure_bucket_exists()

            logger.info("Storage service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize storage service: {e}")
            raise

    async def upload_audio_file(
        self,
        audio_data: bytes,
        story_id: uuid.UUID,
        file_format: str = "mp3",
        metadata: dict | None = None,
    ) -> str:
        """
        Upload audio file to cloud storage.

        Args:
            audio_data: Audio file data as bytes.
            story_id: UUID of the story this audio belongs to.
            file_format: Audio file format (mp3, wav, etc.).
            metadata: Optional metadata to store with file.

        Returns:
            Public URL of uploaded file.
        """
        if not self.supabase_client:
            raise RuntimeError("Storage service not initialized")

        try:
            # Validate file size
            if len(audio_data) > self.max_file_size:
                raise ValueError(
                    f"File size {len(audio_data)} exceeds maximum {self.max_file_size}"
                )

            # Validate format
            if f".{file_format.lower()}" not in self.supported_formats:
                raise ValueError(f"Unsupported format: {file_format}")

            # Generate file path
            file_path = await self._generate_file_path(story_id, file_format)

            # Create file metadata
            file_metadata = {
                "story_id": str(story_id),
                "upload_timestamp": datetime.utcnow().isoformat(),
                "file_size": len(audio_data),
                "format": file_format,
            }

            if metadata:
                file_metadata.update(metadata)

            # Upload file with retries
            success = False
            last_error = None

            for attempt in range(self.max_retries):
                try:
                    # Upload to Supabase Storage
                    response = await self.supabase_client.storage.from_(
                        self.bucket_name
                    ).upload(
                        path=file_path,
                        file=audio_data,
                        file_options={
                            "content-type": f"audio/{file_format}",
                            "cache-control": "3600",  # 1 hour cache
                            "upsert": True,  # Overwrite if exists
                        },
                    )

                    if response:
                        success = True
                        break

                except Exception as e:
                    last_error = e
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        logger.warning(
                            f"Upload attempt {attempt + 1} failed, retrying: {e}"
                        )
                    else:
                        logger.error(f"All upload attempts failed: {e}")

            if not success:
                raise last_error or Exception("Upload failed after all retries")

            # Generate public URL
            public_url = f"{self.base_url}{file_path}"

            logger.info(f"Successfully uploaded audio file: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"Failed to upload audio file for story {story_id}: {e}")
            raise

    async def download_audio_file(self, file_path: str) -> bytes:
        """
        Download audio file from cloud storage.

        Args:
            file_path: Path to file in storage bucket.

        Returns:
            Audio file data as bytes.
        """
        if not self.supabase_client:
            raise RuntimeError("Storage service not initialized")

        try:
            # Download from Supabase Storage
            response = await self.supabase_client.storage.from_(
                self.bucket_name
            ).download(file_path)

            if not response:
                raise FileNotFoundError(f"File not found: {file_path}")

            logger.info(f"Successfully downloaded audio file: {file_path}")
            return response

        except Exception as e:
            logger.error(f"Failed to download audio file {file_path}: {e}")
            raise

    async def delete_audio_file(self, file_path: str) -> bool:
        """
        Delete audio file from cloud storage.

        Args:
            file_path: Path to file in storage bucket.

        Returns:
            True if deletion successful.
        """
        if not self.supabase_client:
            raise RuntimeError("Storage service not initialized")

        try:
            # Delete from Supabase Storage
            response = await self.supabase_client.storage.from_(
                self.bucket_name
            ).remove([file_path])

            if response:
                logger.info(f"Successfully deleted audio file: {file_path}")
                return True
            else:
                logger.warning(f"File may not exist: {file_path}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete audio file {file_path}: {e}")
            return False

    async def get_file_info(self, file_path: str) -> dict | None:
        """
        Get information about a stored file.

        Args:
            file_path: Path to file in storage bucket.

        Returns:
            File information dictionary or None if not found.
        """
        if not self.supabase_client:
            raise RuntimeError("Storage service not initialized")

        try:
            # List files to get metadata
            files = await self.supabase_client.storage.from_(self.bucket_name).list(
                path=str(Path(file_path).parent),
                limit=100,
                offset=0,
                sort_by="name",
            )

            # Find matching file
            file_name = Path(file_path).name
            for file_info in files:
                if file_info.get("name") == file_name:
                    return {
                        "name": file_info.get("name"),
                        "size": file_info.get("metadata", {}).get("size"),
                        "mimetype": file_info.get("metadata", {}).get("mimetype"),
                        "created_at": file_info.get("created_at"),
                        "updated_at": file_info.get("updated_at"),
                    }

            return None

        except Exception as e:
            logger.error(f"Failed to get file info for {file_path}: {e}")
            return None

    async def list_user_audio_files(self, user_id: uuid.UUID) -> list[dict]:
        """
        List all audio files for a specific user.

        Args:
            user_id: User UUID to filter files.

        Returns:
            List of file information dictionaries.
        """
        if not self.supabase_client:
            raise RuntimeError("Storage service not initialized")

        try:
            # List files in user directory
            user_path = f"users/{user_id}/"

            files = await self.supabase_client.storage.from_(self.bucket_name).list(
                path=user_path,
                limit=1000,
                offset=0,
                sort_by="created_at",
            )

            file_list = []
            for file_info in files:
                if file_info.get("name", "").endswith(tuple(self.supported_formats)):
                    file_list.append(
                        {
                            "name": file_info.get("name"),
                            "path": f"{user_path}{file_info.get('name')}",
                            "size": file_info.get("metadata", {}).get("size"),
                            "created_at": file_info.get("created_at"),
                            "public_url": f"{self.base_url}{user_path}{file_info.get('name')}",
                        }
                    )

            return file_list

        except Exception as e:
            logger.error(f"Failed to list audio files for user {user_id}: {e}")
            return []

    async def cleanup_old_files(self, days_old: int = None) -> int:
        """
        Clean up old audio files to save storage space.

        Args:
            days_old: Number of days old files must be to delete (default from config).

        Returns:
            Number of files deleted.
        """
        if not self.supabase_client:
            raise RuntimeError("Storage service not initialized")

        days_old = days_old or self.cleanup_threshold_days
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        try:
            # List all files
            files = await self.supabase_client.storage.from_(self.bucket_name).list(
                path="",
                limit=10000,
                offset=0,
                sort_by="created_at",
            )

            files_to_delete = []
            for file_info in files:
                created_at = file_info.get("created_at")
                if created_at:
                    file_date = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    if file_date < cutoff_date:
                        files_to_delete.append(file_info.get("name"))

            # Delete old files
            deleted_count = 0
            if files_to_delete:
                response = await self.supabase_client.storage.from_(
                    self.bucket_name
                ).remove(files_to_delete)
                if response:
                    deleted_count = len(files_to_delete)

            logger.info(
                f"Cleaned up {deleted_count} old files (older than {days_old} days)"
            )
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")
            return 0

    async def get_storage_usage(self, user_id: uuid.UUID | None = None) -> dict:
        """
        Get storage usage statistics.

        Args:
            user_id: Optional user ID to get usage for specific user.

        Returns:
            Storage usage information.
        """
        if not self.supabase_client:
            raise RuntimeError("Storage service not initialized")

        try:
            # Determine path to check
            path = f"users/{user_id}/" if user_id else ""

            files = await self.supabase_client.storage.from_(self.bucket_name).list(
                path=path,
                limit=10000,
                offset=0,
                sort_by="created_at",
            )

            total_size = 0
            file_count = 0

            for file_info in files:
                if file_info.get("name", "").endswith(tuple(self.supported_formats)):
                    file_count += 1
                    size = file_info.get("metadata", {}).get("size", 0)
                    total_size += size

            return {
                "total_files": file_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / 1024 / 1024, 2),
                "average_file_size_bytes": (
                    round(total_size / file_count) if file_count > 0 else 0
                ),
            }

        except Exception as e:
            logger.error(f"Failed to get storage usage: {e}")
            return {
                "total_files": 0,
                "total_size_bytes": 0,
                "total_size_mb": 0,
                "average_file_size_bytes": 0,
            }

    async def _generate_file_path(self, story_id: uuid.UUID, file_format: str) -> str:
        """Generate unique file path for audio file."""
        # Use story ID and timestamp for uniqueness
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_name = f"{story_id}_{timestamp}.{file_format.lower()}"

        # Organize by date for easier management
        date_path = datetime.utcnow().strftime("%Y/%m")

        return f"stories/{date_path}/{file_name}"

    async def _ensure_bucket_exists(self) -> None:
        """Ensure storage bucket exists."""
        try:
            # List buckets to check if our bucket exists
            buckets = await self.supabase_client.storage.list_buckets()

            bucket_exists = any(
                bucket.get("name") == self.bucket_name for bucket in buckets
            )

            if not bucket_exists:
                # Create bucket if it doesn't exist
                await self.supabase_client.storage.create_bucket(
                    id=self.bucket_name,
                    options={
                        "public": True,  # Allow public access to audio files
                        "file_size_limit": self.max_file_size,
                        "allowed_mime_types": ["audio/*"],
                    },
                )
                logger.info(f"Created storage bucket: {self.bucket_name}")

        except Exception as e:
            logger.warning(f"Could not verify/create bucket: {e}")
            # Continue anyway - bucket might exist but we don't have list permissions

    async def generate_presigned_url(
        self,
        file_path: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate presigned URL for temporary file access.

        Args:
            file_path: Path to file in storage.
            expires_in: URL expiration time in seconds.

        Returns:
            Presigned URL for file access.
        """
        if not self.supabase_client:
            raise RuntimeError("Storage service not initialized")

        try:
            # Generate presigned URL
            response = await self.supabase_client.storage.from_(
                self.bucket_name
            ).create_signed_url(path=file_path, expires_in=expires_in)

            if response:
                signed_url = response.get("signed_url", "")
                full_url = f"{config.supabase_url}/storage/v1{signed_url}"
                return full_url

            raise Exception("Failed to generate presigned URL")

        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {file_path}: {e}")
            # Fallback to public URL
            return f"{self.base_url}{file_path}"

    def get_public_url(self, file_path: str) -> str:
        """
        Get public URL for a stored file.

        Args:
            file_path: Path to file in storage.

        Returns:
            Public URL for file access.
        """
        return f"{self.base_url}{file_path}"


# Service instance
storage_service = StorageService()


def get_storage_service() -> StorageService:
    """Get storage service instance."""
    return storage_service
