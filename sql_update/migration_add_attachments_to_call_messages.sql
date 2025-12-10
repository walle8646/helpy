-- Migration: Add attachments field to call_messages table
-- Description: Add support for file attachments in call messages

ALTER TABLE call_messages ADD COLUMN IF NOT EXISTS attachments TEXT;

-- Commit
COMMIT;
