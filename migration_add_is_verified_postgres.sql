-- ================================================
-- MIGRATION: Aggiungi campo is_verified e user_type alla tabella user - POSTGRESQL
-- ================================================

-- 1. Crea tabella user_type
CREATE TABLE IF NOT EXISTS user_type (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255)
);

-- 2. Inserisci i tipi di utente
INSERT INTO user_type (id, name, description) VALUES
(1, 'Utente', 'Utente normale della piattaforma'),
(2, 'Verificatore', 'Utente con permessi di verifica'),
(3, 'Amministratore', 'Amministratore della piattaforma')
ON CONFLICT (id) DO NOTHING;

-- 3. Aggiungi campo is_verified alla tabella user
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;

-- 4. Aggiungi campo user_type_id alla tabella user
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS user_type_id INTEGER DEFAULT 1 REFERENCES user_type(id);

-- 5. Opzionale: aggiorna utenti esistenti (esempio: verifica chi ha almeno 3 bollini)
-- UPDATE "user" SET is_verified = TRUE WHERE bollini >= 3;

-- 6. Verifica il risultato
SELECT id, nome, cognome, email, is_verified, user_type_id, bollini FROM "user" LIMIT 10;
SELECT * FROM user_type;
