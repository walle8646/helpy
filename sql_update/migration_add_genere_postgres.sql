-- Migration: Aggiunge colonna genere alla tabella user (PostgreSQL)
-- Valori: 'M' = Maschio, 'F' = Femmina, NULL = Non specificato

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS genere VARCHAR(1) DEFAULT NULL;
