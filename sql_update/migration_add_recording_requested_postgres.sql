-- Migration: Add recording_requested column to booking table (PostgreSQL)
-- Il campo indica se il cliente ha richiesto la registrazione della consulenza

ALTER TABLE booking ADD COLUMN IF NOT EXISTS recording_requested BOOLEAN DEFAULT TRUE NOT NULL;
