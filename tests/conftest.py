"""Configurazione comune dei test.

Il DATABASE_URL viene puntato su uno SQLite temporaneo PRIMA di importare
qualsiasi modulo dell'app: `app.database` legge la variabile a import-time, e
senza questo i test scriverebbero sul database di sviluppo.
"""
import os
import tempfile
from pathlib import Path

_TMP_DB = Path(tempfile.gettempdir()) / "ispiramy_pytest.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TMP_DB.as_posix()}")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
# STAGING_PASSWORD attiverebbe la Basic Auth su ogni richiesta
os.environ.pop("STAGING_PASSWORD", None)

import pytest  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """TestClient con gli hook di startup/shutdown eseguiti (crea le tabelle)."""
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture
def csrf_client(client):
    """Client con token CSRF gia' negoziato, pronto per le richieste POST."""
    resp = client.get("/login")
    token = ""
    marker = 'name="csrf-token" content="'
    if marker in resp.text:
        token = resp.text.split(marker, 1)[1].split('"', 1)[0]
    client.headers.update({"X-CSRF-Token": token})
    return client
