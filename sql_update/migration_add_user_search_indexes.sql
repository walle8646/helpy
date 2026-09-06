-- Indici sui campi usati dalla ricerca consulenti (SQLite).
-- La query filtra su is_verified e, quando l'utente sceglie una categoria,
-- su category_id: senza indici ogni ricerca fa una scansione completa
-- della tabella user.
CREATE INDEX IF NOT EXISTS ix_user_is_verified ON "user"(is_verified);
CREATE INDEX IF NOT EXISTS ix_user_category_id ON "user"(category_id);
