-- Migration: Aggiungi tabelle disputes e dispute_messages (PostgreSQL)

CREATE TABLE IF NOT EXISTS disputes (
    id SERIAL PRIMARY KEY,
    booking_id INTEGER NOT NULL REFERENCES booking(id),
    client_user_id INTEGER NOT NULL REFERENCES "user"(id),
    consultant_user_id INTEGER NOT NULL REFERENCES "user"(id),
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_disputes_booking_id ON disputes(booking_id);
CREATE INDEX IF NOT EXISTS idx_disputes_client_user_id ON disputes(client_user_id);
CREATE INDEX IF NOT EXISTS idx_disputes_consultant_user_id ON disputes(consultant_user_id);

CREATE TABLE IF NOT EXISTS dispute_messages (
    id SERIAL PRIMARY KEY,
    dispute_id INTEGER NOT NULL REFERENCES disputes(id),
    sender_user_id INTEGER REFERENCES "user"(id),
    is_admin BOOLEAN NOT NULL DEFAULT FALSE,
    message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dispute_messages_dispute_id ON dispute_messages(dispute_id);
