-- Migration: Add PayPal fields (SQLite)

-- User: email PayPal per ricevere pagamenti
ALTER TABLE user ADD COLUMN paypal_email TEXT;

-- Booking: PayPal payment tracking
ALTER TABLE booking ADD COLUMN paypal_order_id TEXT;
ALTER TABLE booking ADD COLUMN paypal_capture_id TEXT;
ALTER TABLE booking ADD COLUMN paypal_payout_id TEXT;
