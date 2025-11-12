-- Migration: Aggiunge tabella community_contacts per tracciare chi contatta gli autori
-- SQLite version

CREATE TABLE IF NOT EXISTS community_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign keys
    FOREIGN KEY (question_id) REFERENCES community_questions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE,
    
    -- Constraint univoco: un utente può incrementare il contatore una sola volta per domanda
    UNIQUE(question_id, user_id)
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_community_contacts_question ON community_contacts(question_id);
CREATE INDEX IF NOT EXISTS idx_community_contacts_user ON community_contacts(user_id);
