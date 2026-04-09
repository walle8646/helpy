-- Migration: Add payment hold fields to booking table (PostgreSQL)
ALTER TABLE booking ADD COLUMN IF NOT EXISTS stripe_transfer_id TEXT;
ALTER TABLE booking ADD COLUMN IF NOT EXISTS payment_held_until TIMESTAMP;
ALTER TABLE booking ADD COLUMN IF NOT EXISTS payment_released_at TIMESTAMP;
ALTER TABLE booking ADD COLUMN IF NOT EXISTS refund_amount DECIMAL(10,2);

-- Aggiorna il CHECK constraint per includere i nuovi stati
ALTER TABLE booking DROP CONSTRAINT IF EXISTS chk_payment_status;
ALTER TABLE booking ADD CONSTRAINT chk_payment_status CHECK (payment_status IN ('pending', 'held', 'paid', 'released', 'refunded', 'partially_refunded', 'failed'));
