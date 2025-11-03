-- Inserimento fasce orarie random per novembre 2025 (utenti ID 11-78)
-- SQLite Script

-- User 11: Consulente attivo (Lunedì, Mercoledì, Venerdì)
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(11, '2025-11-03', '09:00', '12:00', 180, 0, 'available', 1),
(11, '2025-11-03', '14:00', '17:00', 180, 0, 'available', 1),
(11, '2025-11-05', '10:00', '13:00', 180, 0, 'available', 1),
(11, '2025-11-07', '09:00', '11:30', 150, 0, 'available', 1),
(11, '2025-11-07', '15:00', '18:00', 180, 0, 'available', 1),
(11, '2025-11-10', '09:00', '12:00', 180, 0, 'available', 1),
(11, '2025-11-12', '14:00', '17:30', 210, 0, 'available', 1),
(11, '2025-11-14', '10:00', '12:00', 120, 0, 'available', 1),
(11, '2025-11-17', '09:00', '13:00', 240, 0, 'available', 1),
(11, '2025-11-19', '14:00', '17:00', 180, 0, 'available', 1);

-- User 12: Disponibilità mattutina
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(12, '2025-11-04', '08:00', '11:00', 180, 0, 'available', 1),
(12, '2025-11-06', '08:30', '10:30', 120, 0, 'available', 1),
(12, '2025-11-08', '09:00', '12:00', 180, 0, 'available', 1),
(12, '2025-11-11', '08:00', '10:00', 120, 0, 'available', 1),
(12, '2025-11-13', '09:00', '11:30', 150, 0, 'available', 1),
(12, '2025-11-15', '08:00', '11:00', 180, 0, 'available', 1),
(12, '2025-11-18', '09:00', '12:00', 180, 0, 'available', 1),
(12, '2025-11-20', '08:30', '10:30', 120, 0, 'available', 1);

-- User 15: Disponibilità pomeridiana/serale
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(15, '2025-11-03', '15:00', '19:00', 240, 0, 'available', 1),
(15, '2025-11-05', '16:00', '20:00', 240, 0, 'available', 1),
(15, '2025-11-07', '14:00', '18:00', 240, 0, 'available', 1),
(15, '2025-11-10', '15:30', '19:30', 240, 0, 'available', 1),
(15, '2025-11-12', '16:00', '19:00', 180, 0, 'available', 1),
(15, '2025-11-14', '15:00', '18:00', 180, 0, 'available', 1),
(15, '2025-11-17', '16:00', '20:00', 240, 0, 'available', 1),
(15, '2025-11-19', '14:30', '18:30', 240, 0, 'available', 1);

-- User 18: Full day (martedì e giovedì)
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(18, '2025-11-04', '09:00', '13:00', 240, 0, 'available', 1),
(18, '2025-11-04', '14:30', '17:30', 180, 0, 'available', 1),
(18, '2025-11-06', '10:00', '12:00', 120, 0, 'available', 1),
(18, '2025-11-06', '15:00', '18:00', 180, 0, 'available', 1),
(18, '2025-11-11', '09:00', '12:00', 180, 0, 'available', 1),
(18, '2025-11-13', '09:30', '13:00', 210, 0, 'available', 1),
(18, '2025-11-13', '14:00', '17:00', 180, 0, 'available', 1),
(18, '2025-11-18', '10:00', '13:00', 180, 0, 'available', 1),
(18, '2025-11-20', '09:00', '12:00', 180, 0, 'available', 1);

-- User 23: Weekend specialist
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(23, '2025-11-01', '10:00', '14:00', 240, 0, 'available', 1),
(23, '2025-11-02', '11:00', '15:00', 240, 0, 'available', 1),
(23, '2025-11-08', '10:00', '13:00', 180, 0, 'available', 1),
(23, '2025-11-09', '11:00', '16:00', 300, 0, 'available', 1),
(23, '2025-11-15', '10:00', '14:00', 240, 0, 'available', 1),
(23, '2025-11-16', '11:00', '15:00', 240, 0, 'available', 1),
(23, '2025-11-22', '10:00', '13:00', 180, 0, 'available', 1),
(23, '2025-11-23', '11:00', '16:00', 300, 0, 'available', 1);

-- User 27: Disponibilità regolare (Lun-Ven mattina)
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(27, '2025-11-03', '09:00', '12:00', 180, 0, 'available', 1),
(27, '2025-11-04', '09:00', '12:00', 180, 0, 'available', 1),
(27, '2025-11-05', '09:00', '12:00', 180, 0, 'available', 1),
(27, '2025-11-06', '09:00', '12:00', 180, 0, 'available', 1),
(27, '2025-11-07', '09:00', '12:00', 180, 0, 'available', 1),
(27, '2025-11-10', '09:00', '12:00', 180, 0, 'available', 1),
(27, '2025-11-11', '09:00', '12:00', 180, 0, 'available', 1),
(27, '2025-11-12', '09:00', '12:00', 180, 0, 'available', 1),
(27, '2025-11-13', '09:00', '12:00', 180, 0, 'available', 1),
(27, '2025-11-14', '09:00', '12:00', 180, 0, 'available', 1);

-- User 31: Flessibile (giorni vari)
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(31, '2025-11-05', '10:00', '13:00', 180, 0, 'available', 1),
(31, '2025-11-05', '15:00', '17:00', 120, 0, 'available', 1),
(31, '2025-11-08', '11:00', '14:00', 180, 0, 'available', 1),
(31, '2025-11-12', '09:00', '12:00', 180, 0, 'available', 1),
(31, '2025-11-15', '14:00', '18:00', 240, 0, 'available', 1),
(31, '2025-11-19', '10:00', '13:00', 180, 0, 'available', 1),
(31, '2025-11-22', '09:00', '11:00', 120, 0, 'available', 1),
(31, '2025-11-26', '15:00', '18:00', 180, 0, 'available', 1);

-- User 35: Consulente intensivo
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(35, '2025-11-03', '09:00', '12:00', 180, 0, 'available', 1),
(35, '2025-11-03', '14:00', '18:00', 240, 0, 'available', 1),
(35, '2025-11-06', '09:00', '12:00', 180, 0, 'available', 1),
(35, '2025-11-06', '14:00', '17:00', 180, 0, 'available', 1),
(35, '2025-11-10', '10:00', '13:00', 180, 0, 'available', 1),
(35, '2025-11-10', '15:00', '19:00', 240, 0, 'available', 1),
(35, '2025-11-13', '09:00', '12:00', 180, 0, 'available', 1),
(35, '2025-11-13', '14:00', '18:00', 240, 0, 'available', 1),
(35, '2025-11-17', '09:00', '13:00', 240, 0, 'available', 1),
(35, '2025-11-20', '14:00', '18:00', 240, 0, 'available', 1);

-- User 40: Orari brevi ma frequenti
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(40, '2025-11-04', '10:00', '11:30', 90, 0, 'available', 1),
(40, '2025-11-05', '15:00', '16:30', 90, 0, 'available', 1),
(40, '2025-11-07', '11:00', '12:30', 90, 0, 'available', 1),
(40, '2025-11-08', '14:00', '15:30', 90, 0, 'available', 1),
(40, '2025-11-11', '10:00', '11:30', 90, 0, 'available', 1),
(40, '2025-11-12', '15:00', '16:30', 90, 0, 'available', 1),
(40, '2025-11-14', '11:00', '12:30', 90, 0, 'available', 1),
(40, '2025-11-15', '14:00', '15:30', 90, 0, 'available', 1),
(40, '2025-11-18', '10:00', '11:30', 90, 0, 'available', 1),
(40, '2025-11-19', '15:00', '16:30', 90, 0, 'available', 1);

-- User 45: Disponibilità variabile
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(45, '2025-11-06', '09:00', '11:00', 120, 0, 'available', 1),
(45, '2025-11-09', '14:00', '17:00', 180, 0, 'available', 1),
(45, '2025-11-13', '10:00', '12:00', 120, 0, 'available', 1),
(45, '2025-11-16', '15:00', '18:00', 180, 0, 'available', 1),
(45, '2025-11-20', '09:00', '11:00', 120, 0, 'available', 1),
(45, '2025-11-23', '14:00', '17:00', 180, 0, 'available', 1),
(45, '2025-11-27', '10:00', '13:00', 180, 0, 'available', 1);

-- User 50: Mix mattina/pomeriggio
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(50, '2025-11-03', '08:30', '11:00', 150, 0, 'available', 1),
(50, '2025-11-05', '14:00', '16:30', 150, 0, 'available', 1),
(50, '2025-11-07', '09:00', '11:30', 150, 0, 'available', 1),
(50, '2025-11-10', '15:00', '17:30', 150, 0, 'available', 1),
(50, '2025-11-12', '08:30', '11:00', 150, 0, 'available', 1),
(50, '2025-11-14', '14:00', '16:30', 150, 0, 'available', 1),
(50, '2025-11-17', '09:00', '11:30', 150, 0, 'available', 1),
(50, '2025-11-19', '15:00', '17:30', 150, 0, 'available', 1);

-- User 55: Consulente serale
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(55, '2025-11-04', '18:00', '21:00', 180, 0, 'available', 1),
(55, '2025-11-06', '17:30', '20:30', 180, 0, 'available', 1),
(55, '2025-11-08', '18:00', '21:00', 180, 0, 'available', 1),
(55, '2025-11-11', '17:30', '20:30', 180, 0, 'available', 1),
(55, '2025-11-13', '18:00', '21:00', 180, 0, 'available', 1),
(55, '2025-11-15', '17:30', '20:30', 180, 0, 'available', 1),
(55, '2025-11-18', '18:00', '21:00', 180, 0, 'available', 1),
(55, '2025-11-20', '17:30', '20:30', 180, 0, 'available', 1);

-- User 60: Disponibilità concentrata (3 giorni)
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(60, '2025-11-05', '09:00', '12:00', 180, 0, 'available', 1),
(60, '2025-11-05', '14:00', '18:00', 240, 0, 'available', 1),
(60, '2025-11-12', '09:00', '12:00', 180, 0, 'available', 1),
(60, '2025-11-12', '14:00', '18:00', 240, 0, 'available', 1),
(60, '2025-11-19', '09:00', '12:00', 180, 0, 'available', 1),
(60, '2025-11-19', '14:00', '18:00', 240, 0, 'available', 1),
(60, '2025-11-26', '09:00', '13:00', 240, 0, 'available', 1);

-- User 65: Consulente sporadico
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(65, '2025-11-07', '10:00', '13:00', 180, 0, 'available', 1),
(65, '2025-11-14', '14:00', '17:00', 180, 0, 'available', 1),
(65, '2025-11-21', '10:00', '13:00', 180, 0, 'available', 1),
(65, '2025-11-28', '14:00', '17:00', 180, 0, 'available', 1);

-- User 70: Disponibilità pranzo
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(70, '2025-11-03', '12:00', '14:00', 120, 0, 'available', 1),
(70, '2025-11-05', '12:00', '14:00', 120, 0, 'available', 1),
(70, '2025-11-07', '12:00', '14:00', 120, 0, 'available', 1),
(70, '2025-11-10', '12:00', '14:00', 120, 0, 'available', 1),
(70, '2025-11-12', '12:00', '14:00', 120, 0, 'available', 1),
(70, '2025-11-14', '12:00', '14:00', 120, 0, 'available', 1),
(70, '2025-11-17', '12:00', '14:00', 120, 0, 'available', 1),
(70, '2025-11-19', '12:00', '14:00', 120, 0, 'available', 1);

-- User 75: Mix orari vari
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(75, '2025-11-04', '09:00', '11:00', 120, 0, 'available', 1),
(75, '2025-11-06', '15:00', '17:00', 120, 0, 'available', 1),
(75, '2025-11-08', '11:00', '13:00', 120, 0, 'available', 1),
(75, '2025-11-11', '14:00', '16:00', 120, 0, 'available', 1),
(75, '2025-11-13', '10:00', '12:00', 120, 0, 'available', 1),
(75, '2025-11-15', '16:00', '18:00', 120, 0, 'available', 1),
(75, '2025-11-18', '09:00', '11:00', 120, 0, 'available', 1),
(75, '2025-11-20', '15:00', '17:00', 120, 0, 'available', 1);

-- User 78: Consulente weekend + sera
INSERT INTO availability_block (user_id, date, start_time, end_time, total_minutes, booked_minutes, status, is_active) VALUES
(78, '2025-11-01', '10:00', '14:00', 240, 0, 'available', 1),
(78, '2025-11-02', '10:00', '14:00', 240, 0, 'available', 1),
(78, '2025-11-04', '18:00', '20:00', 120, 0, 'available', 1),
(78, '2025-11-08', '10:00', '14:00', 240, 0, 'available', 1),
(78, '2025-11-09', '10:00', '14:00', 240, 0, 'available', 1),
(78, '2025-11-11', '18:00', '20:00', 120, 0, 'available', 1),
(78, '2025-11-15', '10:00', '14:00', 240, 0, 'available', 1),
(78, '2025-11-16', '10:00', '14:00', 240, 0, 'available', 1),
(78, '2025-11-18', '18:00', '20:00', 120, 0, 'available', 1),
(78, '2025-11-22', '10:00', '14:00', 240, 0, 'available', 1);

-- Riepilogo: 
-- Inseriti circa 150+ slot di disponibilità distribuiti su tutto novembre
-- Pattern variabili: mattina, pomeriggio, sera, weekend, full day
-- Diversi stili di consulenza per rendere i dati più realistici
