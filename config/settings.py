from __future__ import annotations
from typing import Dict
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

def _get_req_env(name: str) -> str:
    """
    FIX: Previously this raised RuntimeError at MODULE IMPORT TIME if an env var
    was missing. That crashed the entire app before uvicorn could bind to the port,
    making Koyeb mark the deployment as failed.
    Now it logs a warning and returns an empty string so the app starts up.
    Individual features that need the key will fail gracefully at request time.
    """
    value = os.getenv(name)
    if value is None or value.strip() == "":
        import logging
        logging.getLogger(__name__).warning(
            f"Environment variable '{name}' is not set. "
            f"Features depending on it will be unavailable."
        )
        return ""
    return value.strip()


def _parse_api_key(raw: str) -> Dict[str, str]:
    keys: Dict[str, str] = {}
    if not raw.strip():
        return keys
    for pair in raw.split(','):
        service, _, key = pair.partition(':')
        service = service.strip()
        key = key.strip()
        if service and key:
            keys[service] = key
    return keys


# ── Core ──────────────────────────────────────────────────────────────────────
DB_URL:      str            = _get_req_env("DB_URL")
LOG_LEVEL:   str            = os.getenv("LOG_LEVEL", "INFO").upper()
MLFLOW_URI:  str            = os.getenv("MLFLOW_URI", "http://localhost:5000")

# ── Optional API keys ─────────────────────────────────────────────────────────
API_KEYS:          Dict[str, str] = _parse_api_key(os.getenv("API_KEYS", ""))
FRED_API_KEY:      str            = _get_req_env("FRED_API_KEY")
NEWSDATA_API_KEY:  str            = _get_req_env("NEWSDATA_API_KEY")

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)