-- Migration: Add payment hold fields to booking table (SQLite)
ALTER TABLE booking ADD COLUMN stripe_transfer_id TEXT;
ALTER TABLE booking ADD COLUMN payment_held_until DATETIME;
ALTER TABLE booking ADD COLUMN payment_released_at DATETIME;
ALTER TABLE booking ADD COLUMN refund_amount DECIMAL(10,2);
