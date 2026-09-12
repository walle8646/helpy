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


class TestRicercaPerCompetenze:
    """La ricerca guarda solo aree di interesse e tag del consulente.

    Prima cercava anche in nome, cognome, professione e descrizione: usciva
    chi *nomina* un argomento invece di chi lo sa trattare.
    """

    @pytest.fixture
    def consulenti_vari(self, csrf_client):
        reset_rate_limit()
        with Session(engine) as s:
            per_competenza = _consulente("Anna", venduto=0)
            per_competenza.aree_interesse = "Mutui, finanziamenti per la casa"
            per_tag = _consulente("Bruno", venduto=0)
            per_tag.tags = "ecommerce, vendere online"
            solo_nel_nome = _consulente("Ecommerce", venduto=0)
            solo_nel_nome.professione = "Esperto di ecommerce"
            solo_nel_nome.descrizione = "Parlo spesso di ecommerce ma non me ne occupo"
            for u in (per_competenza, per_tag, solo_nel_nome):
                s.add(u)
            s.commit()
            for u in (per_competenza, per_tag, solo_nel_nome):
                s.refresh(u)
            ids = (per_competenza.id, per_tag.id, solo_nel_nome.id)

        yield csrf_client, ids

        reset_rate_limit()
        with Session(engine) as s:
            for uid in ids:
                u = s.get(User, uid)
                if u:
                    s.delete(u)
            s.commit()

    def test_trova_per_area_di_interesse(self, consulenti_vari):
        client, (per_area, _, _) = consulenti_vari
        pagina = client.get("/consultants?search=finanziamenti").text
        assert f'/user/{per_area}"' in pagina

    def test_trova_per_tag(self, consulenti_vari):
        client, (_, per_tag, solo_nome) = consulenti_vari
        pagina = client.get("/consultants?search=ecommerce").text
        assert f'/user/{per_tag}"' in pagina
        assert f'/user/{solo_nome}"' not in pagina, "nome e descrizione non contano"

    def test_il_cognome_non_basta(self, consulenti_vari):
        client, (_, _, solo_nome) = consulenti_vari
        pagina = client.get("/consultants?search=Ecommerce").text
        assert f'/user/{solo_nome}"' not in pagina


class TestRicercaPerCategoria:
    """Chi cerca "come trovare lavoro a milano" si aspetta i consulenti di
    "Lavoro & Carriera", anche se nelle loro aree c'e' scritto "Leadership"."""

    @pytest.fixture
    def consulente_di_categoria(self, csrf_client):
        from app.models import Category

        reset_rate_limit()
        with Session(engine) as s:
            categoria = s.exec(select(Category).where(Category.name == "Lavoro & Carriera")).first()
            creata = categoria is None
            if creata:
                categoria = Category(name="Lavoro & Carriera", slug=f"lavoro-{secrets.token_hex(3)}",
                                     is_principal=True)
                s.add(categoria)
                s.commit()
                s.refresh(categoria)
            consulente = _consulente("Domenico", venduto=0)
            consulente.aree_interesse = "Leadership"
            consulente.category_id = categoria.id
            s.add(consulente)
            s.commit()
            s.refresh(consulente)
            ids = (consulente.id, categoria.id if creata else None)

        yield csrf_client, ids[0]

        reset_rate_limit()
        with Session(engine) as s:
            u = s.get(User, ids[0])
            if u:
                s.delete(u)
            if ids[1]:
                c = s.get(Category, ids[1])
                if c:
                    s.delete(c)
            s.commit()

    def test_la_frase_intera_lo_trova(self, consulente_di_categoria):
        client, consulente_id = consulente_di_categoria
        pagina = client.get("/consultants?search=come+trovare+lavoro+a+milano").text
        assert f'/user/{consulente_id}"' in pagina

    def test_anche_un_sinonimo_lo_trova(self, consulente_di_categoria):
        client, consulente_id = consulente_di_categoria
        pagina = client.get("/consultants?search=colloquio").text
        assert f'/user/{consulente_id}"' in pagina

    def test_un_argomento_estraneo_non_lo_trova(self, consulente_di_categoria):
        client, consulente_id = consulente_di_categoria
        pagina = client.get("/consultants?search=fotografia+matrimoni").text
        assert f'/user/{consulente_id}"' not in pagina
