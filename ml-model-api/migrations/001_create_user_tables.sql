-- Migration: Create User Management Tables
-- Version: 001
-- Description: Initial schema for comprehensive user management system
-- Date: 2024-01-01

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    status VARCHAR(30) NOT NULL DEFAULT 'pending_verification',
    email_verified BOOLEAN DEFAULT FALSE,
    phone_number VARCHAR(20),
    phone_verified BOOLEAN DEFAULT FALSE,
    two_factor_enabled BOOLEAN DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    failed_login_attempts INTEGER DEFAULT 0,
    account_locked_until TIMESTAMP,
    password_changed_at TIMESTAMP,
    must_change_password BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    CONSTRAINT chk_role CHECK (role IN ('admin', 'moderator', 'premium', 'user', 'guest')),
    CONSTRAINT chk_status CHECK (status IN ('active', 'inactive', 'suspended', 'pending_verification', 'deleted')),
    CONSTRAINT chk_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- ============================================================================
-- PROFILES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS profiles (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    display_name VARCHAR(100),
    bio TEXT,
    avatar_url VARCHAR(500),
    cover_image_url VARCHAR(500),
    location VARCHAR(100),
    website VARCHAR(500),
    social_links JSONB DEFAULT '{}'::jsonb,
    date_of_birth DATE,
    gender VARCHAR(20),
    language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_website_format CHECK (website IS NULL OR website ~* '^https?://')
);

-- ============================================================================
-- PREFERENCES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS preferences (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    notifications JSONB DEFAULT '{"email": true, "sms": false, "push": true, "in_app": true, "marketing": false}'::jsonb,
    privacy JSONB DEFAULT '{"profile_visibility": "public", "email_visibility": "private", "activity_visibility": "friends"}'::jsonb,
    email_frequency VARCHAR(20) DEFAULT 'daily',
    theme VARCHAR(20) DEFAULT 'light',
    language VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    accessibility JSONB DEFAULT '{"high_contrast": false, "large_text": false, "screen_reader": false}'::jsonb,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_email_frequency CHECK (email_frequency IN ('realtime', 'daily', 'weekly', 'never')),
    CONSTRAINT chk_theme CHECK (theme IN ('light', 'dark', 'auto'))
);

-- ============================================================================
-- SESSIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- ACTIVITY LOGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS activity_logs (
    activity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    activity_data JSONB DEFAULT '{}'::jsonb,
    ip_address VARCHAR(45),
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- PASSWORD HISTORY TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS password_history (
    id SERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- USER STATISTICS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_statistics (
    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    total_predictions INTEGER DEFAULT 0,
    total_uploads INTEGER DEFAULT 0,
    total_api_calls INTEGER DEFAULT 0,
    favorite_foods JSONB DEFAULT '[]'::jsonb,
    most_active_day VARCHAR(10),
    most_active_hour INTEGER,
    average_confidence DECIMAL(5, 4) DEFAULT 0.0,
    last_activity TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- VERIFICATION TOKENS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS verification_tokens (
    token VARCHAR(255) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    token_type VARCHAR(50) NOT NULL,
    email VARCHAR(254),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT chk_token_type CHECK (token_type IN ('email_verification', 'password_reset', '2fa_setup'))
);

-- ============================================================================
-- INDEXES
-- ============================================================================

-- Users table indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login);

-- Sessions table indexes
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_is_active ON sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_sessions_created_at ON sessions(created_at);

-- Activity logs table indexes
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_activity_logs_activity_type ON activity_logs(activity_type);

-- Password history table indexes
CREATE INDEX IF NOT EXISTS idx_password_history_user_id ON password_history(user_id);
CREATE INDEX IF NOT EXISTS idx_password_history_created_at ON password_history(created_at);

-- Verification tokens table indexes
CREATE INDEX IF NOT EXISTS idx_verification_tokens_user_id ON verification_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_verification_tokens_expires_at ON verification_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_verification_tokens_token_type ON verification_tokens(token_type);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Trigger to update updated_at timestamp on users table
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_preferences_updated_at
    BEFORE UPDATE ON preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger to create default profile when user is created
CREATE OR REPLACE FUNCTION create_default_profile()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (user_id) VALUES (NEW.user_id);
    INSERT INTO preferences (user_id) VALUES (NEW.user_id);
    INSERT INTO user_statistics (user_id) VALUES (NEW.user_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER create_user_profile
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION create_default_profile();

-- ============================================================================
-- VIEWS
-- ============================================================================

-- View for complete user information
CREATE OR REPLACE VIEW user_complete_view AS
SELECT 
    u.user_id,
    u.username,
    u.email,
    u.role,
    u.status,
    u.email_verified,
    u.two_factor_enabled,
    u.created_at,
    u.last_login,
    p.display_name,
    p.avatar_url,
    p.location,
    pr.theme,
    pr.language,
    s.total_predictions,
    s.total_uploads,
    s.total_api_calls
FROM users u
LEFT JOIN profiles p ON u.user_id = p.user_id
LEFT JOIN preferences pr ON u.user_id = pr.user_id
LEFT JOIN user_statistics s ON u.user_id = s.user_id;

-- View for active sessions
CREATE OR REPLACE VIEW active_sessions_view AS
SELECT 
    s.session_id,
    s.user_id,
    u.username,
    u.email,
    s.created_at,
    s.expires_at,
    s.ip_address,
    s.last_activity,
    EXTRACT(EPOCH FROM (s.expires_at - CURRENT_TIMESTAMP)) AS seconds_until_expiry
FROM sessions s
JOIN users u ON s.user_id = u.user_id
WHERE s.is_active = TRUE AND s.expires_at > CURRENT_TIMESTAMP;

-- View for user activity summary
CREATE OR REPLACE VIEW user_activity_summary AS
SELECT 
    user_id,
    COUNT(*) AS total_activities,
    COUNT(DISTINCT activity_type) AS unique_activity_types,
    MIN(timestamp) AS first_activity,
    MAX(timestamp) AS last_activity,
    COUNT(*) FILTER (WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '24 hours') AS activities_last_24h,
    COUNT(*) FILTER (WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '7 days') AS activities_last_7d,
    COUNT(*) FILTER (WHERE timestamp > CURRENT_TIMESTAMP - INTERVAL '30 days') AS activities_last_30d
FROM activity_logs
GROUP BY user_id;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM sessions
    WHERE expires_at < CURRENT_TIMESTAMP OR (is_active = FALSE AND created_at < CURRENT_TIMESTAMP - INTERVAL '30 days');
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old activity logs (keep last 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_activity_logs()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM activity_logs
    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '90 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up expired verification tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM verification_tokens
    WHERE expires_at < CURRENT_TIMESTAMP OR used = TRUE;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get user statistics
CREATE OR REPLACE FUNCTION get_user_stats(p_user_id UUID)
RETURNS TABLE (
    total_activities BIGINT,
    login_count BIGINT,
    last_login TIMESTAMP,
    account_age_days INTEGER,
    predictions_count INTEGER,
    uploads_count INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT AS total_activities,
        COUNT(*) FILTER (WHERE activity_type = 'login')::BIGINT AS login_count,
        MAX(u.last_login) AS last_login,
        EXTRACT(DAY FROM CURRENT_TIMESTAMP - u.created_at)::INTEGER AS account_age_days,
        COALESCE(s.total_predictions, 0) AS predictions_count,
        COALESCE(s.total_uploads, 0) AS uploads_count
    FROM activity_logs a
    JOIN users u ON a.user_id = u.user_id
    LEFT JOIN user_statistics s ON u.user_id = s.user_id
    WHERE a.user_id = p_user_id
    GROUP BY u.created_at, s.total_predictions, s.total_uploads;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA
-- ============================================================================

-- Insert default admin user (password: Admin@123456)
-- Note: This is a bcrypt hash of "Admin@123456"
INSERT INTO users (username, email, password_hash, role, status, email_verified, password_changed_at)
VALUES (
    'admin',
    'admin@flavorsnap.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYILSBHxQgK',
    'admin',
    'active',
    TRUE,
    CURRENT_TIMESTAMP
)
ON CONFLICT (username) DO NOTHING;

-- ============================================================================
-- GRANTS (adjust based on your database user)
-- ============================================================================

-- Grant permissions to application user (replace 'flavorsnap_app' with your actual user)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO flavorsnap_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO flavorsnap_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO flavorsnap_app;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE users IS 'Main users table storing authentication and account information';
COMMENT ON TABLE profiles IS 'Extended user profile information';
COMMENT ON TABLE preferences IS 'User preferences and settings';
COMMENT ON TABLE sessions IS 'Active user sessions';
COMMENT ON TABLE activity_logs IS 'User activity audit trail';
COMMENT ON TABLE password_history IS 'Password history for preventing reuse';
COMMENT ON TABLE user_statistics IS 'User usage statistics and metrics';
COMMENT ON TABLE verification_tokens IS 'Email verification and password reset tokens';

COMMENT ON COLUMN users.role IS 'User role: admin, moderator, premium, user, guest';
COMMENT ON COLUMN users.status IS 'Account status: active, inactive, suspended, pending_verification, deleted';
COMMENT ON COLUMN users.two_factor_enabled IS 'Whether two-factor authentication is enabled';
COMMENT ON COLUMN users.failed_login_attempts IS 'Number of consecutive failed login attempts';
COMMENT ON COLUMN users.account_locked_until IS 'Timestamp until which account is locked';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 001_create_user_tables.sql completed successfully';
    RAISE NOTICE 'Created tables: users, profiles, preferences, sessions, activity_logs, password_history, user_statistics, verification_tokens';
    RAISE NOTICE 'Created views: user_complete_view, active_sessions_view, user_activity_summary';
    RAISE NOTICE 'Created functions: cleanup_expired_sessions, cleanup_old_activity_logs, cleanup_expired_tokens, get_user_stats';
END $$;
