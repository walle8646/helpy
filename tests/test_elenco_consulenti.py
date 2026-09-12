"""Chi ha fatto accesso non deve trovare se stesso fra i consulenti.

Un consulente si vedeva nell'elenco e fra quelli in evidenza in homepage, ma
non puo' prenotare con se stesso: cliccando sulla propria scheda arrivava a un
vicolo cieco.
"""
import secrets

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import User
from app.utils.password import hash_password
from app.utils.rate_limit import reset_rate_limit


def _consulente(nome, venduto=3):
    return User(
        email=f"cons-{secrets.token_hex(4)}@test.local",
        password_md5=hash_password("prova-password"),
        confirmed=1, nome=nome, cognome="Verdi",
        is_verified=True, prezzo_consulenza=60,
        stripe_account_id="acct_x", stripe_onboarding_complete=True,
        consulenze_vendute=venduto,
    )


@pytest.fixture
def due_consulenti(csrf_client):
    reset_rate_limit()
    with Session(engine) as s:
        io_ = _consulente("Anna")
        altro = _consulente("Bruno")
        s.add(io_)
        s.add(altro)
        s.commit()
        s.refresh(io_)
        s.refresh(altro)
        dati = (io_.id, io_.email, altro.id)

    yield csrf_client, dati

    csrf_client.get("/logout")
    reset_rate_limit()
    with Session(engine) as s:
        for uid in (dati[0], dati[2]):
            u = s.get(User, uid)
            if u:
                s.delete(u)
        s.commit()


def _entra(client, email):
    client.get("/logout")
    reset_rate_limit()
    marker = 'name="csrf-token" content="'
    pagina = client.get("/login").text
    if marker in pagina:
        client.headers.update({"X-CSRF-Token": pagina.split(marker, 1)[1].split('"', 1)[0]})
    assert client.post("/api/login", data={"email": email, "password": "prova-password"}).status_code == 200


class TestElencoConsulenti:
    def test_non_mi_vedo_ma_vedo_gli_altri(self, due_consulenti):
        client, (mio_id, mia_email, altro_id) = due_consulenti
        _entra(client, mia_email)

        pagina = client.get("/consultants").text
        assert f'/user/{mio_id}"' not in pagina, "mi vedo tra i consulenti"
        assert f'/user/{altro_id}"' in pagina, "gli altri consulenti devono esserci"

    def test_non_mi_vedo_nemmeno_in_evidenza(self, due_consulenti):
        client, (mio_id, mia_email, altro_id) = due_consulenti
        _entra(client, mia_email)

        pagina = client.get("/").text
        assert f'/user/{mio_id}"' not in pagina
        assert f'/user/{altro_id}"' in pagina

    def test_da_sloggato_ci_sono_tutti(self, due_consulenti):
        client, (mio_id, mia_email, altro_id) = due_consulenti
        client.get("/logout")

        pagina = client.get("/consultants").text
        assert f'/user/{mio_id}"' in pagina
        assert f'/user/{altro_id}"' in pagina
