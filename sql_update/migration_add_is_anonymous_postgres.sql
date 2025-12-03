-- Migration: Aggiunge campo is_anonymous alla tabella user
-- PostgreSQL version

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_anonymous BOOLEAN DEFAULT FALSE;

-- Indice per migliorare le query di filtro
CREATE INDEX IF NOT EXISTS idx_user_is_anonymous ON "user"(is_anonymous);

-- Commento: Se is_anonymous = TRUE, il nome/cognome non viene mostrato pubblicamente
-- Viene visualizzato "Utente #ID" al posto del nome reale
-- 
-- Implicazioni:
-- - Gli utenti anonimi NON possono prenotare consultazioni
-- - Gli utenti anonimi NON possono ricevere messaggi da consultanti per domande anonime
-- - Le loro domande appaiono come "Utente #XX" nella community
-- - Il nome e l'avatar vengono nascosti (avatar di default mostrato)
