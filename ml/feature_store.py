import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time
import pandas as pd
from sqlalchemy import text
from database.connection import engine
from config.logging_config import get_logger

logger = get_logger(__name__)

# Global in-memory cache
_cache = {}


def _query_db(ticker: str) -> pd.DataFrame:
    query = """
            SELECT *
            FROM features
            WHERE ticker = :ticker
            ORDER BY date ASC
            """
    with engine.connect() as conn:
        df = pd.read_sql(
            sql=text(query),
            con=conn,
            params={'ticker': ticker}
        )
    return df


def get_features(ticker: str) -> pd.DataFrame:
    """Return features from cache or DB."""
    if ticker not in _cache:
        logger.info(f'No data for {ticker} trying to fetch...')
        df = _query_db(ticker)
        _cache[ticker] = df
        print(f"fetched {ticker}")
    return _cache[ticker]



def invalidate(ticker: str) -> None:
    _cache.pop(ticker, None)



def invalidate_all() -> None:
    _cache.clear()

if __name__ == "__main__":
    import time
    tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']
    
    for ticker in tickers:
        start = time.time()
        df = get_features(ticker)
        elapsed = (time.time() - start) * 1000
        print(f"{ticker}: {len(df)} rows in {elapsed:.1f}ms")
    
    print("\n--- Second call (from cache) ---")
    for ticker in tickers:
        start = time.time()
        df = get_features(ticker)
        elapsed = (time.time() - start) * 1000
        print(f"{ticker}: {len(df)} rows in {elapsed:.1f}ms")