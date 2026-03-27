-- ============================================================
-- Inserimento recensioni e booking fake per tutti gli utenti
-- PostgreSQL only
-- ============================================================

-- Pulizia recensioni esistenti
DELETE FROM reviews;

-- Pulizia booking fake precedenti (se esistono)
DELETE FROM booking WHERE id >= 10000;

DO $$
DECLARE
    all_users int[] := ARRAY[
        11,12,13,14,15,16,17,18,19,20,
        21,22,23,24,25,26,27,28,29,30,
        31,32,33,34,35,36,37,38,39,40,
        41,42,43,44,45,46,47,48,49,50,
        51,52,53,54,55,56,57,58,59,60,
        61,62,63,64,65,66,67,68,69,70,
        71,72,73,74,75,76,77,81,87,88,
        89,90,91,92,93,94,95,96,97,98,
        99,100,101,102,103,104,105,106,107,108,
        109,110,111,112,113,114,115
    ];

    comments text[] := ARRAY[
        'Molto professionale e competente. Mi ha aiutato a risolvere il problema in poco tempo.',
        'Esperienza fantastica! Il consulente era preparatissimo e molto disponibile.',
        'Buona consulenza, anche se avrei preferito più tempo per approfondire alcuni aspetti.',
        'Eccellente! Ha capito subito le mie esigenze e mi ha dato consigli pratici utilissimi.',
        'Consulente molto cordiale e paziente. Ha spiegato tutto in modo chiaro.',
        'Ottima esperienza, tornerò sicuramente per un''altra sessione.',
        'Ha risposto a tutte le mie domande con competenza. Consigliato!',
        'Sessione molto utile, mi ha dato una prospettiva completamente nuova sul problema.',
        'Professionista serio e preparato. La consulenza è valsa ogni centesimo.',
        'Buon consulente ma un po'' frettoloso nella spiegazione.',
        'Incredibilmente preparato! Ha risolto in 30 minuti un problema che avevo da settimane.',
        'Consulenza nella media. Niente di eccezionale ma ha fatto il suo lavoro.',
        'Super disponibile e attento alle mie esigenze. Lo consiglio vivamente!',
        'La comunicazione poteva essere migliore, ma i consigli ricevuti erano validi.',
        'Esperienza molto positiva. Mi ha guidato passo passo nella risoluzione.',
        'Davvero bravo! Ha una capacità rara di spiegare concetti complessi in modo semplice.',
        'Consulenza utile, anche se mi aspettavo qualcosa di più approfondito.',
        'Persona molto alla mano e competente. Mi sono sentito subito a mio agio.',
        'Ha superato le mie aspettative. Soluzione chiara e implementabile subito.',
        'Buona preparazione tecnica. Avrei voluto solo un po'' più di esempi pratici.',
        'Consiglio eccezionale su un tema complesso. Molto soddisfatto del risultato.',
        'Puntuale, preciso e molto chiaro. Un vero professionista.',
        'Mi ha dato degli spunti che non avevo considerato. Molto utile!',
        'Ottimo rapporto qualità-prezzo. La sessione è stata densa di contenuti.',
        'Ho apprezzato molto la sua capacità di ascolto prima di dare consigli.',
        'Consulenza rapida ma efficace. Ha centrato subito il punto.',
        'Molto preparato nel suo campo. Le soluzioni proposte erano concrete e applicabili.',
        'Gentilissimo e disponibile. Ha anche seguito via messaggio dopo la consulenza.',
        'Esperienza discreta. Alcuni consigli utili ma nulla di sorprendente.',
        'Bravissimo! Mi ha fatto risparmiare tempo e denaro con i suoi suggerimenti.'
    ];

    times text[] := ARRAY['09:00','09:30','10:00','10:30','11:00','11:30','14:00','14:30','15:00','15:30','16:00','16:30','17:00'];

    v_consultant_id int;
    v_client_id int;
    v_client_idx int;
    v_booking_id int := 10000;
    v_review_count int;
    v_num_users int;
    v_rating_h int;
    v_rating_p int;
    v_rating_c int;
    v_comment text;
    v_base_date date;
    v_time text;
    v_rand float;
BEGIN
    v_num_users := array_length(all_users, 1);

    FOR i IN 1..v_num_users LOOP
        v_consultant_id := all_users[i];

        -- Numero di review per questo consulente (2-5)
        v_rand := random();
        IF v_rand < 0.25 THEN
            v_review_count := 2;
        ELSIF v_rand < 0.55 THEN
            v_review_count := 3;
        ELSIF v_rand < 0.80 THEN
            v_review_count := 4;
        ELSE
            v_review_count := 5;
        END IF;

        FOR j IN 1..v_review_count LOOP
            -- Scegli un client diverso dal consultant
            LOOP
                v_client_idx := 1 + floor(random() * v_num_users)::int;
                IF v_client_idx > v_num_users THEN v_client_idx := v_num_users; END IF;
                v_client_id := all_users[v_client_idx];
                EXIT WHEN v_client_id != v_consultant_id;
            END LOOP;

            v_booking_id := v_booking_id + 1;
            v_base_date := CURRENT_DATE - (1 + floor(random() * 90))::int;  -- ultimi 90 giorni
            v_time := times[1 + floor(random() * array_length(times, 1))::int];
            IF v_time IS NULL THEN v_time := '10:00'; END IF;

            -- Inserisci booking completato
            INSERT INTO booking (
                id, client_user_id, consultant_user_id,
                booking_date, start_time, end_time, duration_minutes,
                status, payment_status,
                recording_status, recording_session_count,
                created_at, updated_at
            ) VALUES (
                v_booking_id, v_client_id, v_consultant_id,
                v_base_date, v_time, v_time, 30,
                'completed', 'paid',
                'not_started', 1,
                v_base_date, v_base_date
            );

            -- Rating pesato verso l'alto (60% -> 5, 25% -> 4, 10% -> 3, 5% -> 2)
            v_rand := random();
            IF v_rand < 0.05 THEN v_rating_h := 2;
            ELSIF v_rand < 0.15 THEN v_rating_h := 3;
            ELSIF v_rand < 0.40 THEN v_rating_h := 4;
            ELSE v_rating_h := 5;
            END IF;

            v_rand := random();
            IF v_rand < 0.05 THEN v_rating_p := 2;
            ELSIF v_rand < 0.15 THEN v_rating_p := 3;
            ELSIF v_rand < 0.40 THEN v_rating_p := 4;
            ELSE v_rating_p := 5;
            END IF;

            v_rand := random();
            IF v_rand < 0.05 THEN v_rating_c := 2;
            ELSIF v_rand < 0.15 THEN v_rating_c := 3;
            ELSIF v_rand < 0.40 THEN v_rating_c := 4;
            ELSE v_rating_c := 5;
            END IF;

            -- Commento (70% con commento, 30% senza)
            IF random() < 0.70 THEN
                v_client_idx := 1 + floor(random() * array_length(comments, 1))::int;
                IF v_client_idx > array_length(comments, 1) THEN v_client_idx := array_length(comments, 1); END IF;
                v_comment := comments[v_client_idx];
            ELSE
                v_comment := NULL;
            END IF;

            -- Inserisci review
            INSERT INTO reviews (
                booking_id, reviewer_user_id, consultant_user_id,
                rating_helpful, rating_prepared, rating_communication,
                comment, created_at
            ) VALUES (
                v_booking_id, v_client_id, v_consultant_id,
                v_rating_h, v_rating_p, v_rating_c,
                v_comment, v_base_date + interval '1 hour'
            );

        END LOOP;
    END LOOP;

    -- Reset sequenze
    PERFORM setval(pg_get_serial_sequence('booking', 'id'), (SELECT MAX(id) FROM booking));
    PERFORM setval(pg_get_serial_sequence('reviews', 'id'), (SELECT MAX(id) FROM reviews));

    RAISE NOTICE 'Inserite % recensioni per % consulenti', v_booking_id - 10000, v_num_users;
END $$;

-- Verifica
SELECT 'Bookings fake:' AS info, COUNT(*) AS totale FROM booking WHERE id >= 10000
UNION ALL
SELECT 'Recensioni totali:', COUNT(*) FROM reviews;
