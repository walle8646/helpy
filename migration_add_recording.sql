-- Migration: Add recording fields to booking table (SQLite)
-- Aggiunge campi per tracciare le registrazioni delle video call

ALTER TABLE booking ADD COLUMN recording_sid VARCHAR(255) DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_resource_id VARCHAR(255) DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_status VARCHAR(50) DEFAULT 'not_started';
ALTER TABLE booking ADD COLUMN recording_url TEXT DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_duration INTEGER DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_file_size INTEGER DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_started_at DATETIME DEFAULT NULL;
ALTER TABLE booking ADD COLUMN recording_completed_at DATETIME DEFAULT NULL;

-- Indici per performance
CREATE INDEX idx_booking_recording_sid ON booking(recording_sid);
CREATE INDEX idx_booking_recording_status ON booking(recording_status);
