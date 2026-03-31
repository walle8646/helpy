-- Migration: Aggiunge colonne analisi AI alla tabella disputes (SQLite)
ALTER TABLE disputes ADD COLUMN ai_verdict TEXT DEFAULT NULL;
ALTER TABLE disputes ADD COLUMN ai_confidence INTEGER DEFAULT NULL;
ALTER TABLE disputes ADD COLUMN ai_comment TEXT DEFAULT NULL;
ALTER TABLE disputes ADD COLUMN ai_analyzed_at TIMESTAMP DEFAULT NULL;
