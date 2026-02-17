-- Migration: Aggiunge colonna genere alla tabella user
-- Valori: 'M' = Maschio, 'F' = Femmina, NULL = Non specificato

-- SQLite
ALTER TABLE user ADD COLUMN genere VARCHAR(1) DEFAULT NULL;
