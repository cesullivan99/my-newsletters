-- Supabase Storage Bucket Configuration
-- Run this after creating your Supabase project

-- Note: Storage buckets must be created via Supabase Dashboard or API
-- This file documents the required configuration

-- Required Storage Bucket: newsletter-audio
-- Configuration:
-- - Public: true (for audio streaming)
-- - File size limit: 50MB
-- - Allowed MIME types: audio/mpeg, audio/mp3, audio/wav

-- Storage policies for newsletter-audio bucket
-- These should be applied via Supabase Dashboard

-- Policy: Allow authenticated users to upload audio for their stories
-- Operation: INSERT
-- Check: bucket_id = 'newsletter-audio' AND auth.role() = 'authenticated'

-- Policy: Allow public read access to audio files
-- Operation: SELECT
-- Check: bucket_id = 'newsletter-audio'

-- Policy: Allow authenticated users to delete their own audio files
-- Operation: DELETE
-- Check: bucket_id = 'newsletter-audio' AND auth.uid()::text IN (
--     SELECT u.id::text FROM users u
--     JOIN newsletters n ON u.id = n.user_id
--     JOIN stories s ON n.id = s.newsletter_id
--     WHERE s.audio_url LIKE '%' || name
-- )

-- Create function to clean up orphaned audio files
CREATE OR REPLACE FUNCTION cleanup_orphaned_audio_files()
RETURNS void AS $$
DECLARE
    orphaned_file RECORD;
BEGIN
    -- Find audio files in cache that no longer have associated stories
    FOR orphaned_file IN
        SELECT ac.* FROM audio_cache ac
        LEFT JOIN stories s ON ac.story_id = s.id
        WHERE s.id IS NULL
    LOOP
        -- Log the deletion
        INSERT INTO activity_log (action_type, action_details)
        VALUES ('audio_cleanup', jsonb_build_object(
            'file_path', orphaned_file.file_path,
            'deleted_at', CURRENT_TIMESTAMP
        ));
        
        -- Delete the cache record
        DELETE FROM audio_cache WHERE id = orphaned_file.id;
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- Create scheduled job to clean up orphaned audio (run daily)
-- Note: Scheduled jobs must be set up via Supabase Dashboard or pg_cron extension
-- Example cron expression: 0 2 * * * (daily at 2 AM)
-- SELECT cron.schedule('cleanup-audio', '0 2 * * *', 'SELECT cleanup_orphaned_audio_files();');