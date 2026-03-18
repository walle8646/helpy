-- Migration: Add languages and last_seen columns to user table (PostgreSQL)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS languages TEXT DEFAULT NULL;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS last_seen TIMESTAMP DEFAULT NULL;
