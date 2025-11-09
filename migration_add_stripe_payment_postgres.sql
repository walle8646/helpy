-- Migration: Add Stripe payment fields to booking table (PostgreSQL)
-- Created: 2024-11-09

ALTER TABLE booking ADD COLUMN stripe_checkout_session_id VARCHAR(255);
ALTER TABLE booking ADD COLUMN stripe_payment_intent_id VARCHAR(255);

CREATE INDEX idx_booking_stripe_session ON booking(stripe_checkout_session_id);
CREATE INDEX idx_booking_stripe_payment ON booking(stripe_payment_intent_id);
