-- Cancella le categorie attuali (PostgreSQL)
DELETE FROM category;

-- 1. LAVORO & CARRIERA (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Lavoro & Carriera', 'lavoro-carriera', '💼', 'Consulenze sulla carriera professionale', '#2196F3', TRUE, NULL);

-- Usa RETURNING per ottenere l'ID (PostgreSQL)
WITH lavoro AS (
  SELECT id FROM category WHERE slug = 'lavoro-carriera'
)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Come trovare lavoro / cambiare lavoro', 'trovare-lavoro', '🔍', 'Strategie per trovare lavoro e cambiare carriera', '#2196F3', FALSE, (SELECT id FROM lavoro)),
('Scrittura CV e profilo LinkedIn', 'cv-linkedin', '📝', 'Aiuto nella stesura di CV e profili professionali', '#2196F3', FALSE, (SELECT id FROM lavoro)),
('Preparazione ai colloqui', 'colloqui', '🎤', 'Preparazione e coaching per colloqui di lavoro', '#2196F3', FALSE, (SELECT id FROM lavoro)),
('Carriera aziendale', 'carriera-aziendale', '📈', 'Sviluppo di carriera all\'interno di aziende', '#2196F3', FALSE, (SELECT id FROM lavoro)),
('Freelancing e consulenza', 'freelancing', '🚀', 'Consigli per freelancer e consulenti', '#2196F3', FALSE, (SELECT id FROM lavoro)),
('Orientamento professionale', 'orientamento-prof', '🧭', 'Orientamento e scelta professionale', '#2196F3', FALSE, (SELECT id FROM lavoro));

-- 2. VITA ALL'ESTERO (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Vita all\'Estero', 'vita-estero', '🌍', 'Consulenze su trasferimenti e vita all\'estero', '#FF9800', TRUE, NULL);

WITH estero AS (
  SELECT id FROM category WHERE slug = 'vita-estero'
)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Trasferirsi in un nuovo Paese', 'trasferimento', '✈️', 'Pianificazione e realizzazione del trasferimento', '#FF9800', FALSE, (SELECT id FROM estero)),
('Permesso di soggiorno / visti', 'visti', '📄', 'Informazioni su visti e permessi di soggiorno', '#FF9800', FALSE, (SELECT id FROM estero)),
('Trovare casa all\'estero', 'casa-estero', '🏠', 'Ricerca e affitto di alloggi all\'estero', '#FF9800', FALSE, (SELECT id FROM estero)),
('Trovare lavoro all\'estero', 'lavoro-estero', '💼', 'Ricerca di lavoro in altri paesi', '#FF9800', FALSE, (SELECT id FROM estero)),
('Adattamento culturale', 'adattamento-cultura', '🌐', 'Consigli per adattarsi a nuove culture', '#FF9800', FALSE, (SELECT id FROM estero)),
('Gestione della burocrazia locale', 'burocrazia', '🏛️', 'Navigare la burocrazia locale', '#FF9800', FALSE, (SELECT id FROM estero)),
('Vita da expat & integrazione', 'expat-integrazione', '🤝', 'Comunità di expat e integrazione sociale', '#FF9800', FALSE, (SELECT id FROM estero));

-- 3. VIAGGIATORI & NOMADI DIGITALI (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Viaggiatori & Nomadi Digitali', 'nomadi-digitali', '🌏', 'Consulenze per nomadi digitali e viaggiatori', '#4CAF50', TRUE, NULL);

WITH nomadi AS (
  SELECT id FROM category WHERE slug = 'nomadi-digitali'
)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Organizzazione viaggi', 'organizzazione-viaggi', '📋', 'Pianificazione e organizzazione di viaggi', '#4CAF50', FALSE, (SELECT id FROM nomadi)),
('Itinerari personalizzati', 'itinerari', '🗺️', 'Creazione di itinerari su misura', '#4CAF50', FALSE, (SELECT id FROM nomadi)),
('Lavorare da remoto in giro per il mondo', 'remote-lavoro', '💻', 'Consigli per lavorare mentre si viaggia', '#4CAF50', FALSE, (SELECT id FROM nomadi)),
('Gestione budget di viaggio', 'budget-viaggio', '💰', 'Pianificazione finanziaria per viaggi', '#4CAF50', FALSE, (SELECT id FROM nomadi)),
('Vita da nomade digitale', 'nomade-digitale', '🛫', 'Lifestyle e organizzazione da nomade', '#4CAF50', FALSE, (SELECT id FROM nomadi)),
('Consigli su sicurezza nelle destinazioni', 'sicurezza-viaggi', '🔒', 'Sicurezza e prevenzione durante i viaggi', '#4CAF50', FALSE, (SELECT id FROM nomadi));

-- 4. ESPERIENZE DI VITA (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Esperienze di Vita', 'esperienze-vita', '🎯', 'Consulenze su esperienze di vita e cambiamenti', '#9C27B0', TRUE, NULL);

WITH esperienza AS (
  SELECT id FROM category WHERE slug = 'esperienze-vita'
)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Traslochi e cambi di città', 'traslochi', '📦', 'Organizzazione traslochi e cambi di residenza', '#9C27B0', FALSE, (SELECT id FROM esperienza)),
('Gestione di eventi importanti', 'eventi-importanti', '🎊', 'Gestione di matrimoni, figli e grandi eventi', '#9C27B0', FALSE, (SELECT id FROM esperienza)),
('Gestione dei fallimenti', 'gestione-fallimenti', '💪', 'Come affrontare e superare i fallimenti', '#9C27B0', FALSE, (SELECT id FROM esperienza)),
('Come ricominciare dopo periodi difficili', 'ricominciare', '🌱', 'Ripartire dopo crisi o periodi difficili', '#9C27B0', FALSE, (SELECT id FROM esperienza)),
('Problemi comuni nella vita quotidiana', 'problemi-quotidiani', '🔧', 'Soluzioni a problemi comuni della vita', '#9C27B0', FALSE, (SELECT id FROM esperienza)),
('Relazioni familiari & personali', 'relazioni', '❤️', 'Consigli su relazioni personali e familiari', '#9C27B0', FALSE, (SELECT id FROM esperienza));

-- 5. SETTORI SPECIFICI (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Settori Specifici', 'settori-specifici', '⚙️', 'Consulenze su settori specifici e specializzati', '#F44336', TRUE, NULL);

WITH settori AS (
  SELECT id FROM category WHERE slug = 'settori-specifici'
)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Immobiliare', 'immobiliare', '🏢', 'Consulenze su acquisto, vendita e affitto di immobili', '#F44336', FALSE, (SELECT id FROM settori)),
('Ristrutturazioni e home improvement', 'ristrutturazioni', '🛠️', 'Consigli per ristrutturazioni e migliorie abitative', '#F44336', FALSE, (SELECT id FROM settori)),
('Auto, moto e veicoli', 'veicoli', '🚗', 'Consulenze su acquisto e manutenzione di veicoli', '#F44336', FALSE, (SELECT id FROM settori)),
('Food & hospitality', 'food-hospitality', '🍽️', 'Consigli su ristorazione e ospitalità', '#F44336', FALSE, (SELECT id FROM settori)),
('Moda & styling', 'moda-styling', '👗', 'Consulenze su moda, stile e immagine personale', '#F44336', FALSE, (SELECT id FROM settori)),
('Educazione e formazione', 'educazione', '🎓', 'Consulenze su percorsi educativi e formazione', '#F44336', FALSE, (SELECT id FROM settori)),
('Finanza personale', 'finanza-personale', '💳', 'Consigli su finanza personale e investimenti', '#F44336', FALSE, (SELECT id FROM settori)),
('Startup & imprenditoria', 'startup', '🚀', 'Consigli per startuppisti e imprenditori', '#F44336', FALSE, (SELECT id FROM settori));

-- 6. MENTORSHIP & CRESCITA PERSONALE (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Mentorship & Crescita Personale', 'mentorship', '🌟', 'Mentorship e sviluppo personale', '#00BCD4', TRUE, NULL);

WITH mentorship AS (
  SELECT id FROM category WHERE slug = 'mentorship'
)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Life coaching peer-to-peer', 'life-coaching', '👥', 'Life coaching e supporto tra pari', '#00BCD4', FALSE, (SELECT id FROM mentorship)),
('Supporto motivazionale', 'motivazione', '⚡', 'Supporto e motivazione personale', '#00BCD4', FALSE, (SELECT id FROM mentorship)),
('Gestione quotidiana dello stress', 'stress-management', '🧘', 'Tecniche per gestire lo stress quotidiano', '#00BCD4', FALSE, (SELECT id FROM mentorship)),
('Definizione obiettivi', 'obiettivi', '🎯', 'Aiuto nella definizione e raggiungimento di obiettivi', '#00BCD4', FALSE, (SELECT id FROM mentorship)),
('Costruire abitudini efficaci', 'abitudini', '📅', 'Sviluppo di abitudini positive e durature', '#00BCD4', FALSE, (SELECT id FROM mentorship)),
('Comunicazione & assertività', 'comunicazione', '💬', 'Migliorare comunicazione e assertività', '#00BCD4', FALSE, (SELECT id FROM mentorship));

-- 7. SPORT & WELLNESS (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Sport & Wellness', 'sport-wellness', '🏋️', 'Consulenze su sport, fitness e benessere', '#E91E63', TRUE, NULL);

WITH sport AS (
  SELECT id FROM category WHERE slug = 'sport-wellness'
)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Fitness & allenamento', 'fitness', '💪', 'Programmi di allenamento e fitness', '#E91E63', FALSE, (SELECT id FROM sport)),
('Nutrizione personale', 'nutrizione', '🥗', 'Consigli nutrizionali personali (non clinici)', '#E91E63', FALSE, (SELECT id FROM sport)),
('Running, cycling, palestra', 'cardio-palestra', '🏃', 'Specialità in running, cycling e allenamenti', '#E91E63', FALSE, (SELECT id FROM sport)),
('Programmi di allenamento personalizzati', 'programmi-allenamento', '📊', 'Creazione di programmi su misura', '#E91E63', FALSE, (SELECT id FROM sport)),
('Riattivazione dopo periodi di stop', 'riattivazione', '🔄', 'Ripresa graduale dell\'attività fisica', '#E91E63', FALSE, (SELECT id FROM sport)),
('Esperienze sportive agonistiche', 'sport-agonistici', '🏅', 'Preparazione a competizioni sportive', '#E91E63', FALSE, (SELECT id FROM sport));

-- 8. GAMING & CREATORS (Principale)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES ('Gaming & Creators', 'gaming-creators', '🎮', 'Consulenze per gamer e content creator', '#00A86B', TRUE, NULL);

WITH gaming AS (
  SELECT id FROM category WHERE slug = 'gaming-creators'
)
INSERT INTO category (name, slug, icon, description, color, is_primary, parent_id) 
VALUES 
('Strategie di gioco', 'strategie-gioco', '🎯', 'Strategie avanzate di gaming', '#00A86B', FALSE, (SELECT id FROM gaming)),
('Come crescere su Twitch / YouTube / TikTok', 'social-media-growth', '📱', 'Strategie di crescita su piattaforme social', '#00A86B', FALSE, (SELECT id FROM gaming)),
('Set-up per gaming e streaming', 'setup-gaming', '💻', 'Configurazione ottimale per gaming e streaming', '#00A86B', FALSE, (SELECT id FROM gaming)),
('Editing video', 'video-editing', '🎬', 'Tecniche e strumenti per editing video', '#00A86B', FALSE, (SELECT id FROM gaming)),
('Brand image da creator', 'brand-creator', '✨', 'Costruzione di brand personale per creator', '#00A86B', FALSE, (SELECT id FROM gaming)),
('Community building', 'community-building', '🌐', 'Creazione e gestione di comunità online', '#00A86B', FALSE, (SELECT id FROM gaming));
