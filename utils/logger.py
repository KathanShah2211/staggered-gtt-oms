"""
utils/logger.py
===============
Application-wide daily rotating log file setup.

Logs are written to:  data/logs/YYYY-MM-DD.log

Usage
-----
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Message")
    log.error("Error details", exc_info=True)
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path

# Resolve log directory relative to project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_LOG_DIR = _PROJECT_ROOT / "data" / "logs"

_initialized: bool = False
_formatter = logging.Formatter(
    fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def _ensure_log_dir() -> None:
    _LOG_DIR.mkdir(parents=True, exist_ok=True)


def _build_daily_log_path() -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    return _LOG_DIR / f"{today}.log"


def setup_logging() -> None:
    """
    Configure the root logger once at application startup.

    - Daily rotating file handler (midnight rollover, keeps 30 days).
    - Console handler for DEBUG output (useful during development).
    """
    global _initialized
    if _initialized:
        return

    _ensure_log_dir()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # ── Daily rotating file handler ──────────────────────────────
    log_path = _build_daily_log_path()
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename  = str(log_path),
        when      = "midnight",
        interval  = 1,
        backupCount = 30,
        encoding  = "utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(_formatter)
    file_handler.suffix = "%Y-%m-%d"
    root_logger.addHandler(file_handler)

    # ── Console handler (INFO+ only) ────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(_formatter)
    root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    for noisy in ("urllib3", "socketio", "engineio", "APILogger", "WebsocketLogger"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _initialized = True
    logging.getLogger(__name__).info("Logging initialised → %s", log_path)


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.  setup_logging() is called automatically
    on first use if it hasn't been called already.
    """
    if not _initialized:
        setup_logging()
    return logging.getLogger(name)
