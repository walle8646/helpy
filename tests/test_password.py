"""Test dell'hashing password e della migrazione da MD5 a bcrypt."""
import hashlib

import pytest

from app.utils.password import (
    UNUSABLE_PASSWORD,
    hash_password,
    is_legacy_hash,
    verify_password,
)


class TestHashBcrypt:
    def test_produce_un_hash_bcrypt(self):
        h = hash_password("password-lunga-abbastanza")
        assert h.startswith("$2")
        assert len(h) >= 59

    def test_hash_diversi_per_la_stessa_password(self):
        # Il salt deve rendere ogni hash diverso: era esattamente cio' che
        # mancava a MD5, e che rende attaccabile un dump con rainbow table.
        a = hash_password("stessa-password")
        b = hash_password("stessa-password")
        assert a != b
        assert verify_password("stessa-password", a)[0]
        assert verify_password("stessa-password", b)[0]

    def test_verifica_corretta(self):
        h = hash_password("segretissima")
        assert verify_password("segretissima", h) == (True, False)
        assert verify_password("sbagliata", h) == (False, False)

    def test_password_oltre_i_72_byte_non_esplode(self):
        lunga = "à" * 100  # 200 byte in UTF-8
        h = hash_password(lunga)
        assert verify_password(lunga, h)[0]


class TestMigrazioneDaMd5:
    def _md5(self, p: str) -> str:
        return hashlib.md5(p.encode()).hexdigest()

    def test_riconosce_hash_legacy(self):
        assert is_legacy_hash(self._md5("qualsiasi"))
        assert not is_legacy_hash(hash_password("qualsiasi"))
        assert not is_legacy_hash("")

    def test_password_legacy_valida_va_ri_hashata(self):
        valida, ri_hashare = verify_password("vecchia-password", self._md5("vecchia-password"))
        assert valida is True
        assert ri_hashare is True

    def test_password_legacy_errata_non_passa(self):
        assert verify_password("altra", self._md5("vecchia-password")) == (False, False)

    def test_dopo_il_ri_hash_non_serve_piu(self):
        nuovo = hash_password("vecchia-password")
        assert verify_password("vecchia-password", nuovo) == (True, False)
        assert not is_legacy_hash(nuovo)


class TestCredenzialiDisattivate:
    def test_valore_impossibile_non_corrisponde_a_niente(self):
        for tentativo in ["", UNUSABLE_PASSWORD, "password", "!disabilitata"]:
            assert verify_password(tentativo, UNUSABLE_PASSWORD) == (False, False)

    def test_hash_vuoto_o_corrotto(self):
        assert verify_password("x", "") == (False, False)
        assert verify_password("x", "non-un-hash") == (False, False)
        assert verify_password("x", "$2b$12$hash-troncato") == (False, False)


class TestMigrazioneDalVivo:
    """La migrazione deve avvenire davvero al primo login, non solo in teoria."""

    def test_login_con_hash_md5_lo_converte_in_bcrypt(self, csrf_client):
        import secrets
        from sqlmodel import Session, select
        from app.database import engine
        from app.models import User
        from app.utils.rate_limit import reset_rate_limit

        reset_rate_limit()
        email = f"legacy-{secrets.token_hex(4)}@test.local"
        password = "vecchia-password-lunga"

        with Session(engine) as s:
            u = User(
                email=email,
                password_md5=hashlib.md5(password.encode()).hexdigest(),
                nome="Legacy",
                confirmed=1,
            )
            s.add(u)
            s.commit()
            s.refresh(u)
            user_id = u.id
            assert is_legacy_hash(u.password_md5)

        try:
            resp = csrf_client.post("/api/login", data={"email": email, "password": password})
            assert resp.status_code == 200, resp.text

            with Session(engine) as s:
                aggiornato = s.get(User, user_id)
                assert not is_legacy_hash(aggiornato.password_md5)
                assert aggiornato.password_md5.startswith("$2")
                # E la stessa password continua a funzionare
                assert verify_password(password, aggiornato.password_md5) == (True, False)
        finally:
            reset_rate_limit()
            with Session(engine) as s:
                u = s.get(User, user_id)
                if u:
                    s.delete(u)
                    s.commit()

    def test_password_sbagliata_non_migra_nulla(self, csrf_client):
        import secrets
        from sqlmodel import Session
        from app.database import engine
        from app.models import User
        from app.utils.rate_limit import reset_rate_limit

        reset_rate_limit()
        email = f"legacy2-{secrets.token_hex(4)}@test.local"
        originale = hashlib.md5(b"giusta-password-lunga").hexdigest()

        with Session(engine) as s:
            u = User(email=email, password_md5=originale, confirmed=1)
            s.add(u)
            s.commit()
            s.refresh(u)
            user_id = u.id

        try:
            resp = csrf_client.post("/api/login", data={"email": email, "password": "sbagliata"})
            assert resp.status_code == 401
            with Session(engine) as s:
                assert s.get(User, user_id).password_md5 == originale
        finally:
            reset_rate_limit()
            with Session(engine) as s:
                u = s.get(User, user_id)
                if u:
                    s.delete(u)
                    s.commit()
