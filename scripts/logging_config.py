import logging
import os
from logging.handlers import RotatingFileHandler
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None  # fallback if not installed

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE_PATH = os.path.join(LOG_DIR, "pipeline.log")

def get_logger(name=__name__, use_json=False):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.hasHandlers():
        logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler()
    if use_json and jsonlogger:
        formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(message)s')
    else:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler with Rotation
    file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=5_000_000, backupCount=3)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger