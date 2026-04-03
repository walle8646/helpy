-- Migration: Add recording_requested column to booking table (SQLite)
-- Il campo indica se il cliente ha richiesto la registrazione della consulenza

ALTER TABLE booking ADD COLUMN recording_requested BOOLEAN DEFAULT 1 NOT NULL;
