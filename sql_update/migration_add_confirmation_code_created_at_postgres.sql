-- Data di generazione del codice di verifica email (PostgreSQL).
-- L'email dice "valido 15 minuti", ma senza questa data il codice valeva per
-- sempre. La colonna viene aggiunta anche in automatico all'avvio
-- (app/database.py, ensure_added_columns).
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS confirmation_code_created_at TIMESTAMP;
