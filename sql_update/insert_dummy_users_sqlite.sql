-- =====================================================================
-- DUMMY USERS PER TESTARE LE CATEGORIE (SQLite)
-- =====================================================================

-- Abilita i vincoli di chiave esterna
PRAGMA foreign_keys = ON;

-- =====================================================================
-- 1. LAVORO & CARRIERA (id=1)
-- =====================================================================

INSERT INTO "user" (email, password_md5, nome, cognome, professione, category_id, prezzo_consulenza, bollini, consulenze_vendute, profile_picture, is_verified) VALUES
('elena.russo@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Elena', 'Russo', 'Career Transition Coach', 1, 150, 5, 12, 'https://i.imgur.com/avatar1.jpg', 1),
('marco.villa@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Marco', 'Villa', 'Recruitment Specialist', 1, 120, 4, 8, 'https://i.imgur.com/avatar2.jpg', 1),
('anna.bianchi@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Anna', 'Bianchi', 'CV & LinkedIn Expert', 1, 80, 3, 6, 'https://i.imgur.com/avatar3.jpg', 1);

-- =====================================================================
-- 2. VITA ALL'ESTERO (id=2)
-- =====================================================================

INSERT INTO "user" (email, password_md5, nome, cognome, professione, category_id, prezzo_consulenza, bollini, consulenze_vendute, profile_picture, is_verified) VALUES
('luca.marini@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Luca', 'Marini', 'Remote Work Expert & Digital Nomad', 2, 130, 5, 14, 'https://i.imgur.com/avatar4.jpg', 1),
('giulia.ferrari@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Giulia', 'Ferrari', 'Expat Life Coach', 2, 110, 4, 9, 'https://i.imgur.com/avatar5.jpg', 1),
('paolo.rossi@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Paolo', 'Rossi', 'Visa & Immigration Consultant', 2, 140, 4, 7, 'https://i.imgur.com/avatar6.jpg', 1);

-- =====================================================================
-- 3. VIAGGIATORI & NOMADI DIGITALI (id=3)
-- =====================================================================

INSERT INTO "user" (email, password_md5, nome, cognome, professione, category_id, prezzo_consulenza, bollini, consulenze_vendute, profile_picture, is_verified) VALUES
('simona.costa@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Simona', 'Costa', 'Travel Planning Specialist', 3, 100, 5, 16, 'https://i.imgur.com/avatar7.jpg', 1),
('davide.bruno@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Davide', 'Bruno', 'Digital Nomad Coach', 3, 125, 4, 11, 'https://i.imgur.com/avatar8.jpg', 1),
('francesca.gallo@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Francesca', 'Gallo', 'Budget Travel Expert', 3, 90, 3, 8, 'https://i.imgur.com/avatar9.jpg', 1);

-- =====================================================================
-- 4. ESPERIENZE DI VITA (id=4)
-- =====================================================================

INSERT INTO "user" (email, password_md5, nome, cognome, professione, category_id, prezzo_consulenza, bollini, consulenze_vendute, profile_picture, is_verified) VALUES
('alessio.romano@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Alessio', 'Romano', 'Life Coach & Transformation Expert', 4, 140, 5, 13, 'https://i.imgur.com/avatar10.jpg', 1),
('sara.colombo@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Sara', 'Colombo', 'Relationship & Family Consultant', 4, 115, 4, 10, 'https://i.imgur.com/avatar11.jpg', 1),
('lorenzo.russo@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Lorenzo', 'Russo', 'Personal Development Coach', 4, 105, 3, 7, 'https://i.imgur.com/avatar12.jpg', 1);

-- =====================================================================
-- 5. SETTORI SPECIFICI (id=5)
-- =====================================================================

INSERT INTO "user" (email, password_md5, nome, cognome, professione, category_id, prezzo_consulenza, bollini, consulenze_vendute, profile_picture, is_verified) VALUES
('mario.ferretti@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Mario', 'Ferretti', 'Real Estate Advisor', 5, 160, 5, 15, 'https://i.imgur.com/avatar13.jpg', 1),
('valentina.napoli@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Valentina', 'Napoli', 'Personal Finance Consultant', 5, 130, 4, 12, 'https://i.imgur.com/avatar14.jpg', 1),
('carlo.leone@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Carlo', 'Leone', 'Restaurant Owner & Food Advisor', 5, 120, 4, 9, 'https://i.imgur.com/avatar15.jpg', 1),
('isabella.santoro@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Isabella', 'Santoro', 'Fashion & Styling Expert', 5, 110, 3, 6, 'https://i.imgur.com/avatar16.jpg', 1);

-- =====================================================================
-- 6. MENTORSHIP & CRESCITA PERSONALE (id=6)
-- =====================================================================

INSERT INTO "user" (email, password_md5, nome, cognome, professione, category_id, prezzo_consulenza, bollini, consulenze_vendute, profile_picture, is_verified) VALUES
('chiara.ricci@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Chiara', 'Ricci', 'Executive Coach & Mentor', 6, 150, 5, 14, 'https://i.imgur.com/avatar17.jpg', 1),
('roberto.moretti@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Roberto', 'Moretti', 'Mindfulness & Stress Management', 6, 100, 4, 10, 'https://i.imgur.com/avatar18.jpg', 1),
('marta.conti@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Marta', 'Conti', 'Goal Setting Specialist', 6, 95, 3, 7, 'https://i.imgur.com/avatar19.jpg', 1);

-- =====================================================================
-- 7. SPORT & WELLNESS (id=7)
-- =====================================================================

INSERT INTO "user" (email, password_md5, nome, cognome, professione, category_id, prezzo_consulenza, bollini, consulenze_vendute, profile_picture, is_verified) VALUES
('tommaso.rizzo@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Tommaso', 'Rizzo', 'Personal Trainer & Fitness Coach', 7, 110, 5, 16, 'https://i.imgur.com/avatar20.jpg', 1),
('ludovica.gatti@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Ludovica', 'Gatti', 'Nutrition & Wellness Specialist', 7, 100, 4, 11, 'https://i.imgur.com/avatar21.jpg', 1),
('enrico.lombardi@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Enrico', 'Lombardi', 'Running Coach & Athlete', 7, 95, 3, 8, 'https://i.imgur.com/avatar22.jpg', 1);

-- =====================================================================
-- 8. GAMING & CREATORS (id=8)
-- =====================================================================

INSERT INTO "user" (email, password_md5, nome, cognome, professione, category_id, prezzo_consulenza, bollini, consulenze_vendute, profile_picture, is_verified) VALUES
('matteo.russo@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Matteo', 'Russo', 'Gaming Streamer & Strategy Coach', 8, 105, 5, 13, 'https://i.imgur.com/avatar23.jpg', 1),
('aurora.moretti@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Aurora', 'Moretti', 'Content Creator & Growth Strategist', 8, 120, 4, 10, 'https://i.imgur.com/avatar24.jpg', 1),
('riccardo.villa@helpy.it', 'e807f1fcf82d132f9bb018ca6738a19f', 'Riccardo', 'Villa', 'Video Editor & Creative Producer', 8, 100, 3, 7, 'https://i.imgur.com/avatar25.jpg', 1);

-- =====================================================================
-- TOTALE: 24 utenti finti distribuiti equamente
-- =====================================================================
-- Lavoro & Carriera: 3
-- Vita all'Estero: 3
-- Viaggiatori & Nomadi: 3
-- Esperienze di Vita: 3
-- Settori Specifici: 4
-- Mentorship: 3
-- Sport & Wellness: 3
-- Gaming & Creators: 3
-- =====================================================================
