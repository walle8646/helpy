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


class TestCacheDeiFileStatici:
    """Dopo un rilascio il browser deve prendere i file nuovi.

    StaticFiles non manda un max-age: con l'URL sempre uguale i browser
    tenevano il JavaScript vecchio per giorni, e la correzione al reset
    password sembrava non essere mai arrivata.
    """

    def test_i_file_statici_hanno_la_versione_nell_url(self, client):
        pagina = client.get("/login").text
        assert "/static/script.js?v=" in pagina
        assert "/static/style.css?v=" in pagina

    def test_la_versione_cambia_con_il_file(self, tmp_path, monkeypatch):
        from app.main import statico

        primo = statico("script.js")
        (RADICE / "app" / "static" / "script.js").touch()
        assert statico("script.js") != primo

    def test_file_inesistente_non_rompe_la_pagina(self):
        from app.main import statico

        assert statico("non-esiste.css") == "/static/non-esiste.css"


class TestLarghezzaColonnaPassword:
    """L'hash bcrypt non entrava nella colonna, pensata per MD5.

    Su PostgreSQL password_md5 era VARCHAR(32) (32 = lunghezza di un MD5):
    salvare un hash bcrypt, che di caratteri ne ha 60, faceva fallire la query
    e l'utente vedeva "Il server ha risposto con un errore (500)". SQLite non
    applica la lunghezza dichiarata, quindi in sviluppo e nei test tutto
    sembrava funzionare.
    """

    def test_l_hash_bcrypt_e_piu_lungo_di_un_md5(self):
        assert len(hash_password("password-di-prova")) > 32

    def test_la_colonna_e_prevista_abbastanza_larga(self):
        from app.database import COLONNE_DA_ALLARGARE

        misure = {(t, c): minimo for t, c, minimo in COLONNE_DA_ALLARGARE}
        assert misure[("user", "password_md5")] >= len(hash_password("x")) * 2

    def test_su_sqlite_non_tocca_niente(self):
        from app.database import ensure_column_widths

        assert ensure_column_widths() == []
