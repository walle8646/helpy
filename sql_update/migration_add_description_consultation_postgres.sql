-- Migration: Aggiungere colonna description alla tabella booking (PostgreSQL)
-- Data: 2025-11-28
-- Descrizione: Aggiunge un campo per i dettagli della consulenza richiesta dal cliente

-- Aggiungi la colonna description
ALTER TABLE booking 
ADD COLUMN description VARCHAR(2000) DEFAULT NULL;

-- Crea indice per query frequenti
CREATE INDEX idx_booking_description ON booking(description);

-- Verifica la colonna aggiunta
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'booking' AND column_name = 'description';

-- Totale: 1 colonna aggiunta + 1 indice
-- description: VARCHAR(2000) NULL - Dettagli della consulenza richiesta dal cliente

