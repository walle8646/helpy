"""La notifica di un nuovo messaggio deve portare alla conversazione.

Puntava a /messages, che non esiste: sia il click nella campanella sia il
bottone "Apri Chat" dell'email finivano su un 404. Nello stesso passaggio le
notifiche sono state unificate su notification_service (c'erano due moduli
paralleli con firme diverse).
"""
import re
import secrets
from pathlib import Path

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import Conversation, Message, Notification, NotificationType, User
from app.utils.password import hash_password
from app.utils.rate_limit import reset_rate_limit


@pytest.fixture
def due_utenti_e_tipo_notifica():
    reset_rate_limit()
    password = secrets.token_urlsafe(12)
    with Session(engine) as s:
        tipo = s.exec(select(NotificationType).where(NotificationType.type_key == "community_contact")).first()
        creato_tipo = tipo is None
        if creato_tipo:
            s.add(NotificationType(type_key="community_contact", name="Nuovo messaggio",
                                   in_app=True, send_email=False, is_active=True))
        mittente = User(email=f"mit-{secrets.token_hex(4)}@test.local",
                        password_md5=hash_password(password), confirmed=1, nome="Mario")
        destinatario = User(email=f"dest-{secrets.token_hex(4)}@test.local",
                            password_md5="x", confirmed=1, nome="Anna")
        s.add(mittente)
        s.add(destinatario)
        s.commit()
        s.refresh(mittente)
        s.refresh(destinatario)
        ids = (mittente.id, destinatario.id, mittente.email, password)

    yield ids

    reset_rate_limit()
    with Session(engine) as s:
        for n in s.exec(select(Notification).where(Notification.user_id == ids[1])).all():
            s.delete(n)
        conv = s.exec(select(Conversation).where(
            Conversation.user1_id == min(ids[0], ids[1]),
            Conversation.user2_id == max(ids[0], ids[1]),
        )).first()
        if conv:
            for m in s.exec(select(Message).where(Message.conversation_id == conv.id)).all():
                s.delete(m)
            s.delete(conv)
        for uid in ids[:2]:
            u = s.get(User, uid)
            if u:
                s.delete(u)
        if creato_tipo:
            t = s.exec(select(NotificationType).where(NotificationType.type_key == "community_contact")).first()
            if t:
                s.delete(t)
        s.commit()


class TestNotificaMessaggio:
    def test_la_notifica_apre_la_conversazione(self, csrf_client, due_utenti_e_tipo_notifica):
        mittente_id, destinatario_id, email, password = due_utenti_e_tipo_notifica
        assert csrf_client.post("/api/login", data={"email": email, "password": password}).status_code == 200
        try:
            r = csrf_client.post(f"/api/messaggi/{destinatario_id}", data={"content": "Ciao!"})
            assert r.status_code == 201, r.text

            with Session(engine) as s:
                notifica = s.exec(select(Notification).where(Notification.user_id == destinatario_id)).one()
            assert notifica.type == "community_contact"
            assert notifica.action_url == f"/messaggi/{mittente_id}"
            assert notifica.related_user_id == mittente_id
            assert "Mario" in notifica.message

            # e il link esiste davvero
            assert csrf_client.get(notifica.action_url, follow_redirects=False).status_code != 404
        finally:
            csrf_client.get("/logout")


class TestNessunLinkAPagineInesistenti:
    def test_nessun_link_a_slash_messages(self):
        """La pagina messaggi è /messaggi: /messages risponde 404."""
        radice = Path(__file__).resolve().parent.parent / "app"
        schema = re.compile(r"""["'`(]/messages(?:["'`/?#)]|$)""")
        trovati = []
        for f in list(radice.rglob("*.html")) + list(radice.rglob("*.py")):
            for n, riga in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), 1):
                if schema.search(riga):
                    trovati.append(f"{f.relative_to(radice.parent)}:{n}")
        assert not trovati, "link a /messages (404): " + ", ".join(trovati)

    def test_slash_messages_non_esiste_davvero(self, client):
        assert client.get("/messages", follow_redirects=False).status_code == 404
