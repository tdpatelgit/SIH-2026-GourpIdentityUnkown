"""Central logging config for the backend — one place to configure the
root logger so every module's log lines are formatted consistently and
show up in whatever terminal is running uvicorn.

Import `get_logger(__name__)` in any module instead of `logging.getLogger`
directly, so format/level stay consistent everywhere.
"""
import logging
import os
import sys

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers if configure_logging() is called more than
    # once (e.g. once from main.py, once from a test import) — uvicorn's
    # --reload also re-imports the app module.
    root.handlers = [handler]

    # Quiet down noisy third-party loggers unless LOG_LEVEL explicitly
    # asks for DEBUG (then let everything through for troubleshooting).
    if level > logging.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("PIL").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
