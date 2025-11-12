-- Migration: Aggiunge campo is_anonymous alla tabella user
-- PostgreSQL version

ALTER TABLE "user" ADD COLUMN is_anonymous BOOLEAN DEFAULT FALSE;

-- Commento: Se is_anonymous = TRUE, il nome/cognome non viene mostrato pubblicamente
-- Viene visualizzato "Utente #ID" al posto del nome reale
