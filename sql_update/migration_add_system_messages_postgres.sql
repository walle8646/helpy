-- Migration: Add system message support to messages table (PostgreSQL)
-- Created: 2024-11-08

ALTER TABLE messages ADD COLUMN is_system_message BOOLEAN DEFAULT FALSE;
ALTER TABLE messages ADD COLUMN consultation_offer_id INTEGER REFERENCES consultation_offers(id);

CREATE INDEX idx_messages_consultation_offer ON messages(consultation_offer_id);
