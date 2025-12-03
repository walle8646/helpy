-- ============================================================================
-- MIGRATION: Aggiungi colonna is_principal alla tabella category (MySQL)
-- Esegui questo script se stai aggiornando un database esistente
-- ============================================================================

-- Aggiungi la colonna is_principal se non esiste
ALTER TABLE category ADD COLUMN is_principal BOOLEAN DEFAULT FALSE;

-- Crea indice per query efficienti
CREATE INDEX idx_category_is_principal ON category(is_principal);

-- Aggiorna le categorie principali (IDs 1-7) a TRUE (1)
UPDATE category SET is_principal = TRUE WHERE id IN (1, 2, 3, 4, 5, 6, 7);

-- Verifica
-- SELECT id, name, is_principal FROM category ORDER BY id;
-- SELECT COUNT(*) as principal_count FROM category WHERE is_principal = TRUE;
