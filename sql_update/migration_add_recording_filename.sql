-- ============================================================
-- Migration: Aggiungi colonna recording_filename a booking
-- ============================================================
-- Questa colonna memorizza il nome del file di registrazione
-- Formato: booking_{booking_id}_{YYYYMMDD_HHMMSS}
-- Esempio: booking_123_20251121_210446

-- ============================================================
-- SQLite
-- ============================================================
-- Esegui questo comando nel tuo database SQLite (dev.db)

ALTER TABLE booking 
ADD COLUMN recording_filename TEXT;

-- Verifica che la colonna sia stata aggiunta
PRAGMA table_info(booking);


-- ============================================================
-- PostgreSQL
-- ============================================================
-- Esegui questo comando nel tuo database PostgreSQL (produzione)

ALTER TABLE booking 
ADD COLUMN recording_filename TEXT;

-- Verifica che la colonna sia stata aggiunta
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'booking' 
ORDER BY ordinal_position;
