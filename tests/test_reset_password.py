"""Reset della password: una richiesta sola, e il codice vale una volta.

Dal profilo "Cambia Password" porta qui. La pagina mostrava
"An error occurred. Please try again." pur avendo cambiato la password: ogni
invio partiva due volte (il template ha il suo script, e app/static/script.js
teneva una copia vecchia degli stessi gestori), e la seconda richiesta trovava
il codice già consumato.
"""
import re
import secrets
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import User
from app.routes import auth
from app.utils.password import hash_password, verify_password
from app.utils.rate_limit import reset_rate_limit

RADICE = Path(__file__).resolve().parent.parent


@pytest.fixture
def utente(monkeypatch):
    reset_rate_limit()
    monkeypatch.setattr(auth, "generate_verification_code", lambda: "542607")
    monkeypatch.setattr(auth, "send_reset_password_email", lambda *a, **k: True)
    email = f"reset-{secrets.token_hex(4)}@test.local"
    with Session(engine) as s:
        u = User(email=email, password_md5=hash_password("vecchia-password"), confirmed=1, nome="Mario")
        s.add(u)
        s.commit()
        s.refresh(u)
        uid = u.id
    yield email
    reset_rate_limit()
    with Session(engine) as s:
        u = s.get(User, uid)
        if u:
            s.delete(u)
            s.commit()


class TestFlusso:
    def test_codice_corretto_cambia_la_password(self, csrf_client, utente):
        assert csrf_client.post("/api/request-password-reset", data={"email": utente}).status_code == 200

        r = csrf_client.post("/api/reset-password", data={
            "email": utente, "code": "542607", "new_password": "NuovaPassword1"})
        assert r.status_code == 200, r.text

        with Session(engine) as s:
            u = s.exec(select(User).where(User.email == utente)).first()
        assert verify_password("NuovaPassword1", u.password_md5)

    def test_il_codice_vale_una_volta_sola(self, csrf_client, utente):
        csrf_client.post("/api/request-password-reset", data={"email": utente})
        csrf_client.post("/api/reset-password", data={
            "email": utente, "code": "542607", "new_password": "NuovaPassword1"})

        r = csrf_client.post("/api/reset-password", data={
            "email": utente, "code": "542607", "new_password": "AltraPassword2"})
        assert r.status_code == 400
        assert "Codice non trovato" in r.json()["error"]

        with Session(engine) as s:
            u = s.exec(select(User).where(User.email == utente)).first()
        assert verify_password("NuovaPassword1", u.password_md5), "il secondo invio non deve cambiare nulla"

    def test_codice_sbagliato(self, csrf_client, utente):
        csrf_client.post("/api/request-password-reset", data={"email": utente})
        r = csrf_client.post("/api/reset-password", data={
            "email": utente, "code": "000000", "new_password": "NuovaPassword1"})
        assert r.status_code == 400
        assert r.json()["error"] == "Codice non valido"


class TestNessunGestoreDuplicato:
    """Lo script globale non deve gestire form che le pagine gestiscono già:
    ogni invio partirebbe due volte."""

    def test_script_globale_senza_gestori_di_form(self):
        script = (RADICE / "app" / "static" / "script.js").read_text(encoding="utf-8-sig")
        assert "addEventListener('submit'" not in script
        assert "/api/reset-password" not in script
        assert "/api/login" not in script

    def test_ogni_form_ha_un_solo_gestore(self):
        for pagina, form in [("login.html", "loginForm"),
                             ("register.html", "registerForm"),
                             ("reset_password.html", "requestResetForm"),
                             ("reset_password.html", "resetPasswordForm")]:
            testo = (RADICE / "app" / "templates" / pagina).read_text(encoding="utf-8-sig")
            quanti = len(re.findall(rf"getElementById\('{form}'\)\.addEventListener", testo))
            assert quanti == 1, f"{pagina}: {quanti} gestori per {form}"
