-- Migration: Aggiungi tabelle disputes e dispute_messages (SQLite)

CREATE TABLE IF NOT EXISTS disputes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id INTEGER NOT NULL REFERENCES booking(id),
    client_user_id INTEGER NOT NULL REFERENCES user(id),
    consultant_user_id INTEGER NOT NULL REFERENCES user(id),
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_disputes_booking_id ON disputes(booking_id);
CREATE INDEX IF NOT EXISTS idx_disputes_client_user_id ON disputes(client_user_id);
CREATE INDEX IF NOT EXISTS idx_disputes_consultant_user_id ON disputes(consultant_user_id);

CREATE TABLE IF NOT EXISTS dispute_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dispute_id INTEGER NOT NULL REFERENCES disputes(id),
    sender_user_id INTEGER REFERENCES user(id),
    is_admin BOOLEAN NOT NULL DEFAULT 0,
    message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dispute_messages_dispute_id ON dispute_messages(dispute_id);
