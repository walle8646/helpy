-- Migration: Aggiunge colonna images alla tabella community_questions (SQLite)
-- Le immagini sono salvate come JSON array di URL S3
ALTER TABLE community_questions ADD COLUMN images TEXT DEFAULT NULL;
