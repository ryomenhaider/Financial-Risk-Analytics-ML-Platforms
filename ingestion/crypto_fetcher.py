
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ccxt
import pandas as pd
from datetime import datetime, timezone
from database.connection import get_session
from database.crud import insert_crypto_prices

SYMBOLS = {
    "BTC/USDT": "BTC-USD",
    "ETH/USDT": "ETH-USD",
    "BNB/USDT": "BNB-USD",
    "SOL/USDT": "SOL-USD",
    "ADA/USDT": "ADA-USD",
}

EXCHANGE = "binance"
TIMEFRAME = "1d"
LIMIT = 365


def fetch_ohlcv(exchange, symbol: str) -> list:
    raw = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=LIMIT)
    return raw   


def transform(raw: list, symbol: str) -> list[dict]:

    record = []
    for row in raw:
        record.append({
            'symbol': symbol,
            'date': datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc).date(),
            "open":   row[1],
            "high":   row[2],
            "low":    row[3],
            "close":  row[4],
            "volume": row[5],
            }
        )

    return record


def run():
    exchange = ccxt.binance()
    session = get_session()
    try:
        for symbol, name in SYMBOLS.items():
            print(f"[{symbol}] fetching '{name}'....")
            try:
                raw = fetch_ohlcv(exchange,     symbol)
                records = transform(raw, symbol)

                if not records:
                    print(f'[{symbol}] No Valid Records, Skipping.')
                    continue

                insert_crypto_prices(session, records)
                print(f'[{symbol}] Inserted {len(records)} records')
            
            except Exception as e:
                print(f'[{symbol} Unexpected Error: {e}]')
                session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    run()