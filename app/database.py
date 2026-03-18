from sqlmodel import SQLModel, create_engine, Session
import os
from app.logger_config import logger
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
    echo=False,  # Log SQL queries (metti False in produzione)
    connect_args=connect_args
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
