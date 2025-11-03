-- Migration: Add booking table
-- SQLite version
-- Date: 2025-11-03

CREATE TABLE IF NOT EXISTS booking (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_user_id INTEGER NOT NULL,
    consultant_user_id INTEGER NOT NULL,
    availability_block_id INTEGER,
    booking_date DATE NOT NULL,
    start_time VARCHAR(5) NOT NULL,
    end_time VARCHAR(5) NOT NULL,
    duration_minutes INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    price DECIMAL(10, 2),
    payment_status VARCHAR(20) DEFAULT 'pending',
    payment_method VARCHAR(50),
    transaction_id VARCHAR(100),
    meeting_link VARCHAR(500),
    client_notes TEXT,
    consultant_notes TEXT,
    cancellation_reason TEXT,
    cancelled_by INTEGER,
    cancelled_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (client_user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (consultant_user_id) REFERENCES user(id) ON DELETE CASCADE,
    FOREIGN KEY (availability_block_id) REFERENCES availability_block(id) ON DELETE SET NULL,
    FOREIGN KEY (cancelled_by) REFERENCES user(id) ON DELETE SET NULL,
    CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled', 'no_show')),
    CHECK (payment_status IN ('pending', 'paid', 'refunded', 'failed')),
    CHECK (duration_minutes IN (30, 60, 90, 120))
);

-- Index per migliorare le performance delle query più comuni
CREATE INDEX IF NOT EXISTS idx_booking_client ON booking(client_user_id);
CREATE INDEX IF NOT EXISTS idx_booking_consultant ON booking(consultant_user_id);
CREATE INDEX IF NOT EXISTS idx_booking_date ON booking(booking_date);
CREATE INDEX IF NOT EXISTS idx_booking_consultant_date ON booking(consultant_user_id, booking_date);
CREATE INDEX IF NOT EXISTS idx_booking_status ON booking(status);
CREATE INDEX IF NOT EXISTS idx_booking_availability_block ON booking(availability_block_id);

-- Trigger per aggiornare updated_at automaticamente
CREATE TRIGGER IF NOT EXISTS update_booking_timestamp 
AFTER UPDATE ON booking
BEGIN
    UPDATE booking SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
