-- Migration: Aggiunge colonna google_id alla tabella user per login Google OAuth
-- SQLite version

ALTER TABLE "user" ADD COLUMN google_id TEXT DEFAULT NULL;
CREATE INDEX IF NOT EXISTS ix_user_google_id ON "user" (google_id);
