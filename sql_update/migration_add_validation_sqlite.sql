-- Migration: Aggiungere colonna validation alla tabella community_questions (SQLite)
-- Data: 2025-12-02
-- Descrizione: Aggiunge un flag per validare/moderare le domande della community

-- Aggiungi la colonna validation
ALTER TABLE community_questions 
ADD COLUMN validation BOOLEAN DEFAULT 0;

-- Crea indice per query frequenti
CREATE INDEX idx_community_questions_validation ON community_questions(validation);

-- Totale: 1 colonna aggiunta + 1 indice
-- validation: BOOLEAN DEFAULT 0 - Flag di validazione (0=non validata, 1=validata)
