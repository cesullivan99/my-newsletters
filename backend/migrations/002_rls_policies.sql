-- Row Level Security (RLS) Policies for Supabase
-- This ensures users can only access their own data

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE newsletters ENABLE ROW LEVEL SECURITY;
ALTER TABLE stories ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE activity_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audio_cache ENABLE ROW LEVEL SECURITY;

-- Users table policies
CREATE POLICY "Users can view own profile" ON users
    FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update own profile" ON users
    FOR UPDATE USING (auth.uid()::text = id::text);

CREATE POLICY "Users can insert own profile" ON users
    FOR INSERT WITH CHECK (auth.uid()::text = id::text);

-- Newsletters table policies
CREATE POLICY "Users can view own newsletters" ON newsletters
    FOR SELECT USING (
        user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = id::text
        )
    );

CREATE POLICY "Users can insert own newsletters" ON newsletters
    FOR INSERT WITH CHECK (
        user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = id::text
        )
    );

CREATE POLICY "Users can update own newsletters" ON newsletters
    FOR UPDATE USING (
        user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = id::text
        )
    );

CREATE POLICY "Users can delete own newsletters" ON newsletters
    FOR DELETE USING (
        user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = id::text
        )
    );

-- Stories table policies
CREATE POLICY "Users can view stories from own newsletters" ON stories
    FOR SELECT USING (
        newsletter_id IN (
            SELECT id FROM newsletters WHERE user_id IN (
                SELECT id FROM users WHERE auth.uid()::text = id::text
            )
        )
    );

CREATE POLICY "Users can manage stories from own newsletters" ON stories
    FOR ALL USING (
        newsletter_id IN (
            SELECT id FROM newsletters WHERE user_id IN (
                SELECT id FROM users WHERE auth.uid()::text = id::text
            )
        )
    );

-- Sessions table policies
CREATE POLICY "Users can view own sessions" ON sessions
    FOR SELECT USING (
        user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = id::text
        )
    );

CREATE POLICY "Users can manage own sessions" ON sessions
    FOR ALL USING (
        user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = id::text
        )
    );

-- User preferences policies
CREATE POLICY "Users can view own preferences" ON user_preferences
    FOR SELECT USING (
        user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = id::text
        )
    );

CREATE POLICY "Users can manage own preferences" ON user_preferences
    FOR ALL USING (
        user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = id::text
        )
    );

-- Activity log policies
CREATE POLICY "Users can view own activity" ON activity_log
    FOR SELECT USING (
        user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = id::text
        )
    );

CREATE POLICY "Users can insert own activity" ON activity_log
    FOR INSERT WITH CHECK (
        user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = id::text
        )
    );

-- Audio cache policies
CREATE POLICY "Users can view audio for own stories" ON audio_cache
    FOR SELECT USING (
        story_id IN (
            SELECT s.id FROM stories s
            JOIN newsletters n ON s.newsletter_id = n.id
            WHERE n.user_id IN (
                SELECT id FROM users WHERE auth.uid()::text = id::text
            )
        )
    );

-- Service role bypass policies (for backend operations)
-- These allow the service role to bypass RLS for background jobs
CREATE POLICY "Service role has full access" ON users
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON newsletters
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON stories
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON sessions
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON user_preferences
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON activity_log
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role has full access" ON audio_cache
    FOR ALL USING (auth.role() = 'service_role');