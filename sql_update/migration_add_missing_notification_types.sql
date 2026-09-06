-- Tipi di notifica usati dal codice ma mai censiti in notification_types.
-- send_notification() scarta in silenzio (solo un warning nei log) qualsiasi
-- type_key non presente o non attivo: senza queste righe il consulente non
-- riceve nulla quando viene pagato, e nessuno viene avvisato di un no-show
-- o del blocco del pagamento per contestazione.
--
-- SQLite. Idempotente: INSERT OR IGNORE sul type_key univoco.

INSERT OR IGNORE INTO notification_types
    (type_key, name, description, in_app, send_email, email_subject, email_template, is_active, created_at, updated_at)
VALUES
    ('payment_released', 'Pagamento rilasciato',
     'Il compenso della consulenza è stato trasferito al consulente',
     1, 0, NULL, NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('payment_hold', 'Pagamento sospeso',
     'Il pagamento resta bloccato per una contestazione in corso',
     1, 0, NULL, NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('booking_noshow', 'Assenza alla consulenza',
     'Uno dei partecipanti non si è presentato',
     1, 0, NULL, NULL, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('review_request', 'Richiesta recensione',
     'Email con il link per votare la consulenza',
     0, 1, 'Lascia una recensione su Ispiramy', 'review_request.html', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('review_reminder', 'Promemoria recensione',
     'Sollecito 24h dopo se la recensione non è stata lasciata',
     0, 1, 'Non dimenticare la recensione', 'review_reminder.html', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
    ('review_received', 'Recensione ricevuta',
     'Notifica al consulente quando riceve una recensione',
     1, 1, 'Hai ricevuto una recensione su Ispiramy', 'review_received.html', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);

-- I nomi template devono combaciare con quelli gestiti in
-- notification_email.generate_email_html, altrimenti l'email non viene generata.
UPDATE notification_types SET email_template = 'reminder_1h.html'
 WHERE type_key = 'reminder_1h' AND email_template <> 'reminder_1h.html';

UPDATE notification_types SET email_template = 'reminder_10min.html'
 WHERE type_key = 'reminder_10min' AND email_template <> 'reminder_10min.html';
