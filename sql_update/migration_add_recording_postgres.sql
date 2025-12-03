-- Migration: Add recording fields to booking table (PostgreSQL)
-- Aggiunge campi per tracciare le registrazioni delle video call

ALTER TABLE booking ADD COLUMN recording_sid VARCHAR(255) DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_resource_id VARCHAR(255) DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_status VARCHAR(50) DEFAULT 'not_started';
ALTER TABLE booking ADD COLUMN recording_url TEXT DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_duration INTEGER DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_file_size INTEGER DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_started_at TIMESTAMP DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_completed_at TIMESTAMP DEFAULT NULL;

-- Commenti per documentazione
COMMENT ON COLUMN booking.recording_sid IS 'Agora Cloud Recording SID identifier';
COMMENT ON COLUMN booking.recording_resource_id IS 'Agora resource ID for the recording';
COMMENT ON COLUMN booking.recording_status IS 'Status: not_started, recording, processing, completed, failed';
COMMENT ON COLUMN booking.recording_url IS 'S3 URL or path to the recorded video file';
COMMENT ON COLUMN booking.recording_duration IS 'Duration of recording in seconds';
COMMENT ON COLUMN booking.recording_file_size IS 'File size in bytes';

-- Indici per performance
CREATE INDEX idx_booking_recording_sid ON booking(recording_sid);
CREATE INDEX idx_booking_recording_status ON booking(recording_status);
