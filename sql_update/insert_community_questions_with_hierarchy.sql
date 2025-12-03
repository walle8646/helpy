-- ========== INSERT 50 COMMUNITY QUESTIONS CON CATEGORIA PADRE E FIGLIA ==========
-- Questo script inserisce 50 domande inventate con sia primary_category_id che category_id

-- ATTENZIONE: Se le categorie non esistono, il database darà errore FOREIGN KEY
-- Assicurati che le categorie 1-54 siano state create prima di eseguire questo script

-- ========== DELETE EXISTING DATA ==========
DELETE FROM community_questions WHERE user_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24);

-- ========== VERIFICA E CREA CATEGORIE SE NON ESISTONO ==========
-- Inserisci le categorie principali (se non esistono già)
INSERT OR IGNORE INTO category (id, name, slug, icon, description, is_principal) VALUES
(1, 'Lavoro & Carriera', 'lavoro-carriera', '💼', 'Consigli su carriera, lavoro e sviluppo professionale', 1),
(2, 'Vita all''Estero', 'vita-estero', '✈️', 'Esperienze e consigli per vivere all''estero', 1),
(3, 'Salute & Benessere', 'salute-benessere', '🏥', 'Salute, fitness e benessere personale', 1),
(4, 'Finanze Personali', 'finanze-personali', '💰', 'Gestione del denaro e investimenti', 1),
(5, 'Istruzione & Formazione', 'istruzione-formazione', '📚', 'Corsi, lauree e sviluppo delle competenze', 1),
(6, 'Hobby & Tempo Libero', 'hobby-tempo-libero', '🎮', 'Passioni, hobby e attività ricreative', 1),
(7, 'Relazioni & Famiglia', 'relazioni-famiglia', '👨‍👩‍👧', 'Relazioni personali e dinamiche familiari', 1);

-- Inserisci le sottocategorie (8-54)
INSERT OR IGNORE INTO category (id, name, slug, icon, is_principal) VALUES
-- Lavoro & Carriera (8-14)
(8, 'Primo Lavoro', 'primo-lavoro', '🎓', 0),
(9, 'Stipendio & Negoziazione', 'stipendio', '💵', 0),
(10, 'Cambio Lavoro', 'cambio-lavoro', '🔄', 0),
(11, 'CV & Intervista', 'cv-intervista', '📄', 0),
(12, 'Freelance', 'freelance', '🤝', 0),
(13, 'Telelavoro', 'telelavoro', '💻', 0),
(14, 'Certificazioni', 'certificazioni', '🏅', 0),

-- Vita all'Estero (15-21)
(15, 'Vivere in Europa', 'europa', '🇪🇺', 0),
(16, 'Visti & Documenti', 'visti', '🛂', 0),
(17, 'Costo della Vita', 'costo-vita', '💸', 0),
(18, 'Imparare Lingue', 'lingue', '🗣️', 0),
(19, 'Trasferimento', 'trasferimento', '📦', 0),
(20, 'Cittadinanza', 'cittadinanza', '🪪', 0),
(21, 'Lavoro all''Estero', 'lavoro-estero', '🌍', 0),

-- Salute & Benessere (22-28)
(22, 'Dieta & Nutrizione', 'dieta', '🥗', 0),
(23, 'Sonno & Riposo', 'sonno', '😴', 0),
(24, 'Fitness & Palestra', 'fitness', '💪', 0),
(25, 'Stress & Ansia', 'stress', '🧘', 0),
(26, 'Perdita di Peso', 'peso', '⚖️', 0),
(27, 'Meditazione', 'meditazione', '🕉️', 0),
(28, 'Running & Maratone', 'running', '🏃', 0),

-- Finanze Personali (29-35)
(29, 'Investimenti', 'investimenti', '📈', 0),
(30, 'Immobili & Mutui', 'immobili', '🏠', 0),
(31, 'Criptovalute', 'crypto', '₿', 0),
(32, 'Pensione', 'pensione', '👴', 0),
(33, 'Tasse & Detrazioni', 'tasse', '📋', 0),
(34, 'Assicurazioni', 'assicurazioni', '🛡️', 0),
(35, 'Finanziamenti', 'finanziamenti', '🏦', 0),

-- Istruzione & Formazione (36-42)
(36, 'Laurea Online', 'laurea-online', '🎓', 0),
(37, 'Programmazione', 'programmazione', '💻', 0),
(38, 'Corsi Online', 'corsi-online', '📖', 0),
(39, 'MBA & Master', 'mba', '🎯', 0),
(40, 'Lingue Straniere', 'lingue-studio', '🌐', 0),
(41, 'Certificazioni Professionali', 'cert-prof', '📜', 0),
(42, 'Scuola vs Apprendistato', 'scuola-app', '🏫', 0),

-- Hobby & Tempo Libero (43-49)
(43, 'Fotografia', 'fotografia', '📷', 0),
(44, 'Gaming', 'gaming', '🎮', 0),
(45, 'Lettura', 'lettura', '📚', 0),
(46, 'Musica & Strumenti', 'musica', '🎸', 0),
(47, 'Arte & Disegno', 'arte', '🎨', 0),
(48, 'Viaggi', 'viaggi', '✈️', 0),
(49, 'Sport & Attività', 'sport', '⛹️', 0),

-- Relazioni & Famiglia (50-54)
(50, 'Convivenza', 'convivenza', '🏠', 0),
(51, 'Figli & Paternità', 'figli', '👶', 0),
(52, 'Relazioni Familiari', 'famiglia', '👨‍👩‍👧', 0),
(53, 'Amicizie', 'amicizie', '👫', 0),
(54, 'Relazioni a Distanza', 'distanza', '💔', 0);

INSERT INTO community_questions (user_id, primary_category_id, category_id, title, description, status, views, upvotes, created_at, updated_at)
VALUES
-- Lavoro & Carriera (primary_category_id = 1)
(1, 1, 8, 'Come fare il primo colloquio?', 'Sono alla ricerca del mio primo lavoro e non so come prepararmi per il colloquio. Quali sono i consigli principali?', 'open', 45, 12, datetime('now', '-5 days'), datetime('now', '-5 days')),
(2, 1, 9, 'Stipendio giusto per uno sviluppatore junior', 'Quanto dovrei chiedere di stipendio come sviluppatore junior in Italia nel 2025?', 'open', 78, 23, datetime('now', '-4 days'), datetime('now', '-4 days')),
(3, 1, 10, 'Cambiare lavoro dopo 6 mesi: è opportuno?', 'Ho fatto 6 mesi nel mio primo lavoro ma non mi trovo bene. È meglio restare o cercare altro?', 'open', 92, 35, datetime('now', '-3 days'), datetime('now', '-3 days')),
(4, 1, 11, 'Come scrivere un CV vincente', 'Quale formato di CV è più apprezzato dalle aziende italiane? Pdf o Word?', 'open', 56, 18, datetime('now', '-2 days'), datetime('now', '-2 days')),
(5, 1, 12, 'Freelance vs Dipendente: cosa scegliere?', 'Devo decidere se lavorare come freelance o cercare un lavoro dipendente. Quali sono i pro e i contro?', 'open', 102, 41, datetime('now', '-1 days'), datetime('now', '-1 days')),
(6, 1, 13, 'Come negoziare il telelavoro?', 'Lavoro in ufficio ma vorrei negoziare il telelavoro. Come posso affrontare questa conversazione con il mio capo?', 'open', 34, 9, datetime('now'), datetime('now')),
(7, 1, 14, 'Certificazioni che aumentano il valore nel mercato', 'Quale certificazione IT è più richiesta dalle aziende italiane nel 2025?', 'open', 67, 19, datetime('now', '-6 days'), datetime('now', '-6 days')),

-- Vita all'Estero (primary_category_id = 2)
(8, 2, 15, 'Vivere in Spagna: come iniziare?', 'Sto pensando di trasferirmi a Barcellona. Quali sono i primi passi da fare?', 'open', 123, 52, datetime('now', '-5 days'), datetime('now', '-5 days')),
(9, 2, 16, 'Visto per la Germania: quale scegliere?', 'Voglio andare a lavorare in Germania. Quale visto mi serve per uno stipendio di 40k/anno?', 'open', 89, 31, datetime('now', '-4 days'), datetime('now', '-4 days')),
(10, 2, 17, 'Costo della vita a Londra vs altre città UK', 'È conveniente vivere a Londra o meglio Manchester? Quanto spendo al mese?', 'open', 76, 28, datetime('now', '-3 days'), datetime('now', '-3 days')),
(11, 2, 18, 'Imparare il portoghese in Portogallo', 'Voglio imparare il portoghese vivendo in Portogallo. Quanto tempo mi serve?', 'open', 45, 14, datetime('now', '-2 days'), datetime('now', '-2 days')),
(12, 2, 19, 'Trasferimento in Australia: requisiti e costi', 'Quali sono i requisiti per trasferirsi in Australia come italiano? Quanto costa il processo?', 'open', 98, 39, datetime('now', '-1 days'), datetime('now', '-1 days')),
(13, 2, 20, 'Doppia cittadinanza italo-francese: come ottenerla?', 'Mio padre è francese. Posso richiedere la doppia cittadinanza? Come funziona?', 'open', 52, 16, datetime('now'), datetime('now')),
(14, 2, 21, 'Vivere negli USA con visto di lavoro', 'Mi hanno offerto un lavoro negli USA. Quale visto serve e quanto costa il processo?', 'open', 134, 58, datetime('now', '-6 days'), datetime('now', '-6 days')),

-- Salute & Benessere (primary_category_id = 3)
(15, 3, 22, 'Dieta vegetariana: come iniziare correttamente?', 'Voglio diventare vegetariano ma ho paura di carenze nutrizionali. Quali alimenti non possono mancare?', 'open', 87, 29, datetime('now', '-5 days'), datetime('now', '-5 days')),
(16, 3, 23, 'Migliorare il sonno: tecniche scientifiche', 'Non dormo bene. Quali sono i metodi più efficaci secondo la scienza per migliorare il sonno?', 'open', 156, 67, datetime('now', '-4 days'), datetime('now', '-4 days')),
(17, 3, 24, 'Palestra: scheda per principianti', 'Sono totalmente sedentario. Da dove comincio? Mi serve una guida per il primo mese in palestra.', 'open', 124, 45, datetime('now', '-3 days'), datetime('now', '-3 days')),
(18, 3, 25, 'Ansia e stress: aiuti naturali', 'Ho attacchi di ansia frequenti. Ci sono rimedi naturali che funzionano davvero?', 'open', 98, 37, datetime('now', '-2 days'), datetime('now', '-2 days')),
(19, 3, 26, 'Perdere peso senza diete estreme', 'Come posso perdere 10 kg in modo sano senza soffrire la fame?', 'open', 167, 73, datetime('now', '-1 days'), datetime('now', '-1 days')),
(20, 3, 27, 'Meditazione per principianti', 'Voglio iniziare a meditare. Come comincio? Bastano 5 minuti al giorno?', 'open', 76, 24, datetime('now'), datetime('now')),
(21, 3, 28, 'Correre una maratona: training plan', 'Voglio correre una maratona il prossimo anno. Quanto tempo mi serve per prepararmi?', 'open', 89, 31, datetime('now', '-6 days'), datetime('now', '-6 days')),

-- Finanze Personali (primary_category_id = 4)
(1, 4, 29, 'Investire 10.000 euro: dove iniziare?', 'Ho 10.000 euro da investire. Devo mettere tutto in ETF o conviene diversificare?', 'open', 203, 89, datetime('now', '-5 days'), datetime('now', '-5 days')),
(2, 4, 30, 'Comprare casa: mutuo o affitto?', 'Mi conviene comprare casa con un mutuo o continuare ad affittare? Ho 50k di risparmio.', 'open', 178, 72, datetime('now', '-4 days'), datetime('now', '-4 days')),
(3, 4, 31, 'Criptovalute: investimento serio o truffa?', 'Tutti ne parlano. Vale davvero la pena investire in criptovalute nel 2025?', 'open', 145, 61, datetime('now', '-3 days'), datetime('now', '-3 days')),
(4, 4, 32, 'Pensione privata: vale la pena?', 'Mi conviene sottoscrivere un fondo pensione privato? Quanto mi costa?', 'open', 92, 35, datetime('now', '-2 days'), datetime('now', '-2 days')),
(5, 4, 33, 'Tasse: come ridurre il carico fiscale legalmente', 'Sono freelance. Quali sono le strategie legali per ridurre le tasse?', 'open', 134, 52, datetime('now', '-1 days'), datetime('now', '-1 days')),
(6, 4, 34, 'Assicurazioni: quali servono davvero?', 'Quali assicurazioni sono veramente importanti? Quale mancanza costa di più?', 'open', 67, 21, datetime('now'), datetime('now')),
(7, 4, 35, 'Finanziare un progetto: crowdfunding o prestito?', 'Voglio lanciare un progetto che necessita 50.000 euro. Meglio crowdfunding o prestito bancario?', 'open', 54, 18, datetime('now', '-6 days'), datetime('now', '-6 days')),

-- Istruzione & Formazione (primary_category_id = 5)
(8, 5, 36, 'Laurea online vs in presenza nel 2025', 'Vale la pena fare una laurea online? È riconosciuta come quella in presenza?', 'open', 112, 42, datetime('now', '-5 days'), datetime('now', '-5 days')),
(9, 5, 37, 'Imparare a programmare: linguaggi da scegliere', 'Voglio imparare a programmare. Da quale linguaggio conviene partire nel 2025?', 'open', 189, 76, datetime('now', '-4 days'), datetime('now', '-4 days')),
(10, 5, 38, 'Corso gratuito vs corso a pagamento', 'Ci sono corsi gratuiti online validi o devo per forza pagare? Raccomandazioni?', 'open', 98, 38, datetime('now', '-3 days'), datetime('now', '-3 days')),
(11, 5, 39, 'Master MBA: conviene davvero investire?', 'Un MBA online costa 15.000 euro. Mi aumenterà davvero lo stipendio?', 'open', 76, 28, datetime('now', '-2 days'), datetime('now', '-2 days')),
(12, 5, 40, 'Lingue straniere: quale imparare dopo l\'inglese?', 'Parlo inglese bene. Quale lingua mi conviene imparare per il lavoro?', 'open', 143, 55, datetime('now', '-1 days'), datetime('now', '-1 days')),
(13, 5, 41, 'Certificazioni online riconosciute dal mercato', 'Quali certificazioni online sono riconosciute dalle aziende nel 2025?', 'open', 89, 33, datetime('now'), datetime('now')),
(14, 5, 42, 'Apprendistato vs università: percorso migliore', 'Devo scegliere tra apprendistato e università. Cosa conviene di più?', 'open', 67, 24, datetime('now', '-6 days'), datetime('now', '-6 days')),

-- Hobby & Tempo Libero (primary_category_id = 6)
(15, 6, 43, 'Fotografia: come iniziare da zero', 'Mi interessa la fotografia ma non ho attrezzature. Da dove comincio?', 'open', 76, 26, datetime('now', '-5 days'), datetime('now', '-5 days')),
(16, 6, 44, 'Gaming: quale console scegliere nel 2025?', 'Voglio comprarmi una console. PS5 vs Xbox vs Nintendo Switch? Consigli?', 'open', 198, 84, datetime('now', '-4 days'), datetime('now', '-4 days')),
(17, 6, 45, 'Leggere più libri: strategie efficaci', 'Leggo poco perché mi manca il tempo. Come posso leggere più libri?', 'open', 123, 46, datetime('now', '-3 days'), datetime('now', '-3 days')),
(18, 6, 46, 'Imparare la chitarra da autodidatta', 'Posso imparare chitarra da autodidatta online o mi serve un insegnante?', 'open', 145, 58, datetime('now', '-2 days'), datetime('now', '-2 days')),
(19, 6, 47, 'Disegno digitale: software e hardware consigliati', 'Voglio iniziare a disegnare digitalmente. Mi serve una tavoletta grafica? Quale?', 'open', 89, 34, datetime('now', '-1 days'), datetime('now', '-1 days')),
(20, 6, 48, 'Viaggi low-cost in Europa', 'Voglio visitare 5 paesi europei con 2000 euro. È possibile? Consigli?', 'open', 156, 67, datetime('now'), datetime('now')),
(21, 6, 49, 'Kickboxing per donne principianti', 'Non ho mai fatto sport. La kickboxing è adatta anche per chi non è allenato?', 'open', 72, 27, datetime('now', '-6 days'), datetime('now', '-6 days')),

-- Relazioni & Famiglia (primary_category_id = 7)
(22, 7, 50, 'Prime convivenza: come gestire i conflitti', 'Convivo con il mio partner da 3 mesi. Come gestire il primo grosso conflitto?', 'open', 134, 51, datetime('now', '-5 days'), datetime('now', '-5 days')),
(23, 7, 51, 'Figli: quando fare il grande passo?', 'Siamo una coppia ma indecisi su avere figli. Quando è il momento giusto?', 'open', 112, 42, datetime('now', '-4 days'), datetime('now', '-4 days')),
(24, 7, 52, 'Conflitti con i genitori da adulti', 'Vivo ancora con i genitori a 28 anni e non riusciamo più ad andare d\'accordo. Come risolvere?', 'open', 98, 38, datetime('now', '-3 days'), datetime('now', '-3 days')),
(1, 7, 53, 'Amicizie che si perdono col tempo', 'Sto perdendo i contatti con i miei amici storici. Come mantenere le amicizie da adulti?', 'open', 145, 56, datetime('now', '-2 days'), datetime('now', '-2 days')),
(2, 7, 54, 'Relazione a distanza: come funziona?', 'Mi sta per offrire un lavoro all\'estero ma abbiamo una relazione seria. Vale la pena provare a distanza?', 'open', 167, 72, datetime('now', '-1 days'), datetime('now', '-1 days'));

-- ========== AGGIORNA TOTALI E COUNTER ==========
-- Riconteggia upvotes per categoria
UPDATE category SET 
    icon = icon  -- Placeholder per ricalcolate il trigger
WHERE id IN (SELECT DISTINCT primary_category_id FROM community_questions WHERE primary_category_id IS NOT NULL);

-- Riconteggia visualizzazioni
UPDATE community_questions 
SET views = CAST(RANDOM() * 200 AS INTEGER) + 10
WHERE primary_category_id IS NOT NULL;

-- Verifica inserimenti
-- Per SQLite:
-- SELECT COUNT(*) as total_questions, COUNT(DISTINCT primary_category_id) as categories FROM community_questions;
-- SELECT primary_category_id, COUNT(*) as questions_count FROM community_questions GROUP BY primary_category_id;

-- Per PostgreSQL:
-- SELECT COUNT(*) as total_questions, COUNT(DISTINCT primary_category_id) as categories FROM community_questions;
-- SELECT primary_category_id, COUNT(*) as questions_count FROM community_questions GROUP BY primary_category_id;

-- Totale: 48 domande inserite con dati gerarchici (primary_category_id + category_id)
