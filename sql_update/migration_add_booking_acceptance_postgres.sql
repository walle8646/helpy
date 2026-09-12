-- Richieste di consulenza da accettare (PostgreSQL).
-- Il consulente con la conferma automatica spenta riceve le prenotazioni come
-- richieste: il pagamento è solo autorizzato e si incassa quando accetta.
-- All'avvio l'app applica da sola colonne, vincoli e tipi di notifica
-- (database.ensure_added_columns / ensure_check_constraints,
-- notification_types.ensure_notification_types): questo file serve se si
-- preferisce applicarli a mano prima del deploy.

ALTER TABLE "user" ADD COLUMN IF NOT EXISTS auto_accept_bookings BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE booking ADD COLUMN IF NOT EXISTS acceptance_deadline TIMESTAMP DEFAULT NULL;
ALTER TABLE booking ADD COLUMN IF NOT EXISTS paypal_authorization_id VARCHAR(64) DEFAULT NULL;

COMMENT ON COLUMN "user".auto_accept_bookings IS 'Se false le prenotazioni dirette vanno accettate dal consulente';
COMMENT ON COLUMN booking.acceptance_deadline IS 'Entro quando il consulente deve accettare la richiesta (ora italiana)';
COMMENT ON COLUMN booking.paypal_authorization_id IS 'Autorizzazione PayPal da incassare o annullare';

-- Nuovi stati: awaiting_acceptance (richiesta in attesa), authorized (importo
-- bloccato non incassato), voided (blocco annullato)
ALTER TABLE booking DROP CONSTRAINT IF EXISTS chk_booking_status;
ALTER TABLE booking ADD CONSTRAINT chk_booking_status CHECK (status IN ('pending', 'pending_payment', 'awaiting_acceptance', 'confirmed', 'completed', 'cancelled', 'no_show')) NOT VALID;
ALTER TABLE booking DROP CONSTRAINT IF EXISTS chk_payment_status;
ALTER TABLE booking ADD CONSTRAINT chk_payment_status CHECK (payment_status IN ('pending', 'authorized', 'held', 'paid', 'released', 'refunded', 'partially_refunded', 'voided', 'failed')) NOT VALID;

INSERT INTO notification_types (type_key, name, description, in_app, send_email, email_subject, email_template, is_active, created_at, updated_at) VALUES
    ('booking_request', 'Richiesta di consulenza da accettare', 'Al consulente che conferma a mano: una nuova richiesta da accettare o rifiutare', true, true, '📩 Nuova richiesta di consulenza da confermare', 'booking_request.html', true, NOW(), NOW()),
    ('booking_accepted', 'Richiesta di consulenza accettata', 'Al cliente quando il consulente accetta la richiesta', true, true, '✅ Il consulente ha accettato la tua richiesta', 'booking_accepted.html', true, NOW(), NOW()),
    ('booking_request_expired', 'Richiesta di consulenza scaduta', 'Al cliente quando il consulente non risponde entro la scadenza', true, true, '⌛ Il consulente non ha risposto alla tua richiesta', 'booking_request_expired.html', true, NOW(), NOW()),
    ('booking_refused', 'Prenotazione rifiutata', 'Quando una prenotazione viene rifiutata', true, true, '❌ Prenotazione rifiutata', 'booking_refused.html', true, NOW(), NOW()),
    ('booking_confirmed_client', 'Consulenza confermata (cliente)', 'Al cliente quando la prenotazione è confermata e pagata', true, true, '✅ La tua consulenza è confermata', 'booking_confirmed_client.html', true, NOW(), NOW()),
    ('booking_cancelled', 'Consulenza annullata', 'All''altro partecipante quando una consulenza viene annullata', true, true, '❌ Consulenza annullata', 'booking_cancelled.html', true, NOW(), NOW())
ON CONFLICT (type_key) DO NOTHING;
