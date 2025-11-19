-- Cancella la tabella corrotta
DROP TABLE IF EXISTS availability_block;

-- Ricrea la tabella con la struttura corretta
CREATE TABLE availability_block (
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

-- Crea indice su user_id e date per velocizzare le query
CREATE INDEX idx_availability_block_user_date ON availability_block(user_id, date);
