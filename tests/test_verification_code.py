"""Il codice di verifica email deve scadere davvero dopo 15 minuti.

L'email lo dichiarava valido 15 minuti, ma il codice non aveva una data di
generazione e restava valido per sempre.
"""
import secrets
from datetime import timedelta

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import User
from app.utils.orari import now_italy_naive
from app.utils.password import hash_password
from app.utils.rate_limit import reset_rate_limit

CODICE = "482913"


@pytest.fixture
def utente_da_verificare():
    reset_rate_limit()
    with Session(engine) as s:
        u = User(email=f"verif-{secrets.token_hex(4)}@test.local",
                 password_md5=hash_password("password-di-prova"), confirmed=0,
                 confirmation_code=CODICE)
        s.add(u)
        s.commit()
        s.refresh(u)
        uid, email = u.id, u.email
    yield uid, email
    reset_rate_limit()
    with Session(engine) as s:
        u = s.get(User, uid)
        if u:
            s.delete(u)
            s.commit()


def _imposta_eta_codice(uid, minuti):
    with Session(engine) as s:
        u = s.get(User, uid)
        u.confirmation_code_created_at = None if minuti is None else now_italy_naive() - timedelta(minutes=minuti)
        s.add(u)
        s.commit()


def _verifica(client, email, codice=CODICE):
    return client.post("/api/verify-email", data={"email": email, "code": codice})


class TestScadenza:
    def test_codice_recente_viene_accettato(self, csrf_client, utente_da_verificare):
        uid, email = utente_da_verificare
        _imposta_eta_codice(uid, 3)
        r = _verifica(csrf_client, email)
        assert r.status_code == 200, r.text
        with Session(engine) as s:
            u = s.get(User, uid)
            assert u.confirmed == 1
            assert u.confirmation_code is None
        csrf_client.get("/logout")

    def test_codice_di_20_minuti_fa_e_scaduto(self, csrf_client, utente_da_verificare):
        uid, email = utente_da_verificare
        _imposta_eta_codice(uid, 20)
        r = _verifica(csrf_client, email)
        assert r.status_code == 400
        assert r.json().get("expired") is True
        assert "scaduto" in r.json()["error"]
        with Session(engine) as s:
            assert s.get(User, uid).confirmed == 0

    def test_codice_senza_data_e_trattato_come_scaduto(self, csrf_client, utente_da_verificare):
        """Codici emessi prima di questa modifica: basta chiederne uno nuovo."""
        uid, email = utente_da_verificare
        _imposta_eta_codice(uid, None)
        r = _verifica(csrf_client, email)
        assert r.status_code == 400
        assert r.json().get("expired") is True

    def test_codice_sbagliato_resta_non_valido(self, csrf_client, utente_da_verificare):
        uid, email = utente_da_verificare
        _imposta_eta_codice(uid, 1)
        r = _verifica(csrf_client, email, codice="000000")
        assert r.status_code == 400
        assert r.json()["error"] == "Codice non valido"

    def test_il_reinvio_rinnova_la_scadenza(self, csrf_client, utente_da_verificare, monkeypatch):
        import app.routes.auth as auth
        monkeypatch.setattr(auth, "send_verification_email", lambda *a, **k: True)

        uid, email = utente_da_verificare
        _imposta_eta_codice(uid, 60)
        r = csrf_client.post("/api/resend-verification", data={"email": email})
        assert r.status_code == 200, r.text
        with Session(engine) as s:
            u = s.get(User, uid)
            # Codice nuovo, con una data di generazione di adesso
            assert u.confirmation_code_created_at is not None
            assert now_italy_naive() - u.confirmation_code_created_at < timedelta(minutes=1)

    def test_la_registrazione_data_il_codice(self, csrf_client, monkeypatch):
        import app.routes.auth as auth
        monkeypatch.setattr(auth, "send_verification_email", lambda *a, **k: True)
        reset_rate_limit()

        email = f"nuovo-{secrets.token_hex(4)}@test.local"
        r = csrf_client.post("/api/register", data={
            "email": email, "password": "password-lunga-1", "nome": "Nuovo",
        })
        try:
            assert r.status_code == 201, r.text
            with Session(engine) as s:
                u = s.exec(select(User).where(User.email == email)).one()
                assert u.confirmation_code_created_at is not None
        finally:
            reset_rate_limit()
            with Session(engine) as s:
                u = s.exec(select(User).where(User.email == email)).first()
                if u:
                    s.delete(u)
                    s.commit()


class TestRispostaRateLimit:
    def test_il_429_contiene_il_campo_letto_dalle_pagine(self, csrf_client):
        """Le pagine leggono data.error: prima il 429 aveva solo detail e l'utente
        bloccato vedeva un messaggio sbagliato."""
        reset_rate_limit()
        ultima = None
        for _ in range(15):
            ultima = csrf_client.post("/api/login", data={"email": "x@test.local", "password": "sbagliata"})
            if ultima.status_code == 429:
                break
        try:
            assert ultima.status_code == 429
            corpo = ultima.json()
            assert "Troppi tentativi" in corpo["error"]
            assert corpo["detail"] == corpo["error"]
            assert "retry-after" in {k.lower() for k in ultima.headers}
        finally:
            reset_rate_limit()
