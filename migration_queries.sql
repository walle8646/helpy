-- ============================================================
-- CREAZIONE TABELLA community_questions (DA ZERO)
-- Solo domande con possibilità di like/upvote, senza risposte
-- ============================================================

-- ============================================================
-- SQLITE
-- ============================================================

-- Elimina la tabella se esiste già
DROP TABLE IF EXISTS community_questions;

-- Crea la tabella community_questions
CREATE TABLE community_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER,
    title VARCHAR(200) NOT NULL,
    description VARCHAR(5000) NOT NULL,
    status VARCHAR(50) DEFAULT 'open' NOT NULL,
    views INTEGER DEFAULT 0 NOT NULL,
    upvotes INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL
);

-- Crea indici per performance
CREATE INDEX idx_community_questions_user_id ON community_questions(user_id);
CREATE INDEX idx_community_questions_category_id ON community_questions(category_id);
CREATE INDEX idx_community_questions_status ON community_questions(status);
CREATE INDEX idx_community_questions_created_at ON community_questions(created_at DESC);


-- ============================================================
-- POSTGRESQL
-- ============================================================

-- Elimina la tabella se esiste già
DROP TABLE IF EXISTS community_questions CASCADE;

-- Crea la tabella community_questions
CREATE TABLE community_questions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    category_id INTEGER,
    title VARCHAR(200) NOT NULL,
    description VARCHAR(5000) NOT NULL,
    status VARCHAR(50) DEFAULT 'open' NOT NULL,
    views INTEGER DEFAULT 0 NOT NULL,
    upvotes INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_community_questions_user 
        FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    CONSTRAINT fk_community_questions_category 
        FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE SET NULL
);

-- Crea indici per performance
CREATE INDEX idx_community_questions_user_id ON community_questions(user_id);
CREATE INDEX idx_community_questions_category_id ON community_questions(category_id);
CREATE INDEX idx_community_questions_status ON community_questions(status);
CREATE INDEX idx_community_questions_created_at ON community_questions(created_at DESC);

-- Crea trigger per aggiornare automaticamente updated_at
CREATE OR REPLACE FUNCTION update_community_questions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_community_questions_updated_at
    BEFORE UPDATE ON community_questions
    FOR EACH ROW
    EXECUTE FUNCTION update_community_questions_updated_at();


-- ============================================================
-- VERIFICA STRUTTURA FINALE
-- ============================================================

-- SQLite: Verifica struttura tabella
-- PRAGMA table_info(community_questions);

-- PostgreSQL: Verifica struttura tabella
-- SELECT column_name, data_type, is_nullable, column_default
-- FROM information_schema.columns
-- WHERE table_name = 'community_questions'
-- ORDER BY ordinal_position;
