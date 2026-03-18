-- Migration: Add favorite_consultants table (PostgreSQL)
CREATE TABLE IF NOT EXISTS favorite_consultants (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id),
    consultant_id INTEGER NOT NULL REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_favorite_consultants_user_id ON favorite_consultants(user_id);
CREATE INDEX IF NOT EXISTS ix_favorite_consultants_consultant_id ON favorite_consultants(consultant_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_favorite_consultants_unique ON favorite_consultants(user_id, consultant_id);
