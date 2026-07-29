-- App Credentials Management System - Database Migration
-- Created: 2026-07-26
-- Description: Creates the app_credentials table for storing Netflix and other app credentials

-- Enable UUID extension if needed
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create app_credentials table
CREATE TABLE IF NOT EXISTS app_credentials (
    id SERIAL PRIMARY KEY,
    credential_id VARCHAR(255) UNIQUE NOT NULL,
    app_name VARCHAR(100) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    login_url TEXT,
    profile_name VARCHAR(255),
    api_key VARCHAR(500),
    custom_config TEXT,
    app_version VARCHAR(50),
    device_type VARCHAR(100),
    is_primary BOOLEAN DEFAULT TRUE,
    team_name VARCHAR(255) NOT NULL,
    location VARCHAR(100),
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0
);

-- Create indexes for optimal query performance
CREATE INDEX IF NOT EXISTS idx_app_credentials_app_name ON app_credentials(app_name);
CREATE INDEX IF NOT EXISTS idx_app_credentials_team_name ON app_credentials(team_name);
CREATE INDEX IF NOT EXISTS idx_app_credentials_is_primary ON app_credentials(is_primary);
CREATE INDEX IF NOT EXISTS idx_app_credentials_is_active ON app_credentials(is_active);
CREATE INDEX IF NOT EXISTS idx_app_credentials_device_type ON app_credentials(device_type);
CREATE INDEX IF NOT EXISTS idx_app_credentials_location ON app_credentials(location);

-- Add is_super_admin and is_team_admin columns to users table if they don't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_super_admin BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_team_admin BOOLEAN DEFAULT FALSE;

-- Create index on users for admin fields
CREATE INDEX IF NOT EXISTS idx_users_is_super_admin ON users(is_super_admin);
CREATE INDEX IF NOT EXISTS idx_users_is_team_admin ON users(is_team_admin);

-- Set up sample data (optional - comment out if not needed)
-- INSERT INTO app_credentials (
--     credential_id,
--     app_name,
--     username,
--     password,
--     login_url,
--     profile_name,
--     is_primary,
--     team_name,
--     device_type,
--     is_active,
--     usage_count
-- ) VALUES (
--     'netflix_qa_team_v1',
--     'netflix',
--     'netflix_user@example.com',
--     'netflix_password',
--     'http://netflix.com/tv2',
--     'Main',
--     TRUE,
--     'QA-Team',
--     'RDK',
--     TRUE,
--     0
-- );

-- Verify table creation
SELECT 
    table_name,
    column_name,
    data_type
FROM 
    information_schema.columns
WHERE 
    table_name = 'app_credentials'
ORDER BY 
    ordinal_position;
