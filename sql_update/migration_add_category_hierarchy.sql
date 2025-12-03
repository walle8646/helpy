-- Aggiungi colonna parent_id alla tabella category
ALTER TABLE category ADD COLUMN parent_id INT NULL;
ALTER TABLE category ADD FOREIGN KEY (parent_id) REFERENCES category(id) ON DELETE SET NULL;

-- Aggiungi colonna is_primary per indicare se è una categoria principale
ALTER TABLE category ADD COLUMN is_primary BOOLEAN DEFAULT FALSE;
