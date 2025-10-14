from sqlmodel import SQLModel, create_engine, Session
import os
from app.logger_config import logger

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    logger.info("Connessione al database e creazione tabelle se necessario")
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
