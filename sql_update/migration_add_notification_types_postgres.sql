-- Migration: Aggiunge tabella notification_types per configurare invio notifiche
-- PostgreSQL version

CREATE TABLE IF NOT EXISTS notification_types (
    id SERIAL PRIMARY KEY,
    type_key VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    
    -- Flags configurazione
    in_app BOOLEAN DEFAULT TRUE NOT NULL,
    send_email BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Configurazione email
    email_subject VARCHAR(200),
    email_template VARCHAR(100),
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notification_types_key ON notification_types(type_key);

-- Popola con i 3 tipi di notifica esistenti
INSERT INTO notification_types (type_key, name, description, in_app, send_email, email_subject, email_template) VALUES
(
    'booking_confirmed',
    'Prenotazione Confermata',
    'Notifica al consulente quando riceve una nuova prenotazione',
    TRUE,  -- in_app: SI
    TRUE,  -- send_email: SI
    'Nuova Prenotazione Ricevuta! 📅',
    'booking_confirmed.html'
),
(
    'reminder_1h',
    'Promemoria 1 Ora Prima',
    'Reminder inviato 1 ora prima della consulenza',
    TRUE,  -- in_app: SI
    TRUE,  -- send_email: SI
    'Promemoria: Consulenza tra 1 ora 🔔',
    'reminder_1h.html'
),
(
    'reminder_10min',
    'Promemoria 10 Minuti Prima',
    'Reminder inviato 10 minuti prima della consulenza',
    TRUE,  -- in_app: SI
    TRUE,  -- send_email: SI
    'La tua consulenza inizia tra 10 minuti! ⏰',
    'reminder_10min.html'
)
ON CONFLICT (type_key) DO NOTHING;
