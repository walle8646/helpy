"""Test dell'URL di ritorno comunicato a Google.

Google confronta il redirect_uri carattere per carattere con quelli registrati
nella console: basta uno schema diverso per ottenere `400 redirect_uri_mismatch`.
Dietro il proxy di Render l'app vede la richiesta in HTTP, e ricavando l'URL
dalla richiesta mandava a Google `http://…` — che su un dominio pubblico non
si può nemmeno registrare.
"""
from types import SimpleNamespace

import pytest

from app.routes.google_auth import callback_url


class _Req:
    """Request minima: callback_url usa solo headers e url_for."""

    def __init__(self, url_richiesta: str, headers: dict | None = None):
        self._url = url_richiesta
        self.headers = headers or {}

    def url_for(self, nome: str):
        assert nome == "google_callback"
        return self._url


class TestConBaseUrl:
    def test_usa_base_url_anche_se_la_richiesta_arriva_in_http(self, monkeypatch):
        monkeypatch.setenv("BASE_URL", "https://ispiramy.com")
        req = _Req("http://ispiramy.com/auth/google/callback", {"x-forwarded-proto": "https"})
        assert callback_url(req) == "https://ispiramy.com/auth/google/callback"

    def test_ignora_lo_slash_finale(self, monkeypatch):
        monkeypatch.setenv("BASE_URL", "https://ispiramy.com/")
        assert callback_url(_Req("http://x/auth/google/callback")) == \
            "https://ispiramy.com/auth/google/callback"

    def test_ignora_host_interni_del_proxy(self, monkeypatch):
        # L'host visto dall'app non deve mai finire nell'URL mandato a Google
        monkeypatch.setenv("BASE_URL", "https://ispiramy.com")
        req = _Req("http://10.0.3.7:10000/auth/google/callback")
        assert callback_url(req) == "https://ispiramy.com/auth/google/callback"


class TestSenzaBaseUrl:
    @pytest.fixture(autouse=True)
    def _senza_base_url(self, monkeypatch):
        monkeypatch.delenv("BASE_URL", raising=False)

    def test_locale_resta_http(self):
        req = _Req("http://localhost:10000/auth/google/callback")
        assert callback_url(req) == "http://localhost:10000/auth/google/callback"

    def test_dietro_proxy_https_corregge_lo_schema(self):
        req = _Req("http://ispiramy.onrender.com/auth/google/callback",
                   {"x-forwarded-proto": "https"})
        assert callback_url(req) == "https://ispiramy.onrender.com/auth/google/callback"

    def test_proxy_che_dichiara_http_non_viene_toccato(self):
        req = _Req("http://ispiramy.local/auth/google/callback", {"x-forwarded-proto": "http"})
        assert callback_url(req) == "http://ispiramy.local/auth/google/callback"


class TestEndpoint:
    def test_senza_client_id_torna_al_login(self, client):
        # In test GOOGLE_CLIENT_ID non è configurato: niente redirect a Google
        r = client.get("/auth/google", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"].endswith("/login")
