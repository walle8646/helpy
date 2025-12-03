-- ============================================================================
-- MIGRATION: Aggiungi colonna primary_category_id a community_questions (SQLite)
-- ============================================================================

PRAGMA foreign_keys = ON;

-- Aggiungi la colonna primary_category_id se non esiste
ALTER TABLE community_questions ADD COLUMN primary_category_id INTEGER REFERENCES category(id);

-- Crea indice per query efficienti
CREATE INDEX IF NOT EXISTS idx_community_questions_primary_category ON community_questions(primary_category_id);

-- Verifica
-- SELECT COUNT(*) FROM community_questions;
-- SELECT id, title, primary_category_id, category_id FROM community_questions LIMIT 5;
