"""
Utility functions per i template Jinja2
"""
from sqlmodel import Session, select
from app.database import engine
from app.models import Category
from app.logger_config import logger


def get_all_categories():
    """
    Carica tutte le categorie dal database.
    Usata per popolare il dropdown nel menu.
    
    Returns:
        List[Category]: Lista di tutte le categorie
    """
    try:
        with Session(engine) as session:
            categories = session.exec(select(Category).order_by(Category.name)).all()
            return categories
    except Exception as e:
        logger.error(f"Errore nel caricamento categorie: {e}")
        return []
