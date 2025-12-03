-- Aggiunta tabella availability_block per gestione disponibilità consulenze (PostgreSQL)
CREATE TABLE IF NOT EXISTS availability_block (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    total_minutes INTEGER NOT NULL,
    booked_minutes INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'available',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_availability_user FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_availability_user_date ON availability_block(user_id, date);
CREATE INDEX IF NOT EXISTS idx_availability_date ON availability_block(date);
CREATE INDEX IF NOT EXISTS idx_availability_status ON availability_block(status);

-- Commenti
COMMENT ON TABLE availability_block IS 'Blocchi di disponibilità per consulenze';
COMMENT ON COLUMN availability_block.status IS 'Status: available, booked, unavailable';
COMMENT ON COLUMN availability_block.start_time IS 'Ora inizio in formato HH:MM';
COMMENT ON COLUMN availability_block.end_time IS 'Ora fine in formato HH:MM';
COMMENT ON COLUMN availability_block.total_minutes IS 'Durata totale della fascia oraria in minuti';
COMMENT ON COLUMN availability_block.booked_minutes IS 'Minuti già prenotati (per prenotazioni parziali)';
