-- Migration: Update booking status constraint to include 'pending_payment' (PostgreSQL)
-- Required for PayPal integration which creates bookings in pending_payment status

ALTER TABLE booking DROP CONSTRAINT IF EXISTS chk_booking_status;
ALTER TABLE booking ADD CONSTRAINT chk_booking_status CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled', 'no_show', 'pending_payment'));
