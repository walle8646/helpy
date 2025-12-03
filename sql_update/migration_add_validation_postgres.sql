-- Migration: Aggiungere colonna validation alla tabella community_questions (PostgreSQL)
-- Data: 2025-12-02
-- Descrizione: Aggiunge un flag per validare/moderare le domande della community

-- Aggiungi la colonna validation
ALTER TABLE community_questions 
ADD COLUMN validation BOOLEAN DEFAULT FALSE;

-- Crea indice per query frequenti
CREATE INDEX idx_community_questions_validation ON community_questions(validation);

-- Totale: 1 colonna aggiunta + 1 indice
-- validation: BOOLEAN DEFAULT FALSE - Flag di validazione (FALSE=non validata, TRUE=validata)
