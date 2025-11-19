-- Migration: Aggiungi tabella per tracciare i reset dei contatori messaggi
-- Data: 2025-11-15
-- Descrizione: Traccia quando il contatore messaggi viene resetato tra due utenti

-- ===== SQLite =====
CREATE TABLE IF NOT EXISTS message_counter_reset (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    user1_id INTEGER NOT NULL,
    user2_id INTEGER NOT NULL,
    booking_id INTEGER,
    reset_reason TEXT DEFAULT 'payment_booking',
    reset_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversation(id) ON DELETE CASCADE,
    FOREIGN KEY (user1_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (user2_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (booking_id) REFERENCES booking(id) ON DELETE SET NULL,
    UNIQUE(conversation_id, booking_id)
);

CREATE INDEX IF NOT EXISTS idx_message_counter_reset_conversation ON message_counter_reset(conversation_id);
CREATE INDEX IF NOT EXISTS idx_message_counter_reset_booking ON message_counter_reset(booking_id);
CREATE INDEX IF NOT EXISTS idx_message_counter_reset_reset_at ON message_counter_reset(reset_at);

-- ===== PostgreSQL (commenta SQLite sopra e usa questa per PostgreSQL) =====
-- CREATE TABLE IF NOT EXISTS message_counter_reset (
--     id SERIAL PRIMARY KEY,
--     conversation_id INTEGER NOT NULL,
--     user1_id INTEGER NOT NULL,
--     user2_id INTEGER NOT NULL,
--     booking_id INTEGER,
--     reset_reason VARCHAR(50) DEFAULT 'payment_booking',
--     reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
--     FOREIGN KEY (conversation_id) REFERENCES conversation(id) ON DELETE CASCADE,
--     FOREIGN KEY (user1_id) REFERENCES "user"(id) ON DELETE CASCADE,
--     FOREIGN KEY (user2_id) REFERENCES "user"(id) ON DELETE CASCADE,
--     FOREIGN KEY (booking_id) REFERENCES booking(id) ON DELETE SET NULL,
--     UNIQUE(conversation_id, booking_id)
-- );
--
-- CREATE INDEX IF NOT EXISTS idx_message_counter_reset_conversation ON message_counter_reset(conversation_id);
-- CREATE INDEX IF NOT EXISTS idx_message_counter_reset_booking ON message_counter_reset(booking_id);
-- CREATE INDEX IF NOT EXISTS idx_message_counter_reset_reset_at ON message_counter_reset(reset_at);
