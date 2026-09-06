"""Regressione sulla falla del token recensione.

Il token del link email non veniva salvato da nessuna parte e il booking
arrivava dalla query string: chiunque, senza autenticazione, poteva creare una
recensione a nome del cliente per qualsiasi consulenza.
"""
import secrets
from datetime import datetime

import pytest
from sqlmodel import Session, select

from app.database import engine
from app.models import Booking, Review, User


@pytest.fixture
def consulenza():
    """Crea cliente, consulente e una consulenza conclusa. Ripulisce alla fine."""
    with Session(engine) as s:
        cliente = User(email=f"cli-{secrets.token_hex(4)}@test.local", password_md5="x", nome="Cli")
        consulente = User(email=f"con-{secrets.token_hex(4)}@test.local", password_md5="x", nome="Con")
        s.add(cliente)
        s.add(consulente)
        s.commit()
        s.refresh(cliente)
        s.refresh(consulente)

        b = Booking(
            client_user_id=cliente.id,
            consultant_user_id=consulente.id,
            booking_date=datetime(2026, 1, 10),
            start_time="10:00",
            end_time="11:00",
            duration_minutes=60,
            status="completed",
        )
        s.add(b)
        s.commit()
        s.refresh(b)
        ids = (b.id, cliente.id, consulente.id)

    yield ids

    with Session(engine) as s:
        for r in s.exec(select(Review).where(Review.booking_id == ids[0])).all():
            s.delete(r)
        b = s.get(Booking, ids[0])
        if b:
            s.delete(b)
        for uid in ids[1:]:
            u = s.get(User, uid)
            if u:
                s.delete(u)
        s.commit()


def _payload():
    return {"rating_helpful": 1, "rating_prepared": 1, "rating_communication": 1,
            "comment": "recensione non autorizzata"}


class TestTokenRecensione:
    def test_token_inventato_viene_rifiutato(self, csrf_client, consulenza):
        booking_id, _, _ = consulenza
        resp = csrf_client.post(
            f"/api/review/{secrets.token_urlsafe(32)}/submit?booking_id={booking_id}",
            json=_payload(),
        )
        assert resp.status_code == 404

        with Session(engine) as s:
            assert s.exec(select(Review).where(Review.booking_id == booking_id)).first() is None

    def test_booking_id_in_query_string_viene_ignorato(self, csrf_client, consulenza):
        """Anche con un token valido, il booking si risolve dal token e non dall'URL."""
        booking_id, _, _ = consulenza
        token = secrets.token_urlsafe(32)
        with Session(engine) as s:
            b = s.get(Booking, booking_id)
            b.review_token = token
            s.add(b)
            s.commit()

        # booking_id palesemente diverso: la recensione deve finire comunque
        # sul booking a cui appartiene il token
        resp = csrf_client.post(
            f"/api/review/{token}/submit?booking_id=999999", json=_payload()
        )
        assert resp.status_code == 200

        with Session(engine) as s:
            review = s.exec(select(Review).where(Review.booking_id == booking_id)).first()
            assert review is not None
            assert s.get(Booking, 999999) is None

    def test_il_token_e_monouso(self, csrf_client, consulenza):
        booking_id, _, _ = consulenza
        token = secrets.token_urlsafe(32)
        with Session(engine) as s:
            b = s.get(Booking, booking_id)
            b.review_token = token
            s.add(b)
            s.commit()

        assert csrf_client.post(f"/api/review/{token}/submit", json=_payload()).status_code == 200
        # Al secondo tentativo il token e' stato bruciato
        assert csrf_client.post(f"/api/review/{token}/submit", json=_payload()).status_code == 404

    def test_token_troppo_corto_rifiutato_senza_query(self, csrf_client):
        resp = csrf_client.post("/api/review/abc/submit", json=_payload())
        assert resp.status_code == 404

    def test_pagina_recensione_con_token_ignoto(self, client):
        resp = client.get(f"/review/{secrets.token_urlsafe(32)}")
        assert resp.status_code == 200
        assert "Link non valido" in resp.text
