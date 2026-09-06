-- Token del link "lascia una recensione" inviato via email (SQLite).
-- Serve per autorizzare l'invio della recensione senza login: prima il token
-- veniva generato e spedito ma mai salvato, quindi non era verificabile.
ALTER TABLE booking ADD COLUMN review_token VARCHAR(64) DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_booking_review_token ON booking(review_token);
