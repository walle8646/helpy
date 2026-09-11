"""L'istante di inizio call deve arrivare al browser identico e con il fuso.

Prima il primo /call-start restituiva "…15:30+02:00" (valore appena creato, con
fuso) e i successivi "…13:30" o "…15:30" senza fuso (letto dal database). Su
PostgreSQL il valore con fuso veniva anche convertito in UTC entrando nella
colonna senza fuso: al ricaricamento il cronometro saltava avanti di due ore.
"""
import secrets
from datetime import datetime

import pytest
from sqlmodel import Session

from app.database import engine
from app.models import Booking, User
from app.utils.orari import iso_ora_italiana, now_italy_naive
from app.utils.password import hash_password
from app.utils.rate_limit import reset_rate_limit


class TestFormato:
    def test_ora_legale(self):
        assert iso_ora_italiana(datetime(2026, 9, 11, 15, 30)) == "2026-09-11T15:30:00+02:00"

    def test_ora_solare(self):
        assert iso_ora_italiana(datetime(2026, 1, 11, 15, 30)) == "2026-01-11T15:30:00+01:00"

    def test_valore_gia_con_fuso_resta_com_e(self):
        from zoneinfo import ZoneInfo
        dt = datetime(2026, 9, 11, 13, 30, tzinfo=ZoneInfo("UTC"))
        assert iso_ora_italiana(dt) == "2026-09-11T13:30:00+00:00"

    def test_nessun_valore(self):
        assert iso_ora_italiana(None) is None


@pytest.fixture
def partecipante_in_call(csrf_client):
    """Un cliente loggato con una consulenza in corso adesso."""
    reset_rate_limit()
    password = secrets.token_urlsafe(12)
    adesso = now_italy_naive()
    with Session(engine) as s:
        cliente = User(email=f"call-c-{secrets.token_hex(4)}@test.local",
                       password_md5=hash_password(password), confirmed=1)
        consulente = User(email=f"call-p-{secrets.token_hex(4)}@test.local",
                          password_md5="x", confirmed=1)
        s.add(cliente)
        s.add(consulente)
        s.commit()
        s.refresh(cliente)
        s.refresh(consulente)
        b = Booking(
            client_user_id=cliente.id, consultant_user_id=consulente.id,
            booking_date=datetime(adesso.year, adesso.month, adesso.day),
            start_time="00:00", end_time="23:59", duration_minutes=60,
            status="confirmed", payment_status="held",
        )
        s.add(b)
        s.commit()
        s.refresh(b)
        ids = (b.id, cliente.id, consulente.id, cliente.email)

    r = csrf_client.post("/api/login", data={"email": ids[3], "password": password})
    assert r.status_code == 200, r.text
    yield csrf_client, ids[0]

    csrf_client.get("/logout")
    reset_rate_limit()
    with Session(engine) as s:
        b = s.get(Booking, ids[0])
        if b:
            s.delete(b)
        for uid in ids[1:3]:
            u = s.get(User, uid)
            if u:
                s.delete(u)
        s.commit()


class TestEndpoint:
    def test_primo_avvio_e_ricaricamento_danno_lo_stesso_istante(self, partecipante_in_call):
        client, booking_id = partecipante_in_call

        primo = client.post(f"/api/booking/{booking_id}/call-start").json()["call_started_at"]
        ricaricato = client.post(f"/api/booking/{booking_id}/call-start").json()["call_started_at"]

        assert primo == ricaricato
        assert primo.endswith(("+01:00", "+02:00")), f"manca il fuso: {primo}"

    def test_salvato_come_ora_italiana_senza_fuso(self, partecipante_in_call):
        client, booking_id = partecipante_in_call
        client.post(f"/api/booking/{booking_id}/call-start")

        with Session(engine) as s:
            salvato = s.get(Booking, booking_id).call_started_at
        assert salvato.tzinfo is None
        scarto = abs((salvato - now_italy_naive()).total_seconds())
        assert scarto < 60, "l'orario salvato non è l'ora italiana corrente"


class TestGuardiaFusoOrario:
    """Un datetime con fuso salvato in una colonna senza fuso viene convertito
    in UTC da PostgreSQL. SQLite invece toglie solo il fuso: nessun test su
    SQLite vedrebbe il problema, quindi lo si impedisce leggendo il sorgente."""

    def test_nessuna_colonna_riceve_un_datetime_con_fuso(self):
        import re
        from pathlib import Path

        radice = Path(__file__).resolve().parent.parent / "app"
        # es.  booking.payment_released_at = datetime.now(ITALY_TZ)
        #      Dispute(created_at=datetime.now(ITALY_TZ), ...)
        schema = re.compile(r"(\.\w+_(at|until)\s*=|\b\w+_(at|until)\s*=)\s*datetime\.now\(\s*\w*TZ\s*\)")
        violazioni = []
        for f in radice.rglob("*.py"):
            for n, riga in enumerate(f.read_text(encoding="utf-8-sig").splitlines(), 1):
                if schema.search(riga):
                    violazioni.append(f"{f.relative_to(radice.parent)}:{n}")
        assert not violazioni, (
            "usare now_italy_naive() per i valori da salvare: " + ", ".join(violazioni)
        )
