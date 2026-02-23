from __future__ import annotations
from typing import Dict
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

def _get_req_env(name:str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"missing {name}")
    return value

def _parse_api_key(raw:str) -> Dict[str, str]:
    
    keys: Dict[str, str] = {}

    if not raw.strip():
        return keys
    
    for pair in raw.split(','):
        service, _, key = pair.partition(':')
        service = service.strip()
        key = key.strip()

        if not service or not key:
            if not service:
                raise ValueError(f"Empty service name in API_KEYS: '{pair}'")
        if not key:
                raise ValueError(f"Empty key value for service '{service}' in API_KEYS")
        keys[service] = key
    
    return keys


DB_URL: str = _get_req_env("DB_URL")
MLFLOW_URI: str = os.getenv("MLFLOW_URI", "http://localhost:5000")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
API_KEYS: Dict[str, str] = _parse_api_key(
    os.getenv("API_KEYS", "")
)
DATA_DIR: Path = Path(os.getenv("DATA_DIR", "./data")).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)  
FRED_API_KEY: str = _get_req_env("FRED_API_KEY")
NEWS_API_KEY: str = _get_req_env('NEWS_API_KEY')