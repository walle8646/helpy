-- ================================================
-- INSERIMENTO RICHIESTE COMMUNITY Q&A
-- Compatibile con SQLite e PostgreSQL
-- ================================================

-- Categoria 1: Ambito Lavorativo e Carriera
INSERT INTO community_questions (user_id, category_id, title, description, status, views, upvotes, created_at, updated_at)
VALUES 
(15, 1, 'Consigli per il primo colloquio di lavoro?', 'Tra una settimana ho il mio primo colloquio per una posizione junior in marketing. Sono molto nervoso e non so come prepararmi. Quali domande mi faranno? Come devo vestirmi? Qualche consiglio pratico?', 'open', 5, 0, datetime('now', '-2 days'), datetime('now', '-2 days')),

(23, 1, 'Cambio carriera a 35 anni: è troppo tardi?', 'Ho 35 anni e lavoro da 10 anni nel settore bancario, ma non mi sento più realizzato. Vorrei passare al settore tech/programmazione. È troppo tardi per cambiare completamente settore? Qualcuno ha avuto esperienze simili?', 'open', 12, 3, datetime('now', '-5 days'), datetime('now', '-5 days')),

(34, 1, 'Negoziare lo stipendio: come fare?', 'Mi hanno fatto un''offerta di lavoro ma lo stipendio proposto è inferiore alle mie aspettative. Come posso negoziare senza sembrare troppo esigente o rischiare di perdere l''opportunità? Quali strategie consigliate?', 'open', 8, 1, datetime('now', '-1 day'), datetime('now', '-1 day'));

-- Categoria 2: Sviluppo Software e Tech
INSERT INTO community_questions (user_id, category_id, title, description, status, views, upvotes, created_at, updated_at)
VALUES 
(42, 2, 'Quale linguaggio imparare per primo nel 2025?', 'Voglio iniziare a programmare da zero. Ho sentito parlare di Python, JavaScript, Java... sono confuso! Quale mi consigliate per iniziare considerando le opportunità lavorative attuali?', 'open', 18, 5, datetime('now', '-3 days'), datetime('now', '-3 days')),

(51, 2, 'React vs Vue.js: quale scegliere?', 'Devo sviluppare una nuova web app per la mia azienda. Ho esperienza con vanilla JavaScript ma mai usato framework moderni. Meglio React o Vue.js per chi inizia? Pro e contro di entrambi?', 'open', 14, 2, datetime('now', '-4 days'), datetime('now', '-4 days')),

(28, 2, 'Come gestire il burnout da sviluppatore?', 'Lavoro come developer da 3 anni e ultimamente sento di essere in burnout. Scadenze strette, troppe riunioni, codice legacy impossibile. Come avete gestito situazioni simili? Consigli per ritrovare la motivazione?', 'open', 22, 7, datetime('now', '-6 days'), datetime('now', '-6 days'));

-- Categoria 3: Business e Imprenditoria
INSERT INTO community_questions (user_id, category_id, title, description, status, views, upvotes, created_at, updated_at)
VALUES 
(67, 3, 'Aprire partita IVA: regime forfettario o ordinario?', 'Voglio iniziare la mia attività di consulenza freelance. Mi conviene il regime forfettario o quello ordinario? Fatturerò circa 30-35k all''anno. Quali sono i pro e contro di ciascuno?', 'open', 16, 4, datetime('now', '-3 days'), datetime('now', '-3 days')),

(45, 3, 'Trovare i primi clienti come freelance', 'Ho appena aperto partita IVA come graphic designer. Come posso trovare i miei primi clienti? LinkedIn, portfolio online, passaparola... da dove inizio? Budget limitato per marketing.', 'open', 11, 2, datetime('now', '-2 days'), datetime('now', '-2 days')),

(72, 3, 'Business plan per startup: è davvero necessario?', 'Sto per lanciare una startup tech. Tutti mi dicono di fare un business plan dettagliato, ma mi sembra una perdita di tempo considerando che tutto cambia velocemente. Quanto è importante realmente?', 'open', 9, 1, datetime('now', '-1 day'), datetime('now', '-1 day'));

-- Categoria 4: Marketing e Comunicazione
INSERT INTO community_questions (user_id, category_id, title, description, status, views, upvotes, created_at, updated_at)
VALUES 
(38, 4, 'Instagram o TikTok per promuovere business locale?', 'Ho un piccolo negozio di abbigliamento e voglio aumentare la visibilità sui social. Meglio concentrarsi su Instagram o TikTok? Ho poco tempo da dedicarci, quindi vorrei puntare su uno solo.', 'open', 19, 6, datetime('now', '-4 days'), datetime('now', '-4 days')),

(56, 4, 'SEO nel 2025: da dove iniziare?', 'Ho un sito e-commerce ma nessuno mi trova su Google. Vorrei migliorare la SEO ma non so da dove partire. È meglio affidarsi a un''agenzia o posso fare qualcosa da solo? Budget limitato.', 'open', 15, 3, datetime('now', '-5 days'), datetime('now', '-5 days'));

-- Categoria 5: Design e Creatività
INSERT INTO community_questions (user_id, category_id, title, description, status, views, upvotes, created_at, updated_at)
VALUES 
(61, 5, 'Figma vs Adobe XD: quale usare per UI/UX?', 'Sto iniziando a fare UI/UX design professionalmente. Ho visto che molti usano Figma, altri Adobe XD. Quale mi consigliate? Considerate che dovrò collaborare con sviluppatori.', 'open', 13, 4, datetime('now', '-3 days'), datetime('now', '-3 days')),

(29, 5, 'Come farsi pagare il giusto come designer?', 'Sono un graphic designer freelance da un anno. Spesso mi chiedono "quanto costa un logo?" e non so mai cosa rispondere. Come si calcola una tariffa corretta? Tariffa oraria o a progetto?', 'open', 20, 8, datetime('now', '-6 days'), datetime('now', '-6 days'));

-- Categoria 6: Finanza e Investimenti
INSERT INTO community_questions (user_id, category_id, title, description, status, views, upvotes, created_at, updated_at)
VALUES 
(77, 6, 'Iniziare a investire con 500€ al mese', 'Ho 28 anni e posso mettere da parte 500€ al mese. Vorrei iniziare a investire ma sono totalmente inesperto. ETF, azioni, obbligazioni... da dove inizio? Consigli per un principiante?', 'open', 25, 9, datetime('now', '-5 days'), datetime('now', '-5 days')),

(48, 6, 'Criptovalute: ancora conveniente investire?', 'Tutti parlano di Bitcoin ed Ethereum ma ormai sono già saliti molto. Ha ancora senso investire in crypto nel 2025 o il treno è già passato? Troppo rischioso per un portfolio bilanciato?', 'open', 17, 5, datetime('now', '-4 days'), datetime('now', '-4 days'));

-- ================================================
-- NOTA: Per PostgreSQL, sostituire datetime('now', '-X days') 
-- con: NOW() - INTERVAL 'X days'
-- ================================================
