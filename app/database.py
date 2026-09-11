from sqlmodel import SQLModel, create_engine, Session
import os
from app.logger_config import logger
from contextlib import contextmanager

# Ottieni DATABASE_URL da environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ispiramy.db")

# 🔥 FIX per Render: postgres:// → postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configurazione engine
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    echo=False,  # Log SQL queries (metti False in produzione)
    connect_args=connect_args,
    # Verifica la connessione prima di usarla e la ricrea se è stata chiusa.
    # Una connessione rimasta ferma nel pool (es. mentre l'utente paga su
    # Stripe) può essere stata chiusa dal server o dalla rete: senza questo la
    # prima query al ritorno falliva, e verify_token trattava l'errore come
    # "utente non autenticato" — l'utente risultava sloggato.
    pool_pre_ping=True,
    pool_recycle=1800,
)

@contextmanager
def get_session():
    """Context manager per sessione database"""
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    """Crea tutte le tabelle se non esistono"""
    logger.info("Creating database and tables")
    # Import modelli per registrarli
    from app.models import (
        User, Category, CategoryHierarchy,
        Consultation, 
        Conversation, Message,
        CommunityQuestion,  # ✅ Solo CommunityQuestion, senza CommunityAnswer
        AvailabilityBlock,  # ✅ Gestione disponibilità
        Booking,  # ✅ Gestione prenotazioni
        ConsultationOffer,  # ✅ Gestione offerte consulenze
        ConfigurationProperty,  # ✅ Configurazione globale
        FavoriteConsultant  # ✅ Consulenti preferiti
    )
    
    SQLModel.metadata.create_all(engine)
    ensure_added_columns()
    ensure_check_constraints()

    from app.utils.notification_types import ensure_notification_types
    ensure_notification_types()


# Colonne aggiunte ai modelli DOPO che le tabelle esistevano già in produzione.
#
# create_all() crea le tabelle mancanti ma non aggiunge colonne a quelle
# esistenti. Senza migrazione, SQLModel include comunque la colonna in ogni
# SELECT e ogni query sulla tabella fallisce con "column does not exist".
# Lo staging si deploya da solo a ogni push su develop, quindi una colonna nuova
# nel modello rompeva l'app finché qualcuno non lanciava la migrazione a mano.
#
# Ogni voce corrisponde a una migrazione in sql_update/: qui ci sono solo le
# aggiunte di colonna, sicure da eseguire all'avvio (su PostgreSQL un ADD
# COLUMN nullable o con default costante è istantaneo e non riscrive la
# tabella). Indici e dati restano nei file SQL.
COLONNE_AGGIUNTE = [
    # (tabella, colonna, definizione SQL)                  migrazione
    ("booking", "review_token", "VARCHAR(64)"),             # migration_add_booking_review_token
    ("social_drafts", "publish_attempt", "INTEGER NOT NULL DEFAULT 0"),  # migration_add_social_publish_attempt
    ("user", "confirmation_code_created_at", "TIMESTAMP"),     # migration_add_confirmation_code_created_at
    ("user", "auto_accept_bookings", "BOOLEAN NOT NULL DEFAULT TRUE"),  # migration_add_booking_acceptance
    ("booking", "acceptance_deadline", "TIMESTAMP"),         # migration_add_booking_acceptance
    ("booking", "paypal_authorization_id", "VARCHAR(64)"),   # migration_add_booking_acceptance
]


# Valori ammessi dai CHECK sulla tabella booking in PostgreSQL (creati dalle
# migrazioni in sql_update/). Un valore nuovo nel codice ma non nel vincolo fa
# fallire ogni UPDATE che lo usa: il vincolo va allineato insieme al codice.
VINCOLI_BOOKING = {
    "chk_booking_status": ("status", [
        "pending", "pending_payment", "awaiting_acceptance", "confirmed",
        "completed", "cancelled", "no_show",
    ]),
    "chk_payment_status": ("payment_status", [
        "pending", "authorized", "held", "paid", "released", "refunded",
        "partially_refunded", "voided", "failed",
    ]),
}


def ensure_check_constraints(eng=None) -> list[str]:
    """Allinea i CHECK di booking ai valori usati dal codice (solo PostgreSQL).

    Tocca solo i vincoli che esistono già e a cui manca qualche valore. Il
    vincolo nuovo è aggiunto NOT VALID: vale per le scritture da qui in poi e
    non ricontrolla le righe esistenti, quindi non può fallire su dati vecchi.
    Ritorna i nomi dei vincoli aggiornati.
    """
    from sqlalchemy import text

    eng = eng or engine
    if eng.dialect.name != "postgresql":
        return []

    aggiornati = []
    for nome, (colonna, valori) in VINCOLI_BOOKING.items():
        try:
            with eng.begin() as conn:
                definizione = conn.execute(text(
                    "SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c "
                    "JOIN pg_class t ON t.oid = c.conrelid "
                    "WHERE t.relname = 'booking' AND c.conname = :nome"
                ), {"nome": nome}).scalar()
                if definizione is None or all(f"'{v}'" in definizione for v in valori):
                    continue
                elenco = ", ".join(f"'{v}'" for v in valori)
                conn.execute(text(f"ALTER TABLE booking DROP CONSTRAINT {nome}"))
                conn.execute(text(
                    f"ALTER TABLE booking ADD CONSTRAINT {nome} CHECK ({colonna} IN ({elenco})) NOT VALID"
                ))
            aggiornati.append(nome)
            logger.warning(f"🛠️ Schema: vincolo {nome} aggiornato con i nuovi valori")
        except Exception as e:  # noqa: BLE001
            logger.error(
                f"❌ Schema: impossibile aggiornare il vincolo {nome} ({e}). "
                "Applicare a mano sql_update/migration_add_booking_acceptance_postgres.sql."
            )
    return aggiornati


def ensure_added_columns(eng=None) -> list[str]:
    """Aggiunge le colonne di COLONNE_AGGIUNTE che mancano nel database.

    Idempotente: controlla lo schema reale prima di ogni ALTER. Ritorna
    l'elenco delle colonne aggiunte (vuoto se era già tutto a posto).
    """
    from sqlalchemy import inspect, text

    eng = eng or engine
    tabelle = set(inspect(eng).get_table_names())
    aggiunte = []

    for tabella, colonna, definizione in COLONNE_AGGIUNTE:
        if tabella not in tabelle:
            continue  # appena creata da create_all, ha già tutte le colonne
        if colonna in {c["name"] for c in inspect(eng).get_columns(tabella)}:
            continue
        try:
            # Una transazione per colonna: su PostgreSQL un errore annulla
            # l'intera transazione e bloccherebbe anche le aggiunte successive.
            with eng.begin() as conn:
                conn.execute(text(f'ALTER TABLE "{tabella}" ADD COLUMN {colonna} {definizione}'))
            aggiunte.append(f"{tabella}.{colonna}")
        except Exception as e:  # noqa: BLE001
            # Due processi avviati insieme possono provarci entrambi: se ora la
            # colonna c'è, l'ha aggiunta l'altro e va bene così.
            if colonna in {c["name"] for c in inspect(eng).get_columns(tabella)}:
                continue
            logger.error(
                f"❌ Schema: impossibile aggiungere {tabella}.{colonna} ({e}). "
                "Le query su questa tabella falliranno: applicare a mano la migrazione in sql_update/."
            )

    for nome in aggiunte:
        logger.warning(
            f"🛠️ Schema: aggiunta la colonna mancante {nome} "
            "(la migrazione in sql_update/ non era stata applicata)"
        )
    return aggiunte
