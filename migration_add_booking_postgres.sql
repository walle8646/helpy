-- Migration: Add booking table
-- PostgreSQL version
-- Date: 2025-11-03

CREATE TABLE IF NOT EXISTS booking (
    id SERIAL PRIMARY KEY,
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
    cancelled_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_booking_client FOREIGN KEY (client_user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    CONSTRAINT fk_booking_consultant FOREIGN KEY (consultant_user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    CONSTRAINT fk_booking_availability FOREIGN KEY (availability_block_id) REFERENCES availability_block(id) ON DELETE SET NULL,
    CONSTRAINT fk_booking_cancelled_by FOREIGN KEY (cancelled_by) REFERENCES "user"(id) ON DELETE SET NULL,
    CONSTRAINT chk_booking_status CHECK (status IN ('pending', 'confirmed', 'completed', 'cancelled', 'no_show')),
    CONSTRAINT chk_payment_status CHECK (payment_status IN ('pending', 'paid', 'refunded', 'failed')),
    CONSTRAINT chk_duration CHECK (duration_minutes IN (30, 60, 90, 120))
);

-- Index per migliorare le performance delle query più comuni
CREATE INDEX IF NOT EXISTS idx_booking_client ON booking(client_user_id);
CREATE INDEX IF NOT EXISTS idx_booking_consultant ON booking(consultant_user_id);
CREATE INDEX IF NOT EXISTS idx_booking_date ON booking(booking_date);
CREATE INDEX IF NOT EXISTS idx_booking_consultant_date ON booking(consultant_user_id, booking_date);
CREATE INDEX IF NOT EXISTS idx_booking_status ON booking(status);
CREATE INDEX IF NOT EXISTS idx_booking_availability_block ON booking(availability_block_id);

-- Trigger function per aggiornare updated_at automaticamente
CREATE OR REPLACE FUNCTION update_booking_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger per chiamare la function
CREATE TRIGGER trigger_update_booking_timestamp
BEFORE UPDATE ON booking
FOR EACH ROW
EXECUTE FUNCTION update_booking_timestamp();

-- Commenti sulle colonne per documentazione
COMMENT ON TABLE booking IS 'Tabella per gestire le prenotazioni tra clienti e consulenti';
COMMENT ON COLUMN booking.status IS 'pending: in attesa di conferma, confirmed: confermata, completed: completata, cancelled: cancellata, no_show: cliente non si è presentato';
COMMENT ON COLUMN booking.payment_status IS 'pending: pagamento in attesa, paid: pagato, refunded: rimborsato, failed: fallito';
COMMENT ON COLUMN booking.duration_minutes IS 'Durata della consulenza: 30, 60, 90 o 120 minuti';
COMMENT ON COLUMN booking.availability_block_id IS 'Riferimento al blocco di disponibilità del consulente';
COMMENT ON COLUMN booking.meeting_link IS 'Link per la videochiamata (Zoom, Google Meet, etc.)';
