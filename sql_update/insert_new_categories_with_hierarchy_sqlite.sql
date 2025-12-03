-- Abilita i vincoli di chiave esterna in SQLite
PRAGMA foreign_keys = ON;

-- Crea la tabella category_hierarchy per gestire le relazioni gerarchiche (SQLite)
CREATE TABLE IF NOT EXISTS category_hierarchy (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_category_id INTEGER NOT NULL,
    child_category_id INTEGER NOT NULL,
    position INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_category_id) REFERENCES category(id) ON DELETE CASCADE,
    FOREIGN KEY (child_category_id) REFERENCES category(id) ON DELETE CASCADE,
    UNIQUE (parent_category_id, child_category_id)
);

-- Aggiungi indice per ricerche veloci
CREATE INDEX IF NOT EXISTS idx_parent_category ON category_hierarchy(parent_category_id);
CREATE INDEX IF NOT EXISTS idx_child_category ON category_hierarchy(child_category_id);

-- Cancella le categorie attuali
DELETE FROM category;
DELETE FROM sqlite_sequence WHERE name='category';

-- Inserisci solo le 8 categorie principali
INSERT INTO category (id, name, slug, icon, description, color) VALUES
(1, 'Lavoro & Carriera', 'lavoro-carriera', '💼', 'Consulenze sulla carriera professionale', '#2196F3'),
(2, 'Vita all''Estero', 'vita-estero', '🌍', 'Consulenze su trasferimenti e vita all''estero', '#FF9800'),
(3, 'Viaggiatori & Nomadi Digitali', 'nomadi-digitali', '🌏', 'Consulenze per nomadi digitali e viaggiatori', '#4CAF50'),
(4, 'Esperienze di Vita', 'esperienze-vita', '🎯', 'Consulenze su esperienze di vita e cambiamenti', '#9C27B0'),
(5, 'Settori Specifici', 'settori-specifici', '⚙️', 'Consulenze su settori specifici e specializzati', '#F44336'),
(6, 'Mentorship & Crescita Personale', 'mentorship', '🌟', 'Mentorship e sviluppo personale', '#00BCD4'),
(7, 'Sport & Wellness', 'sport-wellness', '🏋️', 'Consulenze su sport, fitness e benessere', '#E91E63'),
(8, 'Gaming & Creators', 'gaming-creators', '🎮', 'Consulenze per gamer e content creator', '#00A86B');

-- Inserisci tutte le sottocategorie con IDs fissi
INSERT INTO category (id, name, slug, icon, description, color) VALUES
(9, 'Come trovare lavoro / cambiare lavoro', 'trovare-lavoro', '🔍', 'Strategie per trovare lavoro e cambiare carriera', '#2196F3'),
(10, 'Scrittura CV e profilo LinkedIn', 'cv-linkedin', '📝', 'Aiuto nella stesura di CV e profili professionali', '#2196F3'),
(11, 'Preparazione ai colloqui', 'colloqui', '🎤', 'Preparazione e coaching per colloqui di lavoro', '#2196F3'),
(12, 'Carriera aziendale', 'carriera-aziendale', '📈', 'Sviluppo di carriera all''interno di aziende', '#2196F3'),
(13, 'Freelancing e consulenza', 'freelancing', '🚀', 'Consigli per freelancer e consulenti', '#2196F3'),
(14, 'Orientamento professionale', 'orientamento-prof', '🧭', 'Orientamento e scelta professionale', '#2196F3'),
(15, 'Trasferirsi in un nuovo Paese', 'trasferimento', '✈️', 'Pianificazione e realizzazione del trasferimento', '#FF9800'),
(16, 'Permesso di soggiorno / visti', 'visti', '📄', 'Informazioni su visti e permessi di soggiorno', '#FF9800'),
(17, 'Trovare casa all''estero', 'casa-estero', '🏠', 'Ricerca e affitto di alloggi all''estero', '#FF9800'),
(18, 'Trovare lavoro all''estero', 'lavoro-estero', '💼', 'Ricerca di lavoro in altri paesi', '#FF9800'),
(19, 'Adattamento culturale', 'adattamento-cultura', '🌐', 'Consigli per adattarsi a nuove culture', '#FF9800'),
(20, 'Gestione della burocrazia locale', 'burocrazia', '🏛️', 'Navigare la burocrazia locale', '#FF9800'),
(21, 'Vita da expat & integrazione', 'expat-integrazione', '🤝', 'Comunità di expat e integrazione sociale', '#FF9800'),
(22, 'Organizzazione viaggi', 'organizzazione-viaggi', '📋', 'Pianificazione e organizzazione di viaggi', '#4CAF50'),
(23, 'Itinerari personalizzati', 'itinerari', '🗺️', 'Creazione di itinerari su misura', '#4CAF50'),
(24, 'Lavorare da remoto in giro per il mondo', 'remote-lavoro', '💻', 'Consigli per lavorare mentre si viaggia', '#4CAF50'),
(25, 'Gestione budget di viaggio', 'budget-viaggio', '💰', 'Pianificazione finanziaria per viaggi', '#4CAF50'),
(26, 'Vita da nomade digitale', 'nomade-digitale', '🛫', 'Lifestyle e organizzazione da nomade', '#4CAF50'),
(27, 'Consigli su sicurezza nelle destinazioni', 'sicurezza-viaggi', '🔒', 'Sicurezza e prevenzione durante i viaggi', '#4CAF50'),
(28, 'Traslochi e cambi di città', 'traslochi', '📦', 'Organizzazione traslochi e cambi di residenza', '#9C27B0'),
(29, 'Gestione di eventi importanti', 'eventi-importanti', '🎊', 'Gestione di matrimoni, figli e grandi eventi', '#9C27B0'),
(30, 'Gestione dei fallimenti', 'gestione-fallimenti', '💪', 'Come affrontare e superare i fallimenti', '#9C27B0'),
(31, 'Come ricominciare dopo periodi difficili', 'ricominciare', '🌱', 'Ripartire dopo crisi o periodi difficili', '#9C27B0'),
(32, 'Problemi comuni nella vita quotidiana', 'problemi-quotidiani', '🔧', 'Soluzioni a problemi comuni della vita', '#9C27B0'),
(33, 'Relazioni familiari & personali', 'relazioni', '❤️', 'Consigli su relazioni personali e familiari', '#9C27B0'),
(34, 'Immobiliare', 'immobiliare', '🏢', 'Consulenze su acquisto, vendita e affitto di immobili', '#F44336'),
(35, 'Ristrutturazioni e home improvement', 'ristrutturazioni', '🛠️', 'Consigli per ristrutturazioni e migliorie abitative', '#F44336'),
(36, 'Auto, moto e veicoli', 'veicoli', '🚗', 'Consulenze su acquisto e manutenzione di veicoli', '#F44336'),
(37, 'Food & hospitality', 'food-hospitality', '🍽️', 'Consigli su ristorazione e ospitalità', '#F44336'),
(38, 'Moda & styling', 'moda-styling', '👗', 'Consulenze su moda, stile e immagine personale', '#F44336'),
(39, 'Educazione e formazione', 'educazione', '🎓', 'Consulenze su percorsi educativi e formazione', '#F44336'),
(40, 'Finanza personale', 'finanza-personale', '💳', 'Consigli su finanza personale e investimenti', '#F44336'),
(41, 'Startup & imprenditoria', 'startup', '🚀', 'Consigli per startuppisti e imprenditori', '#F44336'),
(42, 'Life coaching peer-to-peer', 'life-coaching', '👥', 'Life coaching e supporto tra pari', '#00BCD4'),
(43, 'Supporto motivazionale', 'motivazione', '⚡', 'Supporto e motivazione personale', '#00BCD4'),
(44, 'Gestione quotidiana dello stress', 'stress-management', '🧘', 'Tecniche per gestire lo stress quotidiano', '#00BCD4'),
(45, 'Definizione obiettivi', 'obiettivi', '🎯', 'Aiuto nella definizione e raggiungimento di obiettivi', '#00BCD4'),
(46, 'Costruire abitudini efficaci', 'abitudini', '📅', 'Sviluppo di abitudini positive e durature', '#00BCD4'),
(47, 'Comunicazione & assertività', 'comunicazione', '💬', 'Migliorare comunicazione e assertività', '#00BCD4'),
(48, 'Fitness & allenamento', 'fitness', '💪', 'Programmi di allenamento e fitness', '#E91E63'),
(49, 'Nutrizione personale', 'nutrizione', '🥗', 'Consigli nutrizionali personali (non clinici)', '#E91E63'),
(50, 'Running, cycling, palestra', 'cardio-palestra', '🏃', 'Specialità in running, cycling e allenamenti', '#E91E63'),
(51, 'Programmi di allenamento personalizzati', 'programmi-allenamento', '📊', 'Creazione di programmi su misura', '#E91E63'),
(52, 'Riattivazione dopo periodi di stop', 'riattivazione', '🔄', 'Ripresa graduale dell''attività fisica', '#E91E63'),
(53, 'Esperienze sportive agonistiche', 'sport-agonistici', '🏅', 'Preparazione a competizioni sportive', '#E91E63'),
(54, 'Strategie di gioco', 'strategie-gioco', '🎯', 'Strategie avanzate di gaming', '#00A86B'),
(55, 'Come crescere su Twitch / YouTube / TikTok', 'social-media-growth', '📱', 'Strategie di crescita su piattaforme social', '#00A86B'),
(56, 'Set-up per gaming e streaming', 'setup-gaming', '💻', 'Configurazione ottimale per gaming e streaming', '#00A86B'),
(57, 'Editing video', 'video-editing', '🎬', 'Tecniche e strumenti per editing video', '#00A86B'),
(58, 'Brand image da creator', 'brand-creator', '✨', 'Costruzione di brand personale per creator', '#00A86B'),
(59, 'Community building', 'community-building', '🌐', 'Creazione e gestione di comunità online', '#00A86B');

-- Inserisci la gerarchia nella tabella category_hierarchy
-- Lavoro & Carriera (id=1)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(1, 9, 0), (1, 10, 1), (1, 11, 2), (1, 12, 3), (1, 13, 4), (1, 14, 5);

-- Vita all'Estero (id=2)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(2, 15, 0), (2, 16, 1), (2, 17, 2), (2, 18, 3), (2, 19, 4), (2, 20, 5), (2, 21, 6);

-- Viaggiatori & Nomadi Digitali (id=3)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(3, 22, 0), (3, 23, 1), (3, 24, 2), (3, 25, 3), (3, 26, 4), (3, 27, 5);

-- Esperienze di Vita (id=4)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(4, 28, 0), (4, 29, 1), (4, 30, 2), (4, 31, 3), (4, 32, 4), (4, 33, 5);

-- Settori Specifici (id=5)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(5, 34, 0), (5, 35, 1), (5, 36, 2), (5, 37, 3), (5, 38, 4), (5, 39, 5), (5, 40, 6), (5, 41, 7);

-- Mentorship & Crescita Personale (id=6)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(6, 42, 0), (6, 43, 1), (6, 44, 2), (6, 45, 3), (6, 46, 4), (6, 47, 5);

-- Sport & Wellness (id=7)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(7, 48, 0), (7, 49, 1), (7, 50, 2), (7, 51, 3), (7, 52, 4), (7, 53, 5);

-- Gaming & Creators (id=8)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(8, 54, 0), (8, 55, 1), (8, 56, 2), (8, 57, 3), (8, 58, 4), (8, 59, 5);
