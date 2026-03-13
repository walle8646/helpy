-- Migration: Aggiunge colonna images alla tabella community_questions (PostgreSQL)
-- Le immagini sono salvate come JSON array di URL S3
ALTER TABLE community_questions ADD COLUMN IF NOT EXISTS images TEXT DEFAULT NULL;
