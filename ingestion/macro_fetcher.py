import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from database.connection import get_session
from database.crud import insert_economic_indicators
from config.settings import FRED_API_KEY 

SERIES = {
    "DFF": "Fed Fund Rate",
    "CPIAUCSL" : "CPI",
    "UNRATE": "Unemployment",
    "GDP": "GDP",
    "T10Y2Y": "Yield Curve Speed",
    "VIXCLS": "VIX",
    "DTWEXBGS": "USD Index",
    "MORTGAGE30US": "30Y Mortgage Rate"
}

FRED_BASE_URL = 'https://api.stlouisfed.org/fred/series/observations'

def fetch_series(series_id: str, observation_start: str = "2020-01-01") -> list[dict]:
    params = {
        "series_id":         series_id,
        "api_key":           FRED_API_KEY,
        "file_type":         "json",
        "observation_start": observation_start,
    }

    response = requests.get(FRED_BASE_URL, params=params)
    response.raise_for_status()

    return response.json().get("observations", [])

def transform(observations: list[dict], series_id: str) -> list[dict]:
    records = []
    for obs in observations:
        if obs["value"] == ".":
            continue
        records.append({
            "series_id": series_id,
            "date":      obs["date"],
            "value":     float(obs["value"]),
        })
    return records

def run():
    session = get_session()
    try:
        for series_id, name in SERIES.items():
            print(f"[{series_id}] Fetching '{name}'...")
            try:
                observations = fetch_series(series_id)
                records = transform(observations, series_id)

                if not records:
                    print(f"[{series_id}] No valid records, skipping.")
                    continue

                insert_economic_indicators(session, records)
                print(f"[{series_id}] Inserted {len(records)} records.")

            except requests.HTTPError as e:
                print(f"[{series_id}] HTTP error: {e}")
            except Exception as e:
                print(f"[{series_id}] Unexpected error: {e}")
                session.rollback()
    finally:
        session.close()

if __name__ == '__main__':
    run()