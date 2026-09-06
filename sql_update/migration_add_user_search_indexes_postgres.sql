-- Indici sui campi usati dalla ricerca consulenti (PostgreSQL).
-- La query filtra su is_verified e, quando l'utente sceglie una categoria,
-- su category_id: senza indici ogni ricerca fa un sequential scan della
-- tabella user.
-- CONCURRENTLY evita di bloccare le scritture: va eseguito fuori da una
-- transazione (psql -f va bene, un blocco BEGIN/COMMIT no).
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_is_verified ON "user"(is_verified);
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_user_category_id ON "user"(category_id);
