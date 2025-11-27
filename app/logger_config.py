from loguru import logger
import os
import logging
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Rimuovi i default handlers
logger.remove()

# Filtro per escludere i log di SQLAlchemy
def sql_alchemy_filter(record):
    # Esclude i messaggi che contengono "sqlalchemy"
    return "sqlalchemy" not in record["message"].lower()

# Aggiungi handler che stampa su stderr (funziona meglio con Docker)
logger.add(
    sys.stderr,
    level=LOG_LEVEL,
    filter=sql_alchemy_filter,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)

# Disabilitare completamente i log di SQLAlchemy a livello di Python logging
logging.getLogger('sqlalchemy').setLevel(logging.CRITICAL + 1)
logging.getLogger('sqlalchemy.engine').setLevel(logging.CRITICAL + 1)
logging.getLogger('sqlalchemy.pool').setLevel(logging.CRITICAL + 1)
logging.getLogger('sqlalchemy.orm').setLevel(logging.CRITICAL + 1)
# Disabilitare log di uvicorn access logs (opzionale)
logging.getLogger('uvicorn.access').setLevel(logging.CRITICAL + 1)
