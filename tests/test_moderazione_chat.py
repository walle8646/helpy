"""Le immagini in chat passano dallo stesso controllo della community.

Gli allegati della call venivano filtrati solo dall'endpoint "moderations" di
OpenAI (sessuale, violento, odio), mentre la community usa GPT-4o vision, che
blocca anche politica e pubblicita'. Ora il controllo e' lo stesso.
La chat fra utenti, fuori dalla call, non aveva alcuna moderazione.
"""
import asyncio
import secrets

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import Conversation, Message, Notification, NotificationType, User
from app.utils import ai_service
from app.utils.password import hash_password
from app.utils.rate_limit import reset_rate_limit


class TestControlloUnico:
    def test_senza_chiave_openai_non_blocca(self, monkeypatch):
        """Una configurazione mancante non deve impedire di allegare file."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        esito = asyncio.run(ai_service.modera_immagine_vision("data:image/png;base64,xxx"))
        assert esito["approved"] is True

    def test_la_chat_usa_il_controllo_della_community(self, monkeypatch):
        chiamate = []
        monkeypatch.setattr(ai_service, "_moderazione_rapida_immagine",
                            lambda url: _risposta(chiamate, "rapida", True))
        monkeypatch.setattr(ai_service, "modera_immagine_vision",
                            lambda url, contesto=None, etichetta="": _risposta(chiamate, "vision", True))

        esito = asyncio.run(ai_service.modera_immagine_chat("data:image/png;base64,xxx"))
        assert esito["approved"] is True
        assert chiamate == ["rapida", "vision"], "servono entrambi i passaggi"

    def test_se_il_filtro_rapido_blocca_non_si_prosegue(self, monkeypatch):
        chiamate = []
        monkeypatch.setattr(ai_service, "_moderazione_rapida_immagine",
                            lambda url: _risposta(chiamate, "rapida", False, "contenuto sessuale"))
        monkeypatch.setattr(ai_service, "modera_immagine_vision",
                            lambda url, contesto=None, etichetta="": _risposta(chiamate, "vision", True))

        esito = asyncio.run(ai_service.modera_immagine_chat("data:image/png;base64,xxx"))
        assert esito["approved"] is False
        assert esito["reason"] == "contenuto sessuale"
        assert chiamate == ["rapida"]

    def test_la_community_passa_il_suo_argomento(self, monkeypatch):
        visti = {}

        async def finto(url, contesto=None, etichetta=""):
            visti.update(url=url, contesto=contesto)
            return {"approved": True, "reason": ""}

        monkeypatch.setattr(ai_service, "modera_immagine_vision", finto)
        asyncio.run(ai_service.modera_immagine("Ym9v", "Contratto d'affitto", "Devo capire una clausola"))
        assert visti["url"].startswith("data:image/jpeg;base64,")
        assert "Contratto d'affitto" in visti["contesto"]


async def _risposta(registro, nome, approvata, motivo=""):
    registro.append(nome)
    return {"approved": approvata, "reason": motivo}


@pytest.fixture
def due_utenti(csrf_client):
    reset_rate_limit()
    password = secrets.token_urlsafe(12)
    with Session(engine) as s:
        tipo = s.exec(select(NotificationType).where(NotificationType.type_key == "community_contact")).first()
        mittente = User(email=f"mod-a-{secrets.token_hex(4)}@test.local",
                        password_md5=hash_password(password), confirmed=1, nome="Mario")
        destinatario = User(email=f"mod-b-{secrets.token_hex(4)}@test.local",
                            password_md5="x", confirmed=1, nome="Anna")
        s.add(mittente)
        s.add(destinatario)
        s.commit()
        s.refresh(mittente)
        s.refresh(destinatario)
        ids = (mittente.id, destinatario.id, mittente.email, password)

    assert csrf_client.post("/api/login", data={"email": ids[2], "password": password}).status_code == 200
    yield csrf_client, ids

    csrf_client.get("/logout")
    reset_rate_limit()
    with Session(engine) as s:
        conv = s.exec(select(Conversation).where(
            Conversation.user1_id == min(ids[0], ids[1]),
            Conversation.user2_id == max(ids[0], ids[1]),
        )).first()
        if conv:
            for m in s.exec(select(Message).where(Message.conversation_id == conv.id)).all():
                s.delete(m)
            s.delete(conv)
        for n in s.exec(select(Notification).where(Notification.user_id.in_(ids[:2]))).all():
            s.delete(n)
        s.commit()
        for uid in ids[:2]:
            u = s.get(User, uid)
            if u:
                s.delete(u)
        s.commit()


class TestChatFuoriDallaCall:
    """Prima qui non c'era nessun controllo sui contenuti."""

    def test_messaggio_offensivo_rifiutato(self, due_utenti, monkeypatch):
        client, ids = due_utenti

        async def blocca(testo):
            return {"approved": False, "reason": "Il messaggio contiene contenuti offensivi."}

        monkeypatch.setattr("app.routes.messages.modera_testo_chat", blocca)
        r = client.post(f"/api/messaggi/{ids[1]}", data={"content": "qualcosa di brutto"})
        assert r.status_code == 400
        assert "offensivi" in r.json()["error"]

        with Session(engine) as s:
            assert s.exec(select(Message)).all() == [] or all(
                m.content != "qualcosa di brutto" for m in s.exec(select(Message)).all()
            )

    def test_messaggio_normale_passa(self, due_utenti, monkeypatch):
        client, ids = due_utenti

        async def consenti(testo):
            return {"approved": True, "reason": ""}

        monkeypatch.setattr("app.routes.messages.modera_testo_chat", consenti)
        r = client.post(f"/api/messaggi/{ids[1]}", data={"content": "Ciao, avrei bisogno di una mano"})
        assert r.status_code == 201, r.text
