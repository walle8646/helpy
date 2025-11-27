-- =====================================================================
-- MIGRATION: Aggiungi supporto per sottocategorie nel profilo utente
-- =====================================================================
-- Questa migrazione aggiunge la possibilità di selezionare
-- una o più sottocategorie oltre alla categoria principale

-- =====================================================================
-- SQLite
-- =====================================================================

-- Aggiungi colonna per le sottocategorie selezionate (come JSON)
ALTER TABLE "user" ADD COLUMN selected_subcategories TEXT DEFAULT NULL;
-- selected_subcategories sarà un JSON array: ["9", "10", "15"]

-- Crea indice per ricerche future
CREATE INDEX IF NOT EXISTS idx_user_selected_subcategories ON "user"(selected_subcategories);

-- =====================================================================
-- Note:
-- - selected_subcategories: JSON array degli ID delle sottocategorie
-- - Esempio: '["9", "10", "15"]'
-- - NULL = no subcategories selected
-- =====================================================================
