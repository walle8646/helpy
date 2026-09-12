-- La colonna della password conteneva hash MD5 (32 caratteri). Con bcrypt
-- l'hash e' lungo 60: senza questo ALTER ogni scrittura della password
-- (registrazione, reset, migrazione dell'hash al primo accesso) fallisce con
-- "value too long for type character varying(32)" e l'utente vede un errore 500.
--
-- All'avvio l'app lo applica da sola (database.ensure_column_widths): questo
-- file serve se si preferisce farlo a mano prima del rilascio.
ALTER TABLE "user" ALTER COLUMN password_md5 TYPE VARCHAR(255);

COMMENT ON COLUMN "user".password_md5 IS 'Hash bcrypt della password (il nome resta per compatibilità)';

-- Gli stati delle prenotazioni stanno in VARCHAR(20) e 'awaiting_acceptance'
-- ne occupa 19: spazio in piu' prima che uno stato nuovo rompa le scritture.
ALTER TABLE booking ALTER COLUMN status TYPE VARCHAR(30);
ALTER TABLE booking ALTER COLUMN payment_status TYPE VARCHAR(30);
