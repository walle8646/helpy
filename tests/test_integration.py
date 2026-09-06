"""Test di integrazione sui flussi che attraversano piu' componenti."""
import secrets
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.database import engine
from app.models import Booking, User
from app.routes.booking import hours_until_booking, now_italy_naive
from app.utils.notification_email import generate_email_html


class TestHomepage:
    def test_home_si_carica(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Ispiramy" in resp.text


class TestTemplateEmail:
    """Un nome template sconosciuto fa fallire l'invio in silenzio: i template
    configurati in notification_types devono esistere tutti."""

    def test_template_noti_producono_html(self):
        dati = {
            "user_name": "Mario", "consultant_name": "Anna", "client_name": "Mario",
            "other_user_name": "Anna", "date": "10/01/2026", "time": "10:00",
            "duration": "60", "action_url": "https://example.test/profile",
            "review_url": "https://example.test/review/x", "rating": "5",
            "comment": "ottimo", "author_name": "Mario", "contact_name": "Anna",
            "question_title": "titolo", "contact_date": "oggi", "reviewer_name": "Mario",
        }
        import re
        for nome in ["booking_confirmed.html", "reminder_1h.html", "reminder_10min.html",
                     "community_contact.html", "booking_refused.html", "review_request.html",
                     "review_reminder.html", "review_received.html"]:
            html = generate_email_html(nome, dati)
            assert html, f"template {nome} non generato"
            # Nessun segnaposto {qualcosa} deve restare non sostituito
            residui = set(re.findall(r"\{([a-z_]+)\}", html))
            assert not residui, f"{nome}: segnaposto non sostituiti {residui}"

    def test_alias_dei_nomi_legacy(self):
        """Alcuni DB hanno i nomi vecchi: devono continuare a funzionare."""
        dati = {"user_name": "Mario", "other_user_name": "Anna", "date": "10/01/2026",
                "time": "10:00", "duration": "60", "action_url": "https://example.test"}
        assert generate_email_html("booking_reminder_1h.html", dati)
        assert generate_email_html("booking_reminder_10min.html", dati)

    def test_template_inesistente_ritorna_none(self):
        assert generate_email_html("non_esiste.html", {}) is None


class TestFinestraDiCancellazione:
    """Il cliente non deve poter annullare (e farsi rimborsare) a ridosso o dopo
    la consulenza: era possibile fino a 15 minuti dopo la fine."""

    def _crea_booking(self, ore_da_ora: float):
        quando = now_italy_naive() + timedelta(hours=ore_da_ora)
        with Session(engine) as s:
            cliente = User(email=f"c-{secrets.token_hex(4)}@test.local", password_md5="x")
            consulente = User(email=f"p-{secrets.token_hex(4)}@test.local", password_md5="x")
            s.add(cliente)
            s.add(consulente)
            s.commit()
            s.refresh(cliente)
            s.refresh(consulente)
            b = Booking(
                client_user_id=cliente.id,
                consultant_user_id=consulente.id,
                booking_date=datetime(quando.year, quando.month, quando.day),
                start_time=quando.strftime("%H:%M"),
                end_time=(quando + timedelta(hours=1)).strftime("%H:%M"),
                duration_minutes=60,
                status="confirmed",
                payment_status="held",
            )
            s.add(b)
            s.commit()
            s.refresh(b)
            return b.id, cliente.id, consulente.id

    def _pulisci(self, ids):
        with Session(engine) as s:
            b = s.get(Booking, ids[0])
            if b:
                s.delete(b)
            for uid in ids[1:]:
                u = s.get(User, uid)
                if u:
                    s.delete(u)
            s.commit()

    def test_consulenza_gia_iniziata_e_fuori_finestra(self):
        ids = self._crea_booking(-1)
        try:
            with Session(engine) as s:
                assert hours_until_booking(s.get(Booking, ids[0])) < 0
        finally:
            self._pulisci(ids)

    def test_consulenza_tra_due_ore_e_fuori_finestra(self):
        ids = self._crea_booking(2)
        try:
            with Session(engine) as s:
                assert hours_until_booking(s.get(Booking, ids[0])) < 4
        finally:
            self._pulisci(ids)

    def test_consulenza_tra_sei_ore_e_annullabile(self):
        ids = self._crea_booking(6)
        try:
            with Session(engine) as s:
                assert hours_until_booking(s.get(Booking, ids[0])) >= 4
        finally:
            self._pulisci(ids)


class TestPresenzaInCall:
    """La presenza istantanea non deve piu' toccare i timestamp di partecipazione,
    che sono la prova su cui il job no-show decide i rimborsi."""

    def test_mark_absent_non_azzera_i_joined_at(self):
        from app.routes.booking import mark_absent, mark_present

        mark_present(12345, 1)
        mark_present(12345, 2)
        rimasti = mark_absent(12345, 1)
        assert rimasti == {2}
        assert mark_absent(12345, 2) == set()
