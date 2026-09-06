"""Test delle regole temporali e del calcolo slot delle prenotazioni.

Sono le funzioni che decidono quando si può prenotare, quando si può annullare
(quindi quando scatta un rimborso) e quali orari mostrare al cliente: vale la
pena bloccarne il comportamento.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.models import AvailabilityBlock, Booking
from app.routes.booking import (
    booking_start_datetime,
    calculate_available_slots,
    hours_until_booking,
    minutes_to_time,
    now_italy_naive,
    parse_time_to_minutes,
)

ITALY_TZ = ZoneInfo("Europe/Rome")


def _booking(date: datetime, start: str = "15:00", end: str = "16:00") -> Booking:
    return Booking(
        client_user_id=1,
        consultant_user_id=2,
        booking_date=date,
        start_time=start,
        end_time=end,
        duration_minutes=60,
    )


class TestConversioneOrari:
    def test_stringa_in_minuti(self):
        assert parse_time_to_minutes("00:00") == 0
        assert parse_time_to_minutes("09:30") == 570
        assert parse_time_to_minutes("23:59") == 1439

    def test_andata_e_ritorno(self):
        for minuti in (0, 75, 570, 1439):
            assert parse_time_to_minutes(minutes_to_time(minuti)) == minuti


class TestOrarioItaliano:
    def test_now_italy_naive_e_ora_locale_italiana(self):
        atteso = datetime.now(ITALY_TZ).replace(tzinfo=None)
        delta = abs((now_italy_naive() - atteso).total_seconds())
        assert delta < 5

    def test_non_coincide_con_utcnow(self):
        # È esattamente il bug che rendeva "4 ore prima" un limite di 2 ore:
        # l'Italia non è mai su UTC, né in ora solare né in ora legale.
        scarto = (now_italy_naive() - datetime.utcnow()).total_seconds()
        assert scarto > 1800

    def test_hours_until_booking_futuro(self):
        fra_sei_ore = now_italy_naive() + timedelta(hours=6)
        b = _booking(
            datetime(fra_sei_ore.year, fra_sei_ore.month, fra_sei_ore.day),
            start=fra_sei_ore.strftime("%H:%M"),
        )
        assert 5.9 < hours_until_booking(b) < 6.1

    def test_hours_until_booking_passato_e_negativo(self):
        due_ore_fa = now_italy_naive() - timedelta(hours=2)
        b = _booking(
            datetime(due_ore_fa.year, due_ore_fa.month, due_ore_fa.day),
            start=due_ore_fa.strftime("%H:%M"),
        )
        assert hours_until_booking(b) < 0

    def test_booking_start_datetime_accetta_stringhe(self):
        b = _booking(datetime(2026, 9, 10), start="14:30")
        assert booking_start_datetime(b) == datetime(2026, 9, 10, 14, 30)


def _blocco(start: str, end: str, block_id: int = 1) -> AvailabilityBlock:
    h1, m1 = map(int, start.split(":"))
    h2, m2 = map(int, end.split(":"))
    b = AvailabilityBlock(
        user_id=2,
        date=datetime(2030, 1, 1),
        start_time=__import__("datetime").time(h1, m1),
        end_time=__import__("datetime").time(h2, m2),
        total_minutes=(h2 * 60 + m2) - (h1 * 60 + m1),
    )
    b.id = block_id
    return b


class TestCalcoloSlot:
    """La data usata è lontana nel futuro, così il vincolo delle 4 ore non entra in gioco."""

    DATA = "2030-01-01"

    def test_blocco_vuoto_genera_slot_ogni_15_minuti(self):
        slots = calculate_available_slots([_blocco("09:00", "11:00")], [], 60, self.DATA)
        inizi = [s["start_time"] for s in slots]
        assert inizi[0] == "09:00"
        assert inizi[-1] == "10:00"  # l'ultimo slot da 60' deve stare dentro le 11:00
        assert "10:15" not in inizi

    def test_durata_piu_lunga_del_blocco_non_genera_slot(self):
        assert calculate_available_slots([_blocco("09:00", "10:00")], [], 120, self.DATA) == []

    def test_una_prenotazione_esistente_libera_solo_gli_spazi_reali(self):
        occupato = _booking(datetime(2030, 1, 1), start="10:00", end="11:00")
        slots = calculate_available_slots([_blocco("09:00", "13:00")], [occupato], 60, self.DATA)
        inizi = [s["start_time"] for s in slots]
        assert "09:00" in inizi
        assert "11:00" in inizi
        # Nessuno slot può sovrapporsi alla fascia 10:00-11:00
        assert "09:30" not in inizi
        assert "10:00" not in inizi
        assert "10:30" not in inizi

    def test_nessuna_disponibilita_nessuno_slot(self):
        assert calculate_available_slots([], [], 60, self.DATA) == []

    def test_lo_slot_riporta_il_blocco_di_origine(self):
        slots = calculate_available_slots([_blocco("09:00", "10:00", block_id=77)], [], 60, self.DATA)
        assert slots and all(s["availability_block_id"] == 77 for s in slots)
