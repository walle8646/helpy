-- Rimuovi colonna bollini dalla tabella user (SQLite)
-- SQLite non supporta DROP COLUMN direttamente nelle versioni < 3.35
-- Se usi SQLite >= 3.35:
ALTER TABLE "user" DROP COLUMN bollini;
