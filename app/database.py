from sqlmodel import SQLModel, create_engine, Session
import os
from app.logger_config import logger
from app.models import ImageLink  # ...existing code...
from app.models_user import User  # AGGIUNGI QUESTA RIGA
from contextlib import contextmanager

# Ottieni DATABASE_URL da environment
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./helpy.db")

# 🔥 FIX per Render: postgres:// → postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configurazione engine
connect_args = {}
if "sqlite" in DATABASE_URL:
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    echo=True,  # Log SQL queries (metti False in produzione)
    connect_args=connect_args
)

@contextmanager
def get_session():
    with Session(engine) as session:
        yield session

def create_db_and_tables():
    """Crea tutte le tabelle se non esistono"""
    logger.info("Creating database and tables")
    SQLModel.metadata.create_all(engine)
