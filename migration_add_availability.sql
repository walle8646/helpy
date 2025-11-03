-- Aggiunta tabella availability_block per gestione disponibilità consulenze
CREATE TABLE IF NOT EXISTS availability_block (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    total_minutes INTEGER NOT NULL,
    booked_minutes INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'available',
    is_active BOOLEAN NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id)
);

-- Indici per performance
CREATE INDEX IF NOT EXISTS idx_availability_user_date ON availability_block(user_id, date);
CREATE INDEX IF NOT EXISTS idx_availability_date ON availability_block(date);
CREATE INDEX IF NOT EXISTS idx_availability_status ON availability_block(status);

-- Commenti
-- status possibili: 'available', 'booked', 'unavailable'
-- start_time e end_time in formato "HH:MM" (es: "09:00", "17:30")
-- total_minutes: durata totale della fascia oraria
-- booked_minutes: minuti già prenotati (per future implementazioni prenotazioni parziali)
