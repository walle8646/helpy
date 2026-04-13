-- Migration: Aggiunge colonna google_id alla tabella user per login Google OAuth
-- PostgreSQL version

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS google_id VARCHAR DEFAULT NULL;
CREATE INDEX IF NOT EXISTS ix_user_google_id ON "user" (google_id);
