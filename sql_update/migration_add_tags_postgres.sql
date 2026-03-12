-- Migration: Aggiunge colonna 'tags' alla tabella user
-- PostgreSQL version
-- I tag sono generati automaticamente dall'AI e usati per la ricerca

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS tags TEXT DEFAULT NULL;
