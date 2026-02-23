import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time
import yfinance as yf
import pandas as pd
from database.connection import get_session
from database.crud import insert_market_data

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"]
PERIOD = "1y"
INTERVAL = "1d"

def fetch_ticker(symbol: str) -> pd.DataFrame:
    import requests
    session = requests.Session()
    session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })

    return yf.Ticker(symbol, session=session).history(period=PERIOD, interval=INTERVAL)

def transform(df: pd.DataFrame, symbol: str) -> list[dict]:
    df = df.rename(columns={
        "Date":   "date",
        "Open":   "open",
        "High":   "high",
        "Low":    "low",
        "Close":  "close",
        "Volume": "volume",
    })

    cols = ["date", "open", "high", "low", "close", "volume"]
    df = df[[c for c in cols if c in df.columns]].copy()

    df["ticker"] = symbol


    if pd.api.types.is_datetime64tz_dtype(df["date"]):
        df["date"] = df["date"].dt.tz_convert(None)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    df = df.dropna(subset=["date", "close"])

    return df.to_dict(orient="records")

def run():
    session = get_session()
    try:
        for symbol in TICKERS:
            print(f"[{symbol}] Fetching data...")
            try:
                raw_df = fetch_ticker(symbol)

                if raw_df.empty:
                    print(f"[{symbol}] No data returned, skipping.")
                    continue

                records = transform(raw_df, symbol)

                if not records:
                    print(f"[{symbol}] No valid records after transform, skipping.")
                    continue

                insert_market_data(session, records)
                print(f"[{symbol}] Inserted {len(records)} records.")

            except Exception as e:
                print(f"[{symbol}] Error: {e}")
                session.rollback()

            # Be polite to the API
            time.sleep(1)

    finally:
        session.close()

if __name__ == "__main__":
    run()