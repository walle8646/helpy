from loguru import logger
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
logger.remove()
logger.add(lambda msg: print(msg, end=""), level=LOG_LEVEL)
