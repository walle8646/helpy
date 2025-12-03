"""
Utility functions per i template Jinja2
"""
from sqlmodel import Session, select
from app.database import engine
from app.models import Category
from app.logger_config import logger


def get_all_categories():
    """
    Carica solo le categorie principali dal database.
    Usata per popolare il dropdown nel menu header.
    
    Returns:
        List[Category]: Lista delle categorie principali (is_principal = True)
    """
    try:
        with Session(engine) as session:
            # Carica solo le categorie principali
            categories = session.exec(
                select(Category)
                .where(Category.is_principal == True)
                .order_by(Category.id)
            ).all()
            return categories
    except Exception as e:
        logger.error(f"Errore nel caricamento categorie: {e}")
        return []
