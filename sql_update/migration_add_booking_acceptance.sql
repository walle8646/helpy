-- Richieste di consulenza da accettare (SQLite, sviluppo locale).
-- Vedi migration_add_booking_acceptance_postgres.sql. SQLite non ha i vincoli
-- CHECK sugli stati, quindi bastano le colonne e i tipi di notifica.

ALTER TABLE "user" ADD COLUMN auto_accept_bookings BOOLEAN NOT NULL DEFAULT 1;
ALTER TABLE booking ADD COLUMN acceptance_deadline TIMESTAMP DEFAULT NULL;
ALTER TABLE booking ADD COLUMN paypal_authorization_id VARCHAR(64) DEFAULT NULL;

INSERT OR IGNORE INTO notification_types (type_key, name, description, in_app, send_email, email_subject, email_template, is_active, created_at, updated_at) VALUES
    ('booking_request', 'Richiesta di consulenza da accettare', 'Al consulente che conferma a mano: una nuova richiesta da accettare o rifiutare', 1, 1, '📩 Nuova richiesta di consulenza da confermare', 'booking_request.html', 1, datetime('now'), datetime('now')),
    ('booking_accepted', 'Richiesta di consulenza accettata', 'Al cliente quando il consulente accetta la richiesta', 1, 1, '✅ Il consulente ha accettato la tua richiesta', 'booking_accepted.html', 1, datetime('now'), datetime('now')),
    ('booking_request_expired', 'Richiesta di consulenza scaduta', 'Al cliente quando il consulente non risponde entro la scadenza', 1, 1, '⌛ Il consulente non ha risposto alla tua richiesta', 'booking_request_expired.html', 1, datetime('now'), datetime('now')),
    ('booking_refused', 'Prenotazione rifiutata', 'Quando una prenotazione viene rifiutata', 1, 1, '❌ Prenotazione rifiutata', 'booking_refused.html', 1, datetime('now'), datetime('now'));
