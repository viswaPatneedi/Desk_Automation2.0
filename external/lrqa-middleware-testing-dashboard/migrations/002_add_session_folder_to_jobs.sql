-- Migration: Add session_folder column to jobs table
-- Purpose: Store the execution session folder path for each job to enable accurate screenshot filtering

-- Add session_folder column to jobs table if it doesn't exist
ALTER TABLE jobs
ADD COLUMN IF NOT EXISTS session_folder TEXT;

-- Add index on session_folder for faster lookups (optional but recommended)
CREATE INDEX IF NOT EXISTS idx_jobs_session_folder ON jobs(session_folder);

-- Add index on status and session_folder for common queries
CREATE INDEX IF NOT EXISTS idx_jobs_status_session_folder ON jobs(status, session_folder);
