-- ============================================================================
-- MIGRATION: Aggiungi colonna is_principal alla tabella category (SQLite)
-- Esegui questo script se stai aggiornando un database esistente
-- ============================================================================

PRAGMA foreign_keys = ON;

-- Aggiungi la colonna is_principal se non esiste
ALTER TABLE category ADD COLUMN is_principal BOOLEAN DEFAULT 0;

-- Aggiorna le categorie principali (IDs 1-7) a TRUE (1)
UPDATE category SET is_principal = 1 WHERE id IN (1, 2, 3, 4, 5, 6, 7);

-- Verifica
-- SELECT id, name, is_principal FROM category ORDER BY id;
-- SELECT COUNT(*) as principal_count FROM category WHERE is_principal = 1;
