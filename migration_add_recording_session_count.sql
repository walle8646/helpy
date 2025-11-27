-- Migration: Add recording_session_count to booking table
-- Purpose: Track multiple recording sessions when users rejoin after previous session completed
-- Date: 2025-11-23

-- SQLite
ALTER TABLE booking ADD COLUMN recording_session_count INTEGER DEFAULT 1;

-- PostgreSQL (if needed)
-- ALTER TABLE booking ADD COLUMN recording_session_count INTEGER DEFAULT 1;
