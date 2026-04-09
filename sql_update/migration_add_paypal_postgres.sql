-- Migration: Add PayPal fields (PostgreSQL)

-- User: email PayPal per ricevere pagamenti
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS paypal_email TEXT;

-- Booking: PayPal payment tracking
ALTER TABLE booking ADD COLUMN IF NOT EXISTS paypal_order_id TEXT;
ALTER TABLE booking ADD COLUMN IF NOT EXISTS paypal_capture_id TEXT;
ALTER TABLE booking ADD COLUMN IF NOT EXISTS paypal_payout_id TEXT;
