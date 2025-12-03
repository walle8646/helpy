-- Migration: Aggiungi colonna updated_at a configuration_property
-- Data: 2025-11-15
-- Descrizione: Aggiunge la colonna updated_at per tracciare gli ultimi aggiornamenti delle configurazioni

-- SQLite (non supporta CURRENT_TIMESTAMP come default in ALTER TABLE)
ALTER TABLE configuration_property ADD COLUMN updated_at DATETIME NULL;

-- Aggiorna i valori esistenti con il timestamp corrente
UPDATE configuration_property SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL;

-- PostgreSQL (commenta la parte SQLite e usa questa se su PostgreSQL)
-- ALTER TABLE configuration_property ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
