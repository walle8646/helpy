-- Cancella le categorie attuali
DELETE FROM category;

-- 1. LAVORO & CARRIERA (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Lavoro & Carriera', 'lavoro-carriera', '💼', 'Consulenze sulla carriera professionale', '#2196F3', TRUE, NULL);

SET @lavoro_id = LAST_INSERT_ID();

INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Come trovare lavoro / cambiare lavoro', 'trovare-lavoro', '🔍', 'Strategie per trovare lavoro e cambiare carriera', '#2196F3', FALSE, @lavoro_id),
('Scrittura CV e profilo LinkedIn', 'cv-linkedin', '📝', 'Aiuto nella stesura di CV e profili professionali', '#2196F3', FALSE, @lavoro_id),
('Preparazione ai colloqui', 'colloqui', '🎤', 'Preparazione e coaching per colloqui di lavoro', '#2196F3', FALSE, @lavoro_id),
('Carriera aziendale', 'carriera-aziendale', '📈', 'Sviluppo di carriera all\'interno di aziende', '#2196F3', FALSE, @lavoro_id),
('Freelancing e consulenza', 'freelancing', '🚀', 'Consigli per freelancer e consulenti', '#2196F3', FALSE, @lavoro_id),
('Orientamento professionale', 'orientamento-prof', '🧭', 'Orientamento e scelta professionale', '#2196F3', FALSE, @lavoro_id);

-- 2. VITA ALL'ESTERO (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Vita all\'Estero', 'vita-estero', '🌍', 'Consulenze su trasferimenti e vita all\'estero', '#FF9800', TRUE, NULL);

SET @estero_id = LAST_INSERT_ID();

INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Trasferirsi in un nuovo Paese', 'trasferimento', '✈️', 'Pianificazione e realizzazione del trasferimento', '#FF9800', FALSE, @estero_id),
('Permesso di soggiorno / visti', 'visti', '📄', 'Informazioni su visti e permessi di soggiorno', '#FF9800', FALSE, @estero_id),
('Trovare casa all\'estero', 'casa-estero', '🏠', 'Ricerca e affitto di alloggi all\'estero', '#FF9800', FALSE, @estero_id),
('Trovare lavoro all\'estero', 'lavoro-estero', '💼', 'Ricerca di lavoro in altri paesi', '#FF9800', FALSE, @estero_id),
('Adattamento culturale', 'adattamento-cultura', '🌐', 'Consigli per adattarsi a nuove culture', '#FF9800', FALSE, @estero_id),
('Gestione della burocrazia locale', 'burocrazia', '🏛️', 'Navigare la burocrazia locale', '#FF9800', FALSE, @estero_id),
('Vita da expat & integrazione', 'expat-integrazione', '🤝', 'Comunità di expat e integrazione sociale', '#FF9800', FALSE, @estero_id);

-- 3. VIAGGIATORI & NOMADI DIGITALI (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Viaggiatori & Nomadi Digitali', 'nomadi-digitali', '🌏', 'Consulenze per nomadi digitali e viaggiatori', '#4CAF50', TRUE, NULL);

SET @nomadi_id = LAST_INSERT_ID();

INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Organizzazione viaggi', 'organizzazione-viaggi', '📋', 'Pianificazione e organizzazione di viaggi', '#4CAF50', FALSE, @nomadi_id),
('Itinerari personalizzati', 'itinerari', '🗺️', 'Creazione di itinerari su misura', '#4CAF50', FALSE, @nomadi_id),
('Lavorare da remoto in giro per il mondo', 'remote-lavoro', '💻', 'Consigli per lavorare mentre si viaggia', '#4CAF50', FALSE, @nomadi_id),
('Gestione budget di viaggio', 'budget-viaggio', '💰', 'Pianificazione finanziaria per viaggi', '#4CAF50', FALSE, @nomadi_id),
('Vita da nomade digitale', 'nomade-digitale', '🛫', 'Lifestyle e organizzazione da nomade', '#4CAF50', FALSE, @nomadi_id),
('Consigli su sicurezza nelle destinazioni', 'sicurezza-viaggi', '🔒', 'Sicurezza e prevenzione durante i viaggi', '#4CAF50', FALSE, @nomadi_id);

-- 4. ESPERIENZE DI VITA (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Esperienze di Vita', 'esperienze-vita', '🎯', 'Consulenze su esperienze di vita e cambiamenti', '#9C27B0', TRUE, NULL);

SET @esperienza_id = LAST_INSERT_ID();

INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Traslochi e cambi di città', 'traslochi', '📦', 'Organizzazione traslochi e cambi di residenza', '#9C27B0', FALSE, @esperienza_id),
('Gestione di eventi importanti', 'eventi-importanti', '🎊', 'Gestione di matrimoni, figli e grandi eventi', '#9C27B0', FALSE, @esperienza_id),
('Gestione dei fallimenti', 'gestione-fallimenti', '💪', 'Come affrontare e superare i fallimenti', '#9C27B0', FALSE, @esperienza_id),
('Come ricominciare dopo periodi difficili', 'ricominciare', '🌱', 'Ripartire dopo crisi o periodi difficili', '#9C27B0', FALSE, @esperienza_id),
('Problemi comuni nella vita quotidiana', 'problemi-quotidiani', '🔧', 'Soluzioni a problemi comuni della vita', '#9C27B0', FALSE, @esperienza_id),
('Relazioni familiari & personali', 'relazioni', '❤️', 'Consigli su relazioni personali e familiari', '#9C27B0', FALSE, @esperienza_id);

-- 5. SETTORI SPECIFICI (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Settori Specifici', 'settori-specifici', '⚙️', 'Consulenze su settori specifici e specializzati', '#F44336', TRUE, NULL);

SET @settori_id = LAST_INSERT_ID();

INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Immobiliare', 'immobiliare', '🏢', 'Consulenze su acquisto, vendita e affitto di immobili', '#F44336', FALSE, @settori_id),
('Ristrutturazioni e home improvement', 'ristrutturazioni', '🛠️', 'Consigli per ristrutturazioni e migliorie abitative', '#F44336', FALSE, @settori_id),
('Auto, moto e veicoli', 'veicoli', '🚗', 'Consulenze su acquisto e manutenzione di veicoli', '#F44336', FALSE, @settori_id),
('Food & hospitality', 'food-hospitality', '🍽️', 'Consigli su ristorazione e ospitalità', '#F44336', FALSE, @settori_id),
('Moda & styling', 'moda-styling', '👗', 'Consulenze su moda, stile e immagine personale', '#F44336', FALSE, @settori_id),
('Educazione e formazione', 'educazione', '🎓', 'Consulenze su percorsi educativi e formazione', '#F44336', FALSE, @settori_id),
('Finanza personale', 'finanza-personale', '💳', 'Consigli su finanza personale e investimenti', '#F44336', FALSE, @settori_id),
('Startup & imprenditoria', 'startup', '🚀', 'Consigli per startuppisti e imprenditori', '#F44336', FALSE, @settori_id);

-- 6. MENTORSHIP & CRESCITA PERSONALE (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Mentorship & Crescita Personale', 'mentorship', '🌟', 'Mentorship e sviluppo personale', '#00BCD4', TRUE, NULL);

SET @mentorship_id = LAST_INSERT_ID();

INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Life coaching peer-to-peer', 'life-coaching', '👥', 'Life coaching e supporto tra pari', '#00BCD4', FALSE, @mentorship_id),
('Supporto motivazionale', 'motivazione', '⚡', 'Supporto e motivazione personale', '#00BCD4', FALSE, @mentorship_id),
('Gestione quotidiana dello stress', 'stress-management', '🧘', 'Tecniche per gestire lo stress quotidiano', '#00BCD4', FALSE, @mentorship_id),
('Definizione obiettivi', 'obiettivi', '🎯', 'Aiuto nella definizione e raggiungimento di obiettivi', '#00BCD4', FALSE, @mentorship_id),
('Costruire abitudini efficaci', 'abitudini', '📅', 'Sviluppo di abitudini positive e durature', '#00BCD4', FALSE, @mentorship_id),
('Comunicazione & assertività', 'comunicazione', '💬', 'Migliorare comunicazione e assertività', '#00BCD4', FALSE, @mentorship_id);

-- 7. SPORT & WELLNESS (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Sport & Wellness', 'sport-wellness', '🏋️', 'Consulenze su sport, fitness e benessere', '#E91E63', TRUE, NULL);

SET @sport_id = LAST_INSERT_ID();

INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Fitness & allenamento', 'fitness', '💪', 'Programmi di allenamento e fitness', '#E91E63', FALSE, @sport_id),
('Nutrizione personale', 'nutrizione', '🥗', 'Consigli nutrizionali personali (non clinici)', '#E91E63', FALSE, @sport_id),
('Running, cycling, palestra', 'cardio-palestra', '🏃', 'Specialità in running, cycling e allenamenti', '#E91E63', FALSE, @sport_id),
('Programmi di allenamento personalizzati', 'programmi-allenamento', '📊', 'Creazione di programmi su misura', '#E91E63', FALSE, @sport_id),
('Riattivazione dopo periodi di stop', 'riattivazione', '🔄', 'Ripresa graduale dell\'attività fisica', '#E91E63', FALSE, @sport_id),
('Esperienze sportive agonistiche', 'sport-agonistici', '🏅', 'Preparazione a competizioni sportive', '#E91E63', FALSE, @sport_id);

-- 8. GAMING & CREATORS (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Gaming & Creators', 'gaming-creators', '🎮', 'Consulenze per gamer e content creator', '#00A86B', TRUE, NULL);

SET @gaming_id = LAST_INSERT_ID();

INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Strategie di gioco', 'strategie-gioco', '🎯', 'Strategie avanzate di gaming', '#00A86B', FALSE, @gaming_id),
('Come crescere su Twitch / YouTube / TikTok', 'social-media-growth', '📱', 'Strategie di crescita su piattaforme social', '#00A86B', FALSE, @gaming_id),
('Set-up per gaming e streaming', 'setup-gaming', '💻', 'Configurazione ottimale per gaming e streaming', '#00A86B', FALSE, @gaming_id),
('Editing video', 'video-editing', '🎬', 'Tecniche e strumenti per editing video', '#00A86B', FALSE, @gaming_id),
('Brand image da creator', 'brand-creator', '✨', 'Costruzione di brand personale per creator', '#00A86B', FALSE, @gaming_id),
('Community building', 'community-building', '🌐', 'Creazione e gestione di comunità online', '#00A86B', FALSE, @gaming_id);
