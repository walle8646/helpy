-- Crea la tabella category_hierarchy per gestire le relazioni gerarchiche (PostgreSQL)
CREATE TABLE IF NOT EXISTS category_hierarchy (
    id SERIAL PRIMARY KEY,
    parent_category_id INT NOT NULL,
    child_category_id INT NOT NULL,
    position INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_category_id) REFERENCES category(id) ON DELETE CASCADE,
    FOREIGN KEY (child_category_id) REFERENCES category(id) ON DELETE CASCADE,
    UNIQUE (parent_category_id, child_category_id)
);

-- Aggiungi indice per ricerche veloci
CREATE INDEX idx_parent_category ON category_hierarchy(parent_category_id);
CREATE INDEX idx_child_category ON category_hierarchy(child_category_id);
