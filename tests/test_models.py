"""Test delle utility su utenti e modelli.

Sostituiscono i test precedenti, che facevano riferimento a un modello
`Example` mai esistito in questo progetto e rompevano l'intera raccolta pytest.
"""
from datetime import datetime

from app.models import Booking, User
from app.utils_user import (
    get_default_avatar,
    get_display_name,
    has_payment_method,
)
from app.utils.email import generate_verification_code


def _user(**kwargs) -> User:
    base = dict(email="mario@example.com", password_md5="x", nome="Mario", cognome="Rossi")
    base.update(kwargs)
    return User(**base)


class TestDisplayName:
    def test_nome_completo(self):
        assert get_display_name(_user()) == "Mario Rossi"

    def test_solo_nome(self):
        assert get_display_name(_user(), include_full_name=False) == "Mario"

    def test_modalita_anonima_nasconde_il_nome(self):
        u = _user(is_anonymous=True)
        u.id = 42
        assert get_display_name(u) == "Utente #42"
        assert "Mario" not in get_display_name(u)

    def test_senza_nome_ripiega_sull_id(self):
        u = _user(nome=None, cognome=None)
        u.id = 7
        assert get_display_name(u) == "Utente #7"


class TestAvatar:
    def test_per_genere(self):
        assert get_default_avatar(_user(genere="M")) == "/static/avatar-male.svg"
        assert get_default_avatar(_user(genere="F")) == "/static/avatar-female.svg"
        assert get_default_avatar(_user(genere=None)) == "/static/avatar-default.svg"


class TestMetodoPagamento:
    def test_nessun_metodo(self):
        assert has_payment_method(_user()) is False

    def test_stripe_completato(self):
        assert has_payment_method(_user(stripe_onboarding_complete=True)) is True

    def test_solo_paypal(self):
        assert has_payment_method(_user(paypal_email="mario@paypal.com")) is True

    def test_stripe_account_senza_onboarding_non_basta(self):
        assert has_payment_method(_user(stripe_account_id="acct_123")) is False


class TestCodici:
    def test_lunghezza_e_cifre(self):
        code = generate_verification_code()
        assert len(code) == 6
        assert code.isdigit()

    def test_non_sono_costanti(self):
        # Non prova la qualità crittografica, ma intercetta un generatore rotto
        assert len({generate_verification_code() for _ in range(50)}) > 1


class TestBookingDefaults:
    def test_stato_iniziale(self):
        b = Booking(
            client_user_id=1,
            consultant_user_id=2,
            booking_date=datetime(2026, 9, 10),
            start_time="10:00",
            end_time="11:00",
            duration_minutes=60,
        )
        assert b.status == "pending"
        assert b.payment_status == "pending"
        assert b.recording_status == "not_started"
        assert b.recording_requested is True
        # Il token recensione nasce vuoto: viene valorizzato solo all'invio
        # dell'email, ed è quello che autorizza a recensire senza login.
        assert b.review_token is None
