-- Migration: Aggiunge campo is_anonymous alla tabella user
-- SQLite version

ALTER TABLE user ADD COLUMN is_anonymous BOOLEAN DEFAULT 0;

-- Commento: Se is_anonymous = 1, il nome/cognome non viene mostrato pubblicamente
-- Viene visualizzato "Utente #ID" al posto del nome reale
