import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import numpy as np
from sqlalchemy import text
from database.connection import engine
from config.logging_config import get_logger

logger = get_logger(__name__)

TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']


def load_sentiment_scores(ticker: str) -> pd.DataFrame:
    query = """
            SELECT published_at, score
            FROM news_sentiment
            WHERE ticker = :ticker
            ORDER BY published_at ASC
            """
    with engine.connect() as conn:
        df = pd.read_sql(
            sql=text(query),
            con=conn,
            params={'ticker': ticker}
        )
    return df


def compute_daily_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    
    df['date'] = pd.to_datetime(df['published_at']).dt.date
    daily_df = df.groupby('date')['score'].mean().reset_index()
    daily_df.columns= ['date', 'daily_score']
    return daily_df 

def compute_rolling_signals(daily_df: pd.DataFrame) -> pd.DataFrame:
    
    daily_df['rolling_7d'] = daily_df['daily_score'].rolling(7).mean()
    daily_df['rolling_30d'] = daily_df['daily_score'].rolling(30).mean()

    return daily_df

def print_summary(ticker: str, signals_df: pd.DataFrame) -> None:
    """Print latest sentiment signals for ticker."""
    latest = signals_df.iloc[-1]
    if latest['rolling_7d'] > latest['rolling_30d']:
        signal = 'BULLISH'
    elif latest['rolling_7d'] < latest['rolling_30d']:
        signal = 'BEARISH'
    else:
        signal = 'NEUTRAL'
    
    print(f"\n{ticker} Latest Sentiment:")
    print(f"  Daily score:    {latest['daily_score']:.3f}")
    print(f"  7-day rolling:  {latest['rolling_7d']:.3f}")
    print(f"  30-day rolling: {latest['rolling_30d']:.3f}")
    print(f"  Signal:         {signal}")
    

def run(ticker: str) -> pd.DataFrame:
    df = load_sentiment_scores(ticker)
    if df.empty:                         
        logger.warning(f"[{ticker}] No sentiment data")
        return None 
    daily_df = compute_daily_sentiment(df)
    signals_df = compute_rolling_signals(daily_df)
    print_summary(ticker, signals_df)


if __name__ == "__main__":
    for ticker in TICKERS:
        run(ticker)