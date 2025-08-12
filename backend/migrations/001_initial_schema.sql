-- My Newsletters Voice Assistant - Initial Database Schema
-- Run this migration to set up the initial database structure

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    gmail_credentials JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    preferences JSONB DEFAULT '{}'
);

-- Create newsletters table
CREATE TABLE IF NOT EXISTS newsletters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sender_email VARCHAR(255) NOT NULL,
    sender_name VARCHAR(255),
    subject VARCHAR(500) NOT NULL,
    received_date TIMESTAMP WITH TIME ZONE NOT NULL,
    raw_html TEXT,
    parsed_content JSONB,
    processing_status VARCHAR(50) DEFAULT 'pending',
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create stories table
CREATE TABLE IF NOT EXISTS stories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    newsletter_id UUID NOT NULL REFERENCES newsletters(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    position INTEGER NOT NULL,
    audio_url VARCHAR(500),
    audio_duration INTEGER,
    audio_status VARCHAR(50) DEFAULT 'pending',
    audio_generated_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_type VARCHAR(50) NOT NULL DEFAULT 'briefing',
    current_story_id UUID REFERENCES stories(id) ON DELETE SET NULL,
    current_position INTEGER DEFAULT 0,
    playback_position INTEGER DEFAULT 0,
    session_state JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true
);

-- Create user_preferences table
CREATE TABLE IF NOT EXISTS user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    voice_id VARCHAR(100) DEFAULT 'JBFqnCBsd6RMkjVDRZzb',
    voice_speed FLOAT DEFAULT 1.0,
    voice_stability FLOAT DEFAULT 0.5,
    voice_similarity_boost FLOAT DEFAULT 0.75,
    auto_play_next BOOLEAN DEFAULT true,
    summary_length VARCHAR(20) DEFAULT 'medium',
    preferred_briefing_time TIME,
    timezone VARCHAR(50) DEFAULT 'UTC',
    newsletter_sources JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create activity_log table for analytics
CREATE TABLE IF NOT EXISTS activity_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    action_details JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create audio_cache table for managing audio files
CREATE TABLE IF NOT EXISTS audio_cache (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    story_id UUID UNIQUE NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    mime_type VARCHAR(100) DEFAULT 'audio/mpeg',
    checksum VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    access_count INTEGER DEFAULT 0
);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create views for common queries
CREATE OR REPLACE VIEW v_user_briefing_queue AS
SELECT 
    s.id as story_id,
    s.title,
    s.content,
    s.summary,
    s.audio_url,
    s.position,
    n.id as newsletter_id,
    n.sender_name,
    n.subject as newsletter_subject,
    n.received_date,
    u.id as user_id,
    u.email as user_email
FROM stories s
JOIN newsletters n ON s.newsletter_id = n.id
JOIN users u ON n.user_id = u.id
WHERE s.audio_status = 'completed'
    AND n.processing_status = 'completed'
ORDER BY n.received_date DESC, s.position ASC;

-- Create view for active sessions
CREATE OR REPLACE VIEW v_active_sessions AS
SELECT 
    s.*,
    u.email as user_email,
    st.title as current_story_title,
    st.newsletter_id as current_newsletter_id
FROM sessions s
JOIN users u ON s.user_id = u.id
LEFT JOIN stories st ON s.current_story_id = st.id
WHERE s.is_active = true
    AND s.ended_at IS NULL;

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_newsletters_user_id ON newsletters(user_id);
CREATE INDEX IF NOT EXISTS idx_newsletters_received_date ON newsletters(received_date DESC);
CREATE INDEX IF NOT EXISTS idx_newsletters_processing_status ON newsletters(processing_status);
CREATE INDEX IF NOT EXISTS idx_stories_newsletter_id ON stories(newsletter_id);
CREATE INDEX IF NOT EXISTS idx_stories_position ON stories(position);
CREATE INDEX IF NOT EXISTS idx_stories_audio_status ON stories(audio_status);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active, user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity DESC);
CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON activity_log(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_session_id ON activity_log(session_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_action_type ON activity_log(action_type);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audio_cache_story_id ON audio_cache(story_id);
CREATE INDEX IF NOT EXISTS idx_audio_cache_last_accessed ON audio_cache(last_accessed DESC);

-- Grant permissions (adjust based on your Supabase roles)
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO postgres;