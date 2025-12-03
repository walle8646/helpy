-- Migration: Add client_joined_at and consultant_joined_at to booking table (PostgreSQL)
-- Date: 2025-11-03
-- Description: Tracks when client and consultant click "Partecipa" to join the consultation

-- Add client_joined_at column
ALTER TABLE booking 
ADD COLUMN client_joined_at TIMESTAMP DEFAULT NULL;

-- Add consultant_joined_at column
ALTER TABLE booking 
ADD COLUMN consultant_joined_at TIMESTAMP DEFAULT NULL;

-- Add indexes for performance
CREATE INDEX idx_booking_client_joined ON booking(client_joined_at);
CREATE INDEX idx_booking_consultant_joined ON booking(consultant_joined_at);

-- Add comments for documentation
COMMENT ON COLUMN booking.client_joined_at IS 'Timestamp when the client clicked "Partecipa" to join the consultation';
COMMENT ON COLUMN booking.consultant_joined_at IS 'Timestamp when the consultant clicked "Partecipa" to join the consultation';

-- Verify the changes
\d booking;
