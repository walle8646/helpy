"""Test del rate limiting sugli endpoint di autenticazione.

Prima non c'era alcun limite: login, codice di verifica a 6 cifre e reset
password erano attaccabili a forza bruta senza ostacoli.
"""
import pytest
from fastapi import HTTPException

from app.utils.rate_limit import (
    check_rate_limit,
    clear_attempts,
    enforce_rate_limit,
    client_ip,
    reset_rate_limit,
)


class _FakeRequest:
    """Request minima: al rate limiter servono solo headers e client."""

    def __init__(self, ip="1.2.3.4", forwarded=None):
        self.headers = {"x-forwarded-for": forwarded} if forwarded else {}
        self.client = type("C", (), {"host": ip})()


@pytest.fixture(autouse=True)
def contatori_puliti():
    reset_rate_limit()
    yield
    reset_rate_limit()


class TestIpDelChiamante:
    def test_usa_x_forwarded_for(self):
        # Dietro il proxy di Render request.client.host è sempre lo stesso:
        # senza questo, il limite bloccherebbe tutti gli utenti insieme.
        req = _FakeRequest(ip="10.0.0.1", forwarded="93.40.1.7, 10.0.0.1")
        assert client_ip(req) == "93.40.1.7"

    def test_ripiega_su_client_host(self):
        assert client_ip(_FakeRequest(ip="93.40.1.7")) == "93.40.1.7"


class TestFinestra:
    def test_consente_fino_al_limite(self):
        req = _FakeRequest()
        for i in range(3):
            consentito, _ = check_rate_limit(req, "prova", limit=3, window_seconds=60)
            assert consentito, f"tentativo {i + 1} bloccato troppo presto"

    def test_blocca_oltre_il_limite(self):
        req = _FakeRequest()
        for _ in range(3):
            check_rate_limit(req, "prova", limit=3, window_seconds=60)
        consentito, attesa = check_rate_limit(req, "prova", limit=3, window_seconds=60)
        assert consentito is False
        assert attesa > 0

    def test_ip_diversi_hanno_contatori_separati(self):
        a, b = _FakeRequest(ip="1.1.1.1"), _FakeRequest(ip="2.2.2.2")
        for _ in range(3):
            check_rate_limit(a, "prova", limit=3, window_seconds=60)
        assert check_rate_limit(a, "prova", limit=3, window_seconds=60)[0] is False
        assert check_rate_limit(b, "prova", limit=3, window_seconds=60)[0] is True

    def test_email_diverse_hanno_contatori_separati(self):
        req = _FakeRequest()
        for _ in range(3):
            check_rate_limit(req, "login", limit=3, window_seconds=60, extra_key="a@x.it")
        assert check_rate_limit(req, "login", 3, 60, "a@x.it")[0] is False
        assert check_rate_limit(req, "login", 3, 60, "b@x.it")[0] is True

    def test_scope_diversi_non_si_influenzano(self):
        req = _FakeRequest()
        for _ in range(3):
            check_rate_limit(req, "login", limit=3, window_seconds=60)
        assert check_rate_limit(req, "login", 3, 60)[0] is False
        assert check_rate_limit(req, "register", 3, 60)[0] is True


class TestEnforce:
    def test_solleva_429_con_retry_after(self):
        req = _FakeRequest()
        for _ in range(2):
            enforce_rate_limit(req, "prova", limit=2, window_seconds=60)
        with pytest.raises(HTTPException) as exc:
            enforce_rate_limit(req, "prova", limit=2, window_seconds=60)
        assert exc.value.status_code == 429
        assert "Retry-After" in exc.value.headers


class TestAzzeramento:
    def test_dopo_il_successo_i_tentativi_ripartono(self):
        req = _FakeRequest()
        for _ in range(3):
            check_rate_limit(req, "login", limit=3, window_seconds=60, extra_key="a@x.it")
        assert check_rate_limit(req, "login", 3, 60, "a@x.it")[0] is False

        clear_attempts(req, "login", "a@x.it")
        assert check_rate_limit(req, "login", 3, 60, "a@x.it")[0] is True


class TestSugliEndpoint:
    def test_login_viene_bloccato_dopo_troppi_tentativi(self, csrf_client):
        esiti = []
        for _ in range(15):
            r = csrf_client.post(
                "/api/login",
                data={"email": "nessuno@test.local", "password": "sbagliata"},
            )
            esiti.append(r.status_code)
        assert 429 in esiti, f"nessun 429 fra {sorted(set(esiti))}"
        # I primi tentativi devono comunque passare la validazione normale
        assert esiti[0] == 401
