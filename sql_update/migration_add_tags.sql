-- Migration: Aggiunge colonna 'tags' alla tabella user
-- SQLite version
-- I tag sono generati automaticamente dall'AI e usati per la ricerca

ALTER TABLE user ADD COLUMN tags TEXT DEFAULT NULL;
