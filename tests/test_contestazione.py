"""Dopo una contestazione la call non si riapre, e il consulente lo sa.

Il cliente poteva aprire una contestazione e poi rientrare in call: la
registrazione della consulenza è la prova principale, e riaprire il canale
permetteva di aggiungerci materiale dopo. Il consulente, dal canto suo, non
veniva avvisato: vedeva solo il compenso non arrivare.
"""
import secrets
from datetime import datetime

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import Booking, Dispute, Notification, Review, User
from app.utils.orari import now_italy_naive
from app.utils.password import hash_password
from app.utils.rate_limit import reset_rate_limit


@pytest.fixture
def consulenza_svolta(csrf_client):
    """Cliente loggato, consulenza di oggi già svolta (call ancora nella finestra)."""
    reset_rate_limit()
    password = secrets.token_urlsafe(12)
    adesso = now_italy_naive()
    with Session(engine) as s:
        cliente = User(email=f"cont-c-{secrets.token_hex(4)}@test.local",
                       password_md5=hash_password(password), confirmed=1, nome="Giulia", cognome="Bianchi")
        consulente = User(email=f"cont-p-{secrets.token_hex(4)}@test.local",
                          password_md5="x", confirmed=1, nome="Paolo", cognome="Neri")
        s.add(cliente)
        s.add(consulente)
        s.commit()
        s.refresh(cliente)
        s.refresh(consulente)
        b = Booking(client_user_id=cliente.id, consultant_user_id=consulente.id,
                    booking_date=datetime(adesso.year, adesso.month, adesso.day),
                    start_time="00:00", end_time="23:59", duration_minutes=60,
                    status="confirmed", payment_status="held",
                    client_joined_at=adesso, consultant_joined_at=adesso,
                    recording_requested=True, call_started_at=adesso)
        s.add(b)
        s.commit()
        s.refresh(b)
        ids = {"booking": b.id, "cliente": cliente.id, "consulente": consulente.id}

    assert csrf_client.post("/api/login", data={"email": cliente.email, "password": password}).status_code == 200
    yield csrf_client, ids

    csrf_client.get("/logout")
    reset_rate_limit()
    with Session(engine) as s:
        for d in s.exec(select(Dispute).where(Dispute.booking_id == ids["booking"])).all():
            s.delete(d)
        for r in s.exec(select(Review).where(Review.booking_id == ids["booking"])).all():
            s.delete(r)
        for n in s.exec(select(Notification).where(
                Notification.user_id.in_([ids["cliente"], ids["consulente"]]))).all():
            s.delete(n)
        s.commit()
        b = s.get(Booking, ids["booking"])
        if b:
            s.delete(b)
        s.commit()
        for uid in (ids["cliente"], ids["consulente"]):
            u = s.get(User, uid)
            if u:
                s.delete(u)
        s.commit()


def _apri_contestazione(client, booking_id, testo="Il consulente non ha risposto alle mie domande"):
    return client.post(f"/api/booking/{booking_id}/dispute", json={"description": testo})


class TestCallChiusaDallaContestazione:
    def test_prima_della_contestazione_si_entra(self, consulenza_svolta):
        client, ids = consulenza_svolta
        stato = client.get(f"/api/booking/{ids['booking']}/call-status-extended").json()
        assert stato["closed_by_dispute"] is False
        assert stato["is_expired"] is False

    def test_dopo_la_contestazione_la_call_e_chiusa(self, consulenza_svolta):
        client, ids = consulenza_svolta
        assert _apri_contestazione(client, ids["booking"]).status_code == 200

        stato = client.get(f"/api/booking/{ids['booking']}/call-status-extended").json()
        assert stato["closed_by_dispute"] is True
        assert stato["can_resume"] is False

        stato_base = client.get(f"/api/booking/{ids['booking']}/call-status").json()
        assert stato_base["closed_by_dispute"] is True and stato_base["is_active"] is False

        pagina = client.get(f"/booking/call/{ids['booking']}", follow_redirects=False)
        assert pagina.status_code == 303
        assert pagina.headers["location"] == "/profile?call_closed=dispute"

        token = client.get(f"/api/booking/{ids['booking']}/agora-token")
        assert token.status_code == 403
        assert "contestazione" in token.json()["detail"]

        join = client.post(f"/api/booking/{ids['booking']}/join")
        assert join.status_code == 403

    def test_il_profilo_non_propone_piu_la_call(self, consulenza_svolta):
        client, ids = consulenza_svolta
        _apri_contestazione(client, ids["booking"])
        prossimi = client.get("/api/booking/upcoming").json()["bookings"]
        card = next((b for b in prossimi if b["id"] == ids["booking"]), None)
        if card is not None:
            assert card["closed_by_dispute"] is True


class TestAvvisoAlConsulente:
    def test_il_consulente_riceve_la_notifica(self, consulenza_svolta):
        client, ids = consulenza_svolta
        _apri_contestazione(client, ids["booking"], "Non ha risposto alle mie domande")

        with Session(engine) as s:
            avvisi = s.exec(select(Notification).where(
                Notification.user_id == ids["consulente"],
                Notification.type == "dispute_opened",
            )).all()
        assert len(avvisi) == 1
        assert "contestazione" in avvisi[0].message
        assert avvisi[0].related_booking_id == ids["booking"]

    def test_al_cliente_non_arriva_niente(self, consulenza_svolta):
        client, ids = consulenza_svolta
        _apri_contestazione(client, ids["booking"])
        with Session(engine) as s:
            assert s.exec(select(Notification).where(
                Notification.user_id == ids["cliente"],
                Notification.type == "dispute_opened",
            )).all() == []

    def test_l_email_si_genera(self):
        from app.utils.notification_email import generate_email_html

        html = generate_email_html("dispute_opened.html", {
            "consultant_name": "Paolo", "client_name": "Giulia",
            "date": "12/09/2026", "time": "10:00",
            "reason_section": "<div>motivo</div>",
            "action_url": "https://ispiramy.com/profile",
        })
        assert html and "contestazione" in html.lower()
        import re
        assert not re.findall(r"\{[a-z_]+\}", html)
