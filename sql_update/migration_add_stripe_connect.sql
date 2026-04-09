-- Migration: Add Stripe Connect fields to user table (SQLite)
ALTER TABLE user ADD COLUMN stripe_account_id TEXT;
ALTER TABLE user ADD COLUMN stripe_onboarding_complete BOOLEAN DEFAULT 0;
ALTER TABLE user ADD COLUMN platform_fee_percent INTEGER DEFAULT 20;

CREATE INDEX IF NOT EXISTS idx_user_stripe_account ON user(stripe_account_id);
