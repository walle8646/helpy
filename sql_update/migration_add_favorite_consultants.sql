-- Migration: Add favorite_consultants table (SQLite)
CREATE TABLE IF NOT EXISTS favorite_consultants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    consultant_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id),
    FOREIGN KEY (consultant_id) REFERENCES user(id)
);

CREATE INDEX IF NOT EXISTS ix_favorite_consultants_user_id ON favorite_consultants(user_id);
CREATE INDEX IF NOT EXISTS ix_favorite_consultants_consultant_id ON favorite_consultants(consultant_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_favorite_consultants_unique ON favorite_consultants(user_id, consultant_id);
