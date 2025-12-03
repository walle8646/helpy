-- ============================================================================
-- MIGRATION COMPLETA: Applica le 7 nuove categorie con is_principal
-- SQLite - Esegui questo script per aggiornare il database
-- ============================================================================

PRAGMA foreign_keys = ON;

-- Step 1: Aggiungi la colonna is_principal se non esiste
ALTER TABLE category ADD COLUMN is_principal BOOLEAN DEFAULT 0;

-- Step 2: Cancella tutti i dati dalla tabella category_hierarchy
DELETE FROM category_hierarchy;

-- Step 3: Cancella tutti i dati dalla tabella category
DELETE FROM category;
DELETE FROM sqlite_sequence WHERE name='category';

-- ============================================================================
-- Step 4: INSERIMENTO CATEGORIE PRINCIPALI (7 nuove)
-- ============================================================================

INSERT INTO category (id, name, slug, icon, description, color, target, is_principal) VALUES
(1, '🟦 1. Lavoro & Carriera', 'lavoro-carriera', '💼', 'Consulenza su carriera, lavoro e imprenditoria', '#4A90E2', 'Consulenti con esperienza professionale', 1),
(2, '🟦 2. Vita all\'Estero', 'vita-estero', '🌍', 'Guida per trasferirsi e vivere all\'estero', '#4A90E2', 'Expat e nomadi digitali', 1),
(3, '🟦 3. Viaggiatori & Nomadi Digitali', 'viaggiatori-nomadi', '✈️', 'Organizzazione viaggi e vita nomade', '#4A90E2', 'Travel blogger e nomadi digitali', 1),
(4, '🟦 4. Burocrazia & Documenti', 'burocrazia-documenti', '📋', 'Consulenza su tasse, documenti e burocrazia', '#4A90E2', 'Consulenti esperti di burocrazia', 1),
(5, '🟩 5. Pet & Animal Care', 'pet-animal-care', '🐾', 'Consulenza su cura e addestramento animali', '#50C878', 'Pet trainer e veterinari', 1),
(6, '🟩 6. Esperienze Psicologiche & Benessere', 'esperienze-psicologiche', '🧠', 'Supporto per benessere personale e esperienze di vita', '#50C878', 'Coach e figure di supporto', 1),
(7, '🟦 7. Sport & Wellness', 'sport-wellness', '⚽', 'Allenamento, fitness e nutrizione', '#4A90E2', 'Personal trainer e coach sportivi', 1);

-- ============================================================================
-- Step 5: INSERIMENTO SOTTOCATEGORIE - CATEGORIA 1: LAVORO & CARRIERA
-- ============================================================================

INSERT INTO category (id, name, slug, icon, description, color, target, is_principal) VALUES
(8, 'Come trovare lavoro / cambiare lavoro', 'trovare-lavoro', '🔍', 'Strategie e consigli per trovare nuove opportunità', '#4A90E2', '', 0),
(9, 'Come crescere su Twitch / YouTube / TikTok', 'crescere-social', '📱', 'Strategie di crescita su piattaforme social', '#4A90E2', '', 0),
(10, 'Scrittura CV e profilo LinkedIn', 'cv-linkedin', '📄', 'Creazione di CV e profili professionali efficaci', '#4A90E2', '', 0),
(11, 'Preparazione ai colloqui', 'preparazione-colloqui', '🎤', 'Consigli e allenamento per colloqui di lavoro', '#4A90E2', '', 0),
(12, 'Carriera aziendale', 'carriera-aziendale', '🏢', 'Sviluppo della carriera all\'interno di aziende', '#4A90E2', '', 0),
(13, 'Freelancing e consulenza', 'freelancing-consulenza', '💻', 'Come iniziare e gestire attività freelance', '#4A90E2', '', 0),
(14, 'Orientamento professionale', 'orientamento-prof', '🧭', 'Guida per scegliere la giusta carriera', '#4A90E2', '', 0),
(15, 'Produttività & organizzazione personale', 'produttivita-organizzazione', '⏱️', 'Tecniche di produttività e gestione tempo', '#4A90E2', '', 0),
(16, 'Startup & imprenditoria', 'startup-imprenditoria', '🚀', 'Come avviare e gestire una startup', '#4A90E2', '', 0);

-- ============================================================================
-- Step 6: INSERIMENTO SOTTOCATEGORIE - CATEGORIA 2: VITA ALL'ESTERO
-- ============================================================================

INSERT INTO category (id, name, slug, icon, description, color, target, is_principal) VALUES
(17, 'Trasferirsi in un nuovo Paese', 'trasferirsi-paese', '🏠', 'Guida pratica per trasferirsi all\'estero', '#4A90E2', '', 0),
(18, 'Permesso di soggiorno / visti', 'visti-permessi', '📝', 'Informazioni su visti e permessi di soggiorno', '#4A90E2', '', 0),
(19, 'Trovare casa all\'estero', 'trovare-casa', '🏡', 'Consigli per cercare e affittare casa', '#4A90E2', '', 0),
(20, 'Trovare lavoro all\'estero', 'trovare-lavoro-estero', '💼', 'Strategie per cercare lavoro in altri paesi', '#4A90E2', '', 0),
(21, 'Adattamento culturale', 'adattamento-culturale', '🤝', 'Come adattarsi a nuove culture', '#4A90E2', '', 0),
(22, 'Gestione della burocrazia locale', 'burocrazia-locale', '🗂️', 'Navigare la burocrazia dei paesi stranieri', '#4A90E2', '', 0),
(23, 'Vita da expat & integrazione', 'vita-expat', '🌐', 'Comunità expat e integrazione sociale', '#4A90E2', '', 0);

-- ============================================================================
-- Step 7: INSERIMENTO SOTTOCATEGORIE - CATEGORIA 3: VIAGGIATORI & NOMADI DIGITALI
-- ============================================================================

INSERT INTO category (id, name, slug, icon, description, color, target, is_principal) VALUES
(24, 'Organizzazione viaggi', 'organizzazione-viaggi', '✈️', 'Come pianificare e organizzare un viaggio', '#4A90E2', '', 0),
(25, 'Itinerari personalizzati', 'itinerari-personalizzati', '🗺️', 'Consigli per creare itinerari su misura', '#4A90E2', '', 0),
(26, 'Lavorare da remoto in giro per il mondo', 'lavorare-remoto-viaggio', '💻', 'Come mantenere il lavoro mentre si viaggia', '#4A90E2', '', 0),
(27, 'Gestione budget di viaggio', 'budget-viaggio', '💰', 'Consigli per risparmiare e gestire il budget', '#4A90E2', '', 0),
(28, 'Vita da nomade digitale', 'nomade-digitale', '🏖️', 'Stile di vita e organizzazione da nomade', '#4A90E2', '', 0),
(29, 'Consigli su sicurezza nelle destinazioni', 'sicurezza-destinazioni', '🛡️', 'Come stare sicuri durante i viaggi', '#4A90E2', '', 0);

-- ============================================================================
-- Step 8: INSERIMENTO SOTTOCATEGORIE - CATEGORIA 4: BUROCRAZIA & DOCUMENTI
-- ============================================================================

INSERT INTO category (id, name, slug, icon, description, color, target, is_principal) VALUES
(30, 'Dichiarazione dei redditi / tasse base', 'tasse-redditi', '💵', 'Guida ai tributi e dichiarazioni', '#4A90E2', '', 0),
(31, 'INPS / bonus / agevolazioni', 'inps-bonus', '📊', 'Informazioni su INPS e agevolazioni', '#4A90E2', '', 0),
(32, 'Contratti e questioni amministrative', 'contratti-amministrativa', '⚖️', 'Consulenza su contratti e documenti', '#4A90E2', '', 0),
(33, 'Scuola, università e concorsi', 'scuola-universita', '🎓', 'Guida su percorsi educativi e concorsi', '#4A90E2', '', 0);

-- ============================================================================
-- Step 9: INSERIMENTO SOTTOCATEGORIE - CATEGORIA 5: PET & ANIMAL CARE
-- ============================================================================

INSERT INTO category (id, name, slug, icon, description, color, target, is_principal) VALUES
(34, 'Adozione e accoglienza animali', 'adozione-animali', '🐕', 'Come adottare e accogliere animali', '#50C878', '', 0),
(35, 'Gestione cuccioli', 'gestione-cuccioli', '🐶', 'Consigli per la cura dei cuccioli', '#50C878', '', 0),
(36, 'Comportamento e addestramento base', 'comportamento-addestramento', '🎾', 'Addestrare e gestire il comportamento', '#50C878', '', 0),
(37, 'Alimentazione quotidiana', 'alimentazione-animali', '🥩', 'Corretta alimentazione per gli animali', '#50C878', '', 0),
(38, 'Pulizia e cura dell\'animale', 'pulizia-cura', '🛁', 'Igiene e cura quotidiana', '#50C878', '', 0),
(39, 'Gestione problemi ricorrenti (abbaiare, tirare al guinzaglio, marcature)', 'problemi-ricorrenti', '⚠️', 'Soluzioni per comportamenti problematici', '#50C878', '', 0),
(40, 'Integrazione nuovo animale in famiglia', 'integrazione-animale', '👨‍👩‍👧‍👦', 'Come introdurre un nuovo animale in casa', '#50C878', '', 0),
(41, 'Viaggiare con animali', 'viaggiare-animali', '🚗', 'Come viaggiare in sicurezza con i pet', '#50C878', '', 0);

-- ============================================================================
-- Step 10: INSERIMENTO SOTTOCATEGORIE - CATEGORIA 6: ESPERIENZE PSICOLOGICHE & BENESSERE
-- ============================================================================

INSERT INTO category (id, name, slug, icon, description, color, target, is_principal) VALUES
(42, 'Coming out', 'coming-out', '🏳️‍🌈', 'Supporto per il processo di coming out', '#50C878', '', 0),
(43, 'Solitudine e Lavoro sull\'autostima', 'solitudine-autostima', '💪', 'Gestire la solitudine e costruire autostima', '#50C878', '', 0),
(44, 'Divorzio o separazioni', 'divorzio-separazioni', '💔', 'Supporto durante separazioni e divorzi', '#50C878', '', 0),
(45, 'Obesità e forte perdita di peso', 'perdita-peso', '⚖️', 'Gestire la perdita di peso e cambio stile di vita', '#50C878', '', 0),
(46, 'Problemi con i figli', 'problemi-figli', '👨‍👧', 'Supporto nel rapporto genitoriale', '#50C878', '', 0),
(47, 'Bullismo (esperienze reali)', 'bullismo', '🚫', 'Affrontare e superare il bullismo', '#50C878', '', 0),
(48, 'Gestione stress non clinico', 'gestione-stress', '🧘', 'Tecniche per gestire lo stress quotidiano', '#50C878', '', 0);

-- ============================================================================
-- Step 11: INSERIMENTO SOTTOCATEGORIE - CATEGORIA 7: SPORT & WELLNESS
-- ============================================================================

INSERT INTO category (id, name, slug, icon, description, color, target, is_principal) VALUES
(49, 'Fitness & allenamento', 'fitness-allenamento', '💪', 'Programmi e consigli di fitness', '#4A90E2', '', 0),
(50, 'Nutrizione personale (non clinica)', 'nutrizione-personale', '🥗', 'Consigli su alimentazione e nutrizione', '#4A90E2', '', 0),
(51, 'Running, cycling, palestra', 'running-cycling-palestra', '🏃', 'Sport specifici e allenamento', '#4A90E2', '', 0),
(52, 'Programmi di allenamento personalizzati', 'programmi-personalizzati', '📋', 'Piani di allenamento su misura', '#4A90E2', '', 0),
(53, 'Riattivazione dopo periodi di stop', 'riattivazione-stop', '🔄', 'Come riprendere l\'allenamento', '#4A90E2', '', 0),
(54, 'Esperienze sportive agonistiche', 'esperienze-agonistiche', '🥇', 'Preparazione per competizioni sportive', '#4A90E2', '', 0);

-- ============================================================================
-- Step 12: CREAZIONE GERARCHIA: COLLEGARE OGNI SOTTOCATEGORIA ALLA SUA PRINCIPALE
-- ============================================================================

-- CATEGORIA 1: LAVORO & CARRIERA (IDs 8-16)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(1, 8, 0), (1, 9, 1), (1, 10, 2), (1, 11, 3), (1, 12, 4), (1, 13, 5), (1, 14, 6), (1, 15, 7), (1, 16, 8);

-- CATEGORIA 2: VITA ALL'ESTERO (IDs 17-23)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(2, 17, 0), (2, 18, 1), (2, 19, 2), (2, 20, 3), (2, 21, 4), (2, 22, 5), (2, 23, 6);

-- CATEGORIA 3: VIAGGIATORI & NOMADI DIGITALI (IDs 24-29)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(3, 24, 0), (3, 25, 1), (3, 26, 2), (3, 27, 3), (3, 28, 4), (3, 29, 5);

-- CATEGORIA 4: BUROCRAZIA & DOCUMENTI (IDs 30-33)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(4, 30, 0), (4, 31, 1), (4, 32, 2), (4, 33, 3);

-- CATEGORIA 5: PET & ANIMAL CARE (IDs 34-41)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(5, 34, 0), (5, 35, 1), (5, 36, 2), (5, 37, 3), (5, 38, 4), (5, 39, 5), (5, 40, 6), (5, 41, 7);

-- CATEGORIA 6: ESPERIENZE PSICOLOGICHE & BENESSERE (IDs 42-48)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(6, 42, 0), (6, 43, 1), (6, 44, 2), (6, 45, 3), (6, 46, 4), (6, 47, 5), (6, 48, 6);

-- CATEGORIA 7: SPORT & WELLNESS (IDs 49-54)
INSERT INTO category_hierarchy (parent_category_id, child_category_id, position) VALUES
(7, 49, 0), (7, 50, 1), (7, 51, 2), (7, 52, 3), (7, 53, 4), (7, 54, 5);

-- ============================================================================
-- VERIFICA FINALE
-- ============================================================================
-- SELECT COUNT(*) as total_categories FROM category;
-- SELECT COUNT(*) as total_hierarchy FROM category_hierarchy;
-- SELECT COUNT(*) as principal_count FROM category WHERE is_principal = 1;
-- SELECT parent_category_id, COUNT(*) as children_count FROM category_hierarchy GROUP BY parent_category_id;
