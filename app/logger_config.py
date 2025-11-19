from loguru import logger
import os
import logging
import sys

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logger.remove()

# Filtro per escludere i log di SQLAlchemy
def sql_alchemy_filter(record):
    # Esclude i messaggi che contengono "sqlalchemy"
    return "sqlalchemy" not in record["message"].lower()

logger.add(
    lambda msg: print(msg, end=""),
    level=LOG_LEVEL,
    filter=sql_alchemy_filter
)

# Disabilitare completamente i log di SQLAlchemy a livello di Python logging
logging.getLogger('sqlalchemy').setLevel(logging.CRITICAL + 1)
logging.getLogger('sqlalchemy.engine').setLevel(logging.CRITICAL + 1)
logging.getLogger('sqlalchemy.pool').setLevel(logging.CRITICAL + 1)
logging.getLogger('sqlalchemy.orm').setLevel(logging.CRITICAL + 1)
# Disabilitare log di uvicorn access logs (opzionale)
logging.getLogger('uvicorn.access').setLevel(logging.CRITICAL + 1)
