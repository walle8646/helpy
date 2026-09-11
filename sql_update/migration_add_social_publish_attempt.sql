-- Contatore dei ritentativi di pubblicazione dei post social (SQLite).
-- Entra nell'external_id inviato a Post for Me: senza, un post rifiutato dal
-- social veniva riconosciuto come "già inviato" e non si poteva ripubblicare
-- nemmeno dopo averlo corretto.
ALTER TABLE social_drafts ADD COLUMN publish_attempt INTEGER NOT NULL DEFAULT 0;
