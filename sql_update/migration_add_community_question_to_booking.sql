-- Add community_question_id column to booking table (SQLite)
ALTER TABLE booking ADD COLUMN community_question_id INTEGER REFERENCES community_questions(id);
CREATE INDEX IF NOT EXISTS ix_booking_community_question_id ON booking(community_question_id);
