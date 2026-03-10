from __future__ import annotations
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Any, Dict

# FIX: import LOG_LEVEL safely — if settings fails, default to INFO
try:
    from config.settings import LOG_LEVEL
except Exception:
    LOG_LEVEL = "INFO"

MAX_BYTES    = 10 * 1024 * 1024   # 10 MB
BACKUP_COUNT = 5


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level":     record.levelname,
            "logger":    record.name,
            "message":   record.getMessage(),
            "module":    record.module,
            "function":  record.funcName,
            "line":      record.lineno,
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_record)


def _configure_root_logger() -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVEL)

    # Don't add handlers twice (e.g. on Dash hot-reload)
    if root_logger.handlers:
        return

    formatter = JsonFormatter()

    # Always add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # FIX: file handler is optional — on Koyeb the container may not have a
    # writable logs/ directory. Fail silently and keep console logging.
    try:
        LOG_DIR = Path("logs")
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        LOG_FILE = LOG_DIR / "app.log"
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        root_logger.warning(f"Could not create file log handler: {e}. Logging to console only.")


_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)