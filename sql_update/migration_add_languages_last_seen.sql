-- Migration: Add languages and last_seen columns to user table (SQLite)
ALTER TABLE user ADD COLUMN languages TEXT DEFAULT NULL;
ALTER TABLE user ADD COLUMN last_seen TIMESTAMP DEFAULT NULL;
