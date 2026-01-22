-- Migration: Aggiunge tabella per tracciare le notifiche di richieste di categoria
-- Data: 2026-01-22

CREATE TABLE IF NOT EXISTS category_request_notifications (
    id SERIAL PRIMARY KEY,
    consultant_user_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_consultant_user FOREIGN KEY (consultant_user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    CONSTRAINT fk_question FOREIGN KEY (question_id) REFERENCES community_questions(id) ON DELETE CASCADE
);

-- Indici per performance
CREATE INDEX idx_category_request_notifications_consultant ON category_request_notifications(consultant_user_id);
CREATE INDEX idx_category_request_notifications_question ON category_request_notifications(question_id);
CREATE INDEX idx_category_request_notifications_is_read ON category_request_notifications(is_read);
CREATE INDEX idx_category_request_notifications_consultant_is_read ON category_request_notifications(consultant_user_id, is_read);
