-- Migration: Add ConsultationOffer table
-- Created: 2024-11-08

CREATE TABLE consultation_offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    consultant_user_id INTEGER NOT NULL,
    client_user_id INTEGER NOT NULL,
    price REAL NOT NULL CHECK(price > 0),
    duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
    status VARCHAR(20) DEFAULT 'pending',
    booking_id INTEGER,
    message TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (consultant_user_id) REFERENCES user(id),
    FOREIGN KEY (client_user_id) REFERENCES user(id),
    FOREIGN KEY (booking_id) REFERENCES booking(id)
);

-- Indexes for performance
CREATE INDEX idx_consultation_offers_consultant ON consultation_offers(consultant_user_id);
CREATE INDEX idx_consultation_offers_client ON consultation_offers(client_user_id);
CREATE INDEX idx_consultation_offers_status ON consultation_offers(status);
CREATE INDEX idx_consultation_offers_expires ON consultation_offers(expires_at);
