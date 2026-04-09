-- Migration: Add Stripe Connect fields to user table (PostgreSQL)
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS stripe_account_id TEXT;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS stripe_onboarding_complete BOOLEAN DEFAULT FALSE;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS platform_fee_percent INTEGER DEFAULT 20;

CREATE INDEX IF NOT EXISTS idx_user_stripe_account ON "user"(stripe_account_id);
