from sqlmodel import SQLModel, create_engine, Session
import os
from app.logger_config import logger
from app.models import ImageLink  # ...existing code...
from app.models_user import User  # AGGIUNGI QUESTA RIGA

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
engine = create_engine(DATABASE_URL, echo=True)

def create_db_and_tables():
    logger.info("Creating database and tables")
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
