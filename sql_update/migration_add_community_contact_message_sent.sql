-- Migration: Aggiunge colonna message_sent a community_contacts
-- Il contatore views viene ora incrementato solo quando il consulente invia un messaggio
ALTER TABLE community_contacts ADD COLUMN message_sent BOOLEAN DEFAULT FALSE;
