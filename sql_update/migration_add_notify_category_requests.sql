-- Migration: Aggiungi campo notify_category_requests alla tabella user
-- Descrizione: Flag per ricevere notifiche/mail su richieste della categoria scelta

-- PostgreSQL
ALTER TABLE "user" ADD COLUMN notify_category_requests BOOLEAN DEFAULT TRUE;

-- SQLite (commentato)
-- ALTER TABLE user ADD COLUMN notify_category_requests BOOLEAN DEFAULT 1;
