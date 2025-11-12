-- Migration: Aggiunge tabella community_likes per gestire i like degli utenti
-- SQLite version

CREATE TABLE IF NOT EXISTS community_likes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (question_id) REFERENCES community_questions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    
    -- Constraint univoco: un utente può mettere un solo like per domanda
    UNIQUE(question_id, user_id)
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_community_likes_question ON community_likes(question_id);
CREATE INDEX IF NOT EXISTS idx_community_likes_user ON community_likes(user_id);
