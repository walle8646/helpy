"""Test della selezione delle domande per i contenuti social.

Le domande già trasformate in bozze vanno escluse **prima** di chiamare GPT:
il filtro era a valle, quindi ogni "Genera contenuti" pagava N chiamate al
modello per poi scartarle tutte, visto che la classifica per engagement è
stabile e restituiva sempre le stesse domande.
"""
import secrets
from datetime import datetime, timedelta

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import CommunityQuestion, SocialDraft, User
from app.social.content_generator import fetch_top_questions


@pytest.fixture
def autore():
    with Session(engine) as s:
        u = User(email=f"soc-{secrets.token_hex(4)}@test.local", password_md5="x")
        s.add(u)
        s.commit()
        s.refresh(u)
        uid = u.id
    yield uid
    with Session(engine) as s:
        for d in s.exec(select(SocialDraft)).all():
            s.delete(d)
        for q in s.exec(select(CommunityQuestion).where(CommunityQuestion.user_id == uid)).all():
            s.delete(q)
        u = s.get(User, uid)
        if u:
            s.delete(u)
        s.commit()


def _domanda(user_id, titolo, upvotes=0, views=0, validata=True):
    with Session(engine) as s:
        q = CommunityQuestion(
            user_id=user_id,
            title=titolo,
            description="descrizione della domanda di prova",
            upvotes=upvotes,
            views=views,
            validation=validata,
            created_at=datetime(2026, 1, 1) + timedelta(minutes=upvotes),
        )
        s.add(q)
        s.commit()
        s.refresh(q)
        return q.id


def _bozza(question_id, piattaforma="instagram"):
    with Session(engine) as s:
        s.add(SocialDraft(
            platform=piattaforma,
            caption="caption di prova",
            source_question_id=question_id,
        ))
        s.commit()


class TestSelezioneDomande:
    def test_pesca_solo_le_domande_validate(self, autore):
        _domanda(autore, "Domanda visibile", upvotes=10)
        _domanda(autore, "Domanda non validata", upvotes=99, validata=False)

        titoli = [q["title"] for q in fetch_top_questions(10)]
        assert "Domanda visibile" in titoli
        assert "Domanda non validata" not in titoli

    def test_ordina_per_engagement(self, autore):
        _domanda(autore, "Poco seguita", upvotes=1, views=0)
        _domanda(autore, "Molto seguita", upvotes=20, views=5)

        titoli = [q["title"] for q in fetch_top_questions(10)]
        assert titoli.index("Molto seguita") < titoli.index("Poco seguita")

    def test_le_domande_gia_lavorate_sono_escluse(self, autore):
        """È il punto del fix: senza esclusione a monte, GPT veniva chiamato
        di nuovo su queste e il risultato buttato via."""
        qid_fatta = _domanda(autore, "Già trasformata in bozze", upvotes=50)
        _domanda(autore, "Ancora da lavorare", upvotes=10)
        _bozza(qid_fatta)

        titoli = [q["title"] for q in fetch_top_questions(10)]
        assert "Già trasformata in bozze" not in titoli
        assert "Ancora da lavorare" in titoli

    def test_basta_una_bozza_su_una_piattaforma_per_escludere(self, autore):
        qid = _domanda(autore, "Solo TikTok fatto", upvotes=30)
        _bozza(qid, piattaforma="tiktok")

        assert "Solo TikTok fatto" not in [q["title"] for q in fetch_top_questions(10)]

    def test_esaurite_le_domande_non_torna_nulla(self, autore):
        qid = _domanda(autore, "L'unica", upvotes=5)
        _bozza(qid)

        # Nessuna domanda nuova: generate_batch non deve chiamare GPT
        assert fetch_top_questions(10) == []

    def test_rispetta_il_limite(self, autore):
        for i in range(5):
            _domanda(autore, f"Domanda {i}", upvotes=i)

        assert len(fetch_top_questions(2)) == 2


class TestGenerateBatchSenzaDomande:
    def test_non_chiama_il_modello_se_non_c_e_nulla(self, autore, monkeypatch):
        from app.social import content_generator

        chiamate = []

        def _non_chiamare(q):
            chiamate.append(q)
            raise AssertionError("GPT non doveva essere chiamato")

        monkeypatch.setattr(content_generator, "generate_for_question", _non_chiamare)

        qid = _domanda(autore, "Unica domanda", upvotes=1)
        _bozza(qid)

        assert content_generator.generate_batch(5) == []
        assert chiamate == []


class TestErroriDiGenerazione:
    """Se la generazione fallisce, chi ha premuto il pulsante deve saperlo.

    Gli errori finivano solo nei log e la pagina rispondeva "nessuna domanda
    nuova da lavorare": il contrario di quello che era successo.
    """

    def test_gli_errori_tornano_al_chiamante(self, autore, monkeypatch):
        from app.social import content_generator as generatore

        _domanda(autore, "Come trovare lavoro a Milano", upvotes=10, views=50)

        def esplode(q):
            raise ValueError("OPENAI_API_KEY non configurata.")

        monkeypatch.setattr(generatore, "generate_for_question", esplode)
        bozze, errori = generatore.genera_bozze(3)
        assert bozze == []
        assert len(errori) == 1 and "OPENAI_API_KEY" in errori[0]

    def test_senza_domande_nessun_errore(self, autore, monkeypatch):
        from app.social import content_generator as generatore

        bozze, errori = generatore.genera_bozze(3)
        assert (bozze, errori) == ([], [])

    def test_una_risposta_non_valida_e_un_errore(self, autore, monkeypatch):
        """Prima produceva una bozza vuota e sembrava tutto a posto."""
        import types

        from app.social import content_generator as generatore

        risposta = types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content="non sono json"))]
        )
        finto = types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=lambda **kw: risposta))
        )
        monkeypatch.setattr(generatore, "_get_client", lambda: finto)
        with pytest.raises(generatore.GenerazioneFallita):
            generatore.generate_for_question({"id": 1, "title": "t", "description": "d", "category": "c"})


class TestPulsanteGeneraContenuti:
    @pytest.fixture
    def admin(self, csrf_client):
        import secrets as _s

        from app.utils.password import hash_password
        from app.utils.rate_limit import reset_rate_limit

        reset_rate_limit()
        password = _s.token_urlsafe(12)
        with Session(engine) as s:
            u = User(email=f"adm-{_s.token_hex(4)}@test.local",
                     password_md5=hash_password(password), confirmed=1, user_type_id=3)
            s.add(u)
            s.commit()
            s.refresh(u)
            uid, email = u.id, u.email
        assert csrf_client.post("/api/login", data={"email": email, "password": password}).status_code == 200
        yield csrf_client
        csrf_client.get("/logout")
        reset_rate_limit()
        with Session(engine) as s:
            u = s.get(User, uid)
            if u:
                s.delete(u)
                s.commit()

    def test_dice_perche_non_ha_generato(self, admin, autore, monkeypatch):
        from app.social import content_generator as generatore

        _domanda(autore, "Domanda popolare", upvotes=5, views=20)
        monkeypatch.setattr(generatore, "genera_bozze",
                            lambda limit: ([], [f"domanda #1: OPENAI_API_KEY non configurata."]))

        r = admin.post("/admin/social/generate", json={"limit": 3})
        assert r.status_code == 502
        corpo = r.json()
        assert corpo["ok"] is False
        assert "OPENAI_API_KEY" in corpo["message"]

    def test_senza_domande_lo_dice_senza_allarmare(self, admin, monkeypatch):
        from app.social import content_generator as generatore

        monkeypatch.setattr(generatore, "genera_bozze", lambda limit: ([], []))
        r = admin.post("/admin/social/generate", json={"limit": 3})
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert "Nessuna domanda nuova" in r.json()["message"]
