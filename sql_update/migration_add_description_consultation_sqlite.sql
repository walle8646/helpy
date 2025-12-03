-- Migration: Aggiungere colonna description alla tabella consultation (SQLite)
-- Data: 2025-11-28
-- Descrizione: Aggiunge un campo per i dettagli della consulenza richiesta dal cliente

-- Verifica se la colonna esiste già
PRAGMA table_info(consultation);

-- Se non esiste, aggiungila
ALTER TABLE booking 
ADD COLUMN description TEXT DEFAULT NULL;

-- Verifica che la colonna sia stata aggiunta
PRAGMA table_info(consultation);

-- Totale: 1 colonna aggiunta
-- description: TEXT NULL - Dettagli della consulenza richiesta dal cliente (max 2000 caratteri)
