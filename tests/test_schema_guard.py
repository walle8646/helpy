"""Le colonne aggiunte ai modelli devono comparire da sole nei database esistenti.

create_all() non aggiunge colonne a tabelle già esistenti: con il deploy
automatico dello staging, una colonna nuova nel modello rompeva ogni query su
quella tabella finché la migrazione non veniva lanciata a mano.
"""
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, select

import app.models  # noqa: F401 — registra tutti i modelli nel metadata
from app.database import COLONNE_AGGIUNTE, ensure_added_columns
from app.models import Booking, SocialDraft


@pytest.fixture
def db_con_schema_vecchio():
    """Database con tutte le tabelle ma SENZA le colonne aggiunte di recente,
    come un database di produzione su cui le migrazioni non sono state lanciate."""
    percorso = Path(tempfile.mkdtemp()) / "vecchio.db"
    eng = create_engine(f"sqlite:///{percorso.as_posix()}")
    SQLModel.metadata.create_all(eng)
    with eng.begin() as conn:
        for tabella, colonna, _ in COLONNE_AGGIUNTE:
            for idx in inspect(eng).get_indexes(tabella):
                if colonna in idx["column_names"]:
                    conn.execute(text(f'DROP INDEX "{idx["name"]}"'))
            conn.execute(text(f'ALTER TABLE "{tabella}" DROP COLUMN {colonna}'))
    yield eng
    eng.dispose()


def _colonne(eng, tabella):
    return {c["name"] for c in inspect(eng).get_columns(tabella)}


class TestColonneMancanti:
    def test_senza_colonna_le_query_si_rompono(self, db_con_schema_vecchio):
        """Premessa: è davvero il guasto che vogliamo prevenire."""
        with Session(db_con_schema_vecchio) as s:
            with pytest.raises(OperationalError, match="review_token"):
                s.exec(select(Booking)).all()

    def test_la_guardia_aggiunge_le_colonne(self, db_con_schema_vecchio):
        aggiunte = ensure_added_columns(db_con_schema_vecchio)

        assert "booking.review_token" in aggiunte
        assert "social_drafts.publish_attempt" in aggiunte
        assert "review_token" in _colonne(db_con_schema_vecchio, "booking")
        assert "publish_attempt" in _colonne(db_con_schema_vecchio, "social_drafts")

    def test_dopo_la_guardia_le_query_funzionano(self, db_con_schema_vecchio):
        ensure_added_columns(db_con_schema_vecchio)
        with Session(db_con_schema_vecchio) as s:
            assert s.exec(select(Booking)).all() == []
            s.add(SocialDraft(platform="facebook", caption="x"))
            s.commit()
            bozza = s.exec(select(SocialDraft)).one()
            assert bozza.publish_attempt == 0

    def test_le_righe_esistenti_ricevono_il_default(self, db_con_schema_vecchio):
        """Una colonna NOT NULL su una tabella già popolata deve avere un default."""
        with db_con_schema_vecchio.begin() as conn:
            conn.execute(text(
                "INSERT INTO social_drafts (platform, caption, status, created_at, updated_at) "
                "VALUES ('facebook', 'bozza storica', 'draft', '2026-01-01', '2026-01-01')"
            ))
        ensure_added_columns(db_con_schema_vecchio)
        with Session(db_con_schema_vecchio) as s:
            assert s.exec(select(SocialDraft)).one().publish_attempt == 0

    def test_e_idempotente(self, db_con_schema_vecchio):
        assert ensure_added_columns(db_con_schema_vecchio)
        assert ensure_added_columns(db_con_schema_vecchio) == []


class TestCoerenzaConIModelli:
    def test_ogni_colonna_elencata_esiste_nel_modello(self):
        """Un refuso nell'elenco aggiungerebbe una colonna che il modello non usa."""
        tabelle = SQLModel.metadata.tables
        for tabella, colonna, _ in COLONNE_AGGIUNTE:
            assert tabella in tabelle, f"tabella sconosciuta: {tabella}"
            assert colonna in tabelle[tabella].columns, f"{tabella}.{colonna} non è nel modello"

    def test_ogni_colonna_ha_la_sua_migrazione_sql(self):
        cartella = Path(__file__).resolve().parent.parent / "sql_update"
        sql = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in cartella.glob("*.sql"))
        for tabella, colonna, _ in COLONNE_AGGIUNTE:
            assert colonna in sql, f"manca una migrazione in sql_update/ per {tabella}.{colonna}"
