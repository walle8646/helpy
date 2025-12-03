-- =====================================================================
-- MIGRATION: Aggiungi supporto per sottocategorie nel profilo utente
-- =====================================================================
-- PostgreSQL version

-- Aggiungi colonna per le sottocategorie selezionate (come JSON)
ALTER TABLE "user" ADD COLUMN selected_subcategories JSONB DEFAULT NULL;
-- selected_subcategories sarà un JSON array: ["9", "10", "15"]

-- Crea indice per ricerche future
CREATE INDEX IF NOT EXISTS idx_user_selected_subcategories ON "user" USING GIN (selected_subcategories);

-- =====================================================================
-- Note:
-- - selected_subcategories: JSONB array degli ID delle sottocategorie
-- - Esempio: '["9", "10", "15"]'
-- - NULL = no subcategories selected
-- =====================================================================
