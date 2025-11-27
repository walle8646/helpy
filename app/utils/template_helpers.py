"""
Utility functions per i template Jinja2
"""
from sqlmodel import Session, select
from app.database import engine
from app.models import Category
from app.logger_config import logger


def get_all_categories():
    """
    Carica solo le 8 categorie principali dal database.
    Usata per popolare il dropdown nel menu header.
    
    Returns:
        List[Category]: Lista delle 8 categorie principali (id <= 8)
    """
    try:
        with Session(engine) as session:
            # Carica solo le categorie principali (id da 1 a 8)
            categories = session.exec(
                select(Category)
                .where(Category.id <= 8)
                .order_by(Category.id)
            ).all()
            return categories
    except Exception as e:
        logger.error(f"Errore nel caricamento categorie: {e}")
        return []
