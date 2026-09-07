import logging
import os
import sys
from logging.handlers import RotatingFileHandler

_configured = False


def _log_dir() -> str:
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "logs")
    os.makedirs(path, exist_ok=True)
    return path


def setup_logging() -> logging.Logger:
    global _configured
    logger = logging.getLogger("portfolio")
    if _configured:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler = RotatingFileHandler(
        os.path.join(_log_dir(), "app.log"),
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)
    stream = logging.StreamHandler()
    stream.setFormatter(fmt)
    logger.addHandler(stream)
    _configured = True
    return logger


def get_logger() -> logging.Logger:
    return setup_logging()
