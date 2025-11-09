-- Migration: Add Stripe payment fields to booking table
-- Created: 2024-11-09

ALTER TABLE booking ADD COLUMN stripe_checkout_session_id TEXT;
ALTER TABLE booking ADD COLUMN stripe_payment_intent_id TEXT;

CREATE INDEX idx_booking_stripe_session ON booking(stripe_checkout_session_id);
CREATE INDEX idx_booking_stripe_payment ON booking(stripe_payment_intent_id);
