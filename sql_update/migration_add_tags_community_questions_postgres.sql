-- Add tags column to community_questions table (PostgreSQL)
ALTER TABLE community_questions ADD COLUMN IF NOT EXISTS tags TEXT;
