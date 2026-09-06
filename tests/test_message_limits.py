"""Test dei limiti sulla messaggistica.

Tre problemi distinti, tutti silenziosi:
- il conteggio ripartiva solo da una prenotazione in stato 'confirmed', e 15
  minuti dopo la consulenza quello stato diventa 'completed': la conversazione
  si richiudeva da sola, stavolta per sempre;
- i messaggi di sistema (offerte di consulenza) consumavano il credito;
- i limiti configurati dall'amministratore in configuration_property venivano
  ignorati dal backend, che applicava le costanti scritte nel codice.
"""
import secrets
from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import Booking, ConfigurationProperty, Conversation, Message, User
from app.routes.messages import (
    CONFIG_KEY_MAX_LENGTH,
    CONFIG_KEY_MAX_MESSAGES,
    DEFAULT_MAX_MESSAGES_PER_CONVERSATION,
    conta_messaggi_conversazione,
    get_config_int,
    max_lunghezza_messaggio,
    max_messaggi_per_conversazione,
    svuota_cache_configurazione,
)


@pytest.fixture(autouse=True)
def cache_pulita():
    svuota_cache_configurazione()
    yield
    svuota_cache_configurazione()


@pytest.fixture
def conversazione():
    """Due utenti e la loro conversazione. Ripulisce tutto alla fine."""
    with Session(engine) as s:
        a = User(email=f"chat1-{secrets.token_hex(4)}@test.local", password_md5="x")
        b = User(email=f"chat2-{secrets.token_hex(4)}@test.local", password_md5="x")
        s.add(a)
        s.add(b)
        s.commit()
        s.refresh(a)
        s.refresh(b)
        conv = Conversation(user1_id=min(a.id, b.id), user2_id=max(a.id, b.id))
        s.add(conv)
        s.commit()
        s.refresh(conv)
        ids = (conv.id, a.id, b.id)

    yield ids

    with Session(engine) as s:
        for m in s.exec(select(Message).where(Message.conversation_id == ids[0])).all():
            s.delete(m)
        # Vanno rimosse le prenotazioni in ENTRAMBE le direzioni: SQLite riusa
        # gli id degli utenti cancellati, e una prenotazione orfana finirebbe
        # per corrispondere a una coppia di utenti creata in un test successivo.
        for bk in s.exec(
            select(Booking).where(
                (Booking.client_user_id.in_(ids[1:])) | (Booking.consultant_user_id.in_(ids[1:]))
            )
        ).all():
            s.delete(bk)
        conv = s.get(Conversation, ids[0])
        if conv:
            s.delete(conv)
        for uid in ids[1:]:
            u = s.get(User, uid)
            if u:
                s.delete(u)
        s.commit()


def _messaggi(conv_id, sender_id, quanti, quando, sistema=False):
    with Session(engine) as s:
        for i in range(quanti):
            s.add(Message(
                conversation_id=conv_id,
                sender_id=sender_id,
                content=f"messaggio {i}",
                created_at=quando + timedelta(seconds=i),
                is_system_message=sistema,
            ))
        s.commit()


def _booking(client_id, consultant_id, stato, payment, creato):
    with Session(engine) as s:
        b = Booking(
            client_user_id=client_id,
            consultant_user_id=consultant_id,
            booking_date=datetime(2026, 3, 1),
            start_time="10:00",
            end_time="11:00",
            duration_minutes=60,
            status=stato,
            payment_status=payment,
            created_at=creato,
        )
        s.add(b)
        s.commit()


class TestConteggio:
    def test_conta_i_messaggi_normali(self, conversazione):
        conv_id, a, _ = conversazione
        _messaggi(conv_id, a, 5, datetime(2026, 1, 1))
        with Session(engine) as s:
            assert conta_messaggi_conversazione(s, s.get(Conversation, conv_id)) == 5

    def test_i_messaggi_di_sistema_non_consumano_il_credito(self, conversazione):
        conv_id, a, _ = conversazione
        _messaggi(conv_id, a, 3, datetime(2026, 1, 1))
        _messaggi(conv_id, a, 4, datetime(2026, 1, 2), sistema=True)
        with Session(engine) as s:
            assert conta_messaggi_conversazione(s, s.get(Conversation, conv_id)) == 3

    def test_una_consulenza_pagata_azzera_il_conteggio(self, conversazione):
        conv_id, a, b = conversazione
        _messaggi(conv_id, a, 10, datetime(2026, 1, 1))
        _booking(a, b, "confirmed", "held", datetime(2026, 1, 5))
        _messaggi(conv_id, a, 2, datetime(2026, 1, 10))
        with Session(engine) as s:
            assert conta_messaggi_conversazione(s, s.get(Conversation, conv_id)) == 2

    def test_la_consulenza_conclusa_continua_ad_azzerare(self, conversazione):
        """È il caso che si rompeva: 15 minuti dopo la consulenza il job no-show
        porta lo stato a 'completed' e il vecchio filtro su 'confirmed' non
        corrispondeva più, facendo tornare il conteggio su tutta la cronologia."""
        conv_id, a, b = conversazione
        _messaggi(conv_id, a, 10, datetime(2026, 1, 1))
        _booking(a, b, "completed", "released", datetime(2026, 1, 5))
        _messaggi(conv_id, a, 2, datetime(2026, 1, 10))
        with Session(engine) as s:
            assert conta_messaggi_conversazione(s, s.get(Conversation, conv_id)) == 2

    def test_una_prenotazione_non_pagata_non_azzera_nulla(self, conversazione):
        conv_id, a, b = conversazione
        _messaggi(conv_id, a, 10, datetime(2026, 1, 1))
        _booking(a, b, "pending_payment", "pending", datetime(2026, 1, 5))
        _messaggi(conv_id, a, 2, datetime(2026, 1, 10))
        with Session(engine) as s:
            assert conta_messaggi_conversazione(s, s.get(Conversation, conv_id)) == 12

    def test_una_prenotazione_rimborsata_non_azzera_nulla(self, conversazione):
        conv_id, a, b = conversazione
        _messaggi(conv_id, a, 4, datetime(2026, 1, 1))
        _booking(a, b, "cancelled", "refunded", datetime(2026, 1, 5))
        _messaggi(conv_id, a, 3, datetime(2026, 1, 10))
        with Session(engine) as s:
            assert conta_messaggi_conversazione(s, s.get(Conversation, conv_id)) == 7

    def test_vale_anche_a_ruoli_invertiti(self, conversazione):
        """Il consulente può essere l'uno o l'altro dei due nella conversazione."""
        conv_id, a, b = conversazione
        _messaggi(conv_id, a, 6, datetime(2026, 1, 1))
        _booking(b, a, "confirmed", "held", datetime(2026, 1, 5))
        _messaggi(conv_id, a, 1, datetime(2026, 1, 10))
        with Session(engine) as s:
            assert conta_messaggi_conversazione(s, s.get(Conversation, conv_id)) == 1


class TestConfigurazione:
    def _imposta(self, chiave, valore):
        with Session(engine) as s:
            riga = s.exec(
                select(ConfigurationProperty)
                .where(ConfigurationProperty.property_key == chiave)
            ).first()
            if riga:
                riga.property_value = str(valore)
            else:
                riga = ConfigurationProperty(property_key=chiave, property_value=str(valore))
            s.add(riga)
            s.commit()
            return riga.id

    def _rimuovi(self, chiave):
        with Session(engine) as s:
            for riga in s.exec(
                select(ConfigurationProperty)
                .where(ConfigurationProperty.property_key == chiave)
            ).all():
                s.delete(riga)
            s.commit()

    def test_senza_riga_usa_il_default(self):
        self._rimuovi(CONFIG_KEY_MAX_MESSAGES)
        svuota_cache_configurazione()
        assert max_messaggi_per_conversazione() == DEFAULT_MAX_MESSAGES_PER_CONVERSATION

    def test_il_valore_configurato_viene_applicato(self):
        """È il bug principale: l'amministratore aveva impostato 40 e il backend
        continuava a imporre 80."""
        try:
            self._imposta(CONFIG_KEY_MAX_MESSAGES, 40)
            svuota_cache_configurazione()
            assert max_messaggi_per_conversazione() == 40

            self._imposta(CONFIG_KEY_MAX_LENGTH, 500)
            svuota_cache_configurazione()
            assert max_lunghezza_messaggio() == 500
        finally:
            self._rimuovi(CONFIG_KEY_MAX_MESSAGES)
            self._rimuovi(CONFIG_KEY_MAX_LENGTH)

    def test_valore_non_numerico_ripiega_sul_default(self):
        try:
            self._imposta(CONFIG_KEY_MAX_MESSAGES, "quaranta")
            svuota_cache_configurazione()
            assert max_messaggi_per_conversazione() == DEFAULT_MAX_MESSAGES_PER_CONVERSATION
        finally:
            self._rimuovi(CONFIG_KEY_MAX_MESSAGES)

    def test_la_cache_evita_una_query_per_messaggio(self):
        self._rimuovi(CONFIG_KEY_MAX_MESSAGES)
        svuota_cache_configurazione()
        primo = get_config_int(CONFIG_KEY_MAX_MESSAGES, 99)
        # cambia il valore sotto il naso della cache: deve restare il precedente
        try:
            self._imposta(CONFIG_KEY_MAX_MESSAGES, 7)
            assert get_config_int(CONFIG_KEY_MAX_MESSAGES, 99) == primo
            svuota_cache_configurazione()
            assert get_config_int(CONFIG_KEY_MAX_MESSAGES, 99) == 7
        finally:
            self._rimuovi(CONFIG_KEY_MAX_MESSAGES)


class TestEndpointChatConfig:
    def test_espone_gli_stessi_valori_applicati_dal_backend(self, client):
        resp = client.get("/api/chat-config")
        assert resp.status_code == 200
        dati = resp.json()
        assert dati["max_messages"] == max_messaggi_per_conversazione()
        assert dati["max_length"] == max_lunghezza_messaggio()


class TestFrequenzaInvio:
    """Il limite per conversazione non impedisce di martellare destinatari
    diversi, né di innescare una notifica (email inclusa) a ogni invio."""

    def test_invio_a_raffica_viene_frenato(self, csrf_client):
        from app.utils.password import hash_password
        from app.utils.rate_limit import reset_rate_limit

        reset_rate_limit()
        with Session(engine) as s:
            mittente = User(email=f"rl1-{secrets.token_hex(4)}@test.local",
                            password_md5=hash_password("password-di-prova"), confirmed=1)
            destinatario = User(email=f"rl2-{secrets.token_hex(4)}@test.local",
                                password_md5=hash_password("password-di-prova"), confirmed=1)
            s.add(mittente)
            s.add(destinatario)
            s.commit()
            s.refresh(mittente)
            s.refresh(destinatario)
            ids = (mittente.id, destinatario.id, mittente.email)

        try:
            reset_rate_limit()
            login = csrf_client.post("/api/login",
                                     data={"email": ids[2], "password": "password-di-prova"})
            assert login.status_code == 200, login.text

            esiti = []
            for i in range(40):
                r = csrf_client.post(f"/api/messaggi/{ids[1]}", data={"content": f"ciao {i}"})
                esiti.append(r.status_code)

            assert 429 in esiti, f"nessun 429 fra {sorted(set(esiti))}"
            assert esiti[0] in (200, 201), f"il primo invio doveva riuscire, ha dato {esiti[0]}"
        finally:
            csrf_client.get("/logout")
            reset_rate_limit()
            with Session(engine) as s:
                conv = s.exec(
                    select(Conversation).where(
                        Conversation.user1_id == min(ids[0], ids[1]),
                        Conversation.user2_id == max(ids[0], ids[1]),
                    )
                ).first()
                if conv:
                    for m in s.exec(select(Message).where(Message.conversation_id == conv.id)).all():
                        s.delete(m)
                    s.delete(conv)
                for uid in ids[:2]:
                    u = s.get(User, uid)
                    if u:
                        s.delete(u)
                s.commit()
