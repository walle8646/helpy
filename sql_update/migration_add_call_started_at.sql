-- ========== SQLite ==========
ALTER TABLE booking ADD COLUMN call_started_at DATETIME DEFAULT NULL;

-- ========== PostgreSQL ==========
ALTER TABLE booking ADD COLUMN call_started_at TIMESTAMP DEFAULT NULL;
