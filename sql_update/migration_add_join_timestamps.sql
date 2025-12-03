-- Migration: Add client_joined_at and consultant_joined_at to booking table (SQLite)
-- Date: 2025-11-03
-- Description: Tracks when client and consultant click "Partecipa" to join the consultation

-- Add client_joined_at column
ALTER TABLE booking ADD COLUMN client_joined_at DATETIME DEFAULT NULL;

-- Add consultant_joined_at column
ALTER TABLE booking ADD COLUMN consultant_joined_at DATETIME DEFAULT NULL;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_booking_client_joined ON booking(client_joined_at);
CREATE INDEX IF NOT EXISTS idx_booking_consultant_joined ON booking(consultant_joined_at);

-- Verify the changes
PRAGMA table_info(booking);
