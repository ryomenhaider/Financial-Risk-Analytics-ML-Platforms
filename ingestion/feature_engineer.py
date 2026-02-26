import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import numpy as np
from database.connection import get_session
from database.crud import get_latest_prices
from database.crud import insert_features
from database.crud import get_all_tickers

def fetch_price_data(ticker: str, session, limit: int = 100) -> pd.DataFrame:
    rows = get_latest_prices(session, ticker, limit)
    records = [
        {
            "ticker": row.ticker,
            "date": row.date,
            "open": row.open,
            "high": row.high,
            "low": row.low,
            "close": row.close,
            "volume": row.volume,
        }
        for row in rows
    ]
    df = pd.DataFrame(records)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df

def compute_log_returns(df: pd.DataFrame) -> pd.DataFrame:

    if df is None or df.empty:
            raise ValueError("DataFrame is empty or None")

    df = df.sort_values('date').reset_index(drop=True)

    df['log_return'] = np.log(df['close']/df['close'].shift(1))

    return df

def compute_lag_features(df: pd.DataFrame) -> pd.DataFrame:


    if df is None or df.empty:
        raise ValueError("DataFrame is empty or None")
    df = df.sort_values('date').reset_index(drop=True)

    df['lag_1d'] = df['log_return'].shift(1)
    df['lag_5d'] = df['log_return'].shift(5)
    df['lag_21d'] = df['log_return'].shift(21)
    df['lag_63d'] = df['log_return'].shift(63)

    return df

def compute_rolling_stats(df:pd.DataFrame) -> pd.DataFrame:
    
    required_col = "log_return"
    if required_col not in df.columns:
        raise ValueError("log_return column missing")
    
    df = df.sort_values('date').reset_index(drop=True)

    rolling = df['log_return'].rolling(21)

    df['rolling_mean_21'] = rolling.mean()
    df['rolling_std_21'] = rolling.std()
    df['rolling_skew_21'] = rolling.skew()

    return df

def compute_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:

    if df is None or df.empty:
        return df

    if "close" not in df.columns:
        raise ValueError("close column missing")

    df = df.sort_values("date").reset_index(drop=True)

    delta = df["close"].diff()
    
    gain = delta.clip(lower=0)   
    loss = (-delta).clip(lower=0)   

    avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()

    rs = avg_gain / avg_loss

    # Step 7: compute RSI
    df[f"rsi_{window}"] = 100 - (100 / (1 + rs))  

    return df

def compute_bollinger(df: pd.DataFrame, window: int = 20, num_std: float = 2.0) -> pd.DataFrame:

    rolling_mean_20 = df['close'].rolling(window).mean()
    rolling_std_20 = df['close'].rolling(window).std()

    upper_band = rolling_mean_20 + (num_std * rolling_std_20)
    lower_band = rolling_mean_20 - (num_std * rolling_std_20)
    close = df['close']
    bb_pct_b = (close - lower_band) / (upper_band - lower_band)

    df['bb_pct_b'] = bb_pct_b

    return df

def compute_volume_ratio(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:

    rolling_avg = df['volume'].rolling(window).mean().shift(1)

    df['volume_ratio'] = df['volume'] / rolling_avg

    return df

def write_features(session, df: pd.DataFrame) -> None:
    cols_to_drop = ["open", "high", "low", "close", "volume"]
    df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
    df = df.dropna()
    if df.empty:
        return
    records = df.to_dict(orient="records")

    try:
        insert_features(session, records)
        print(f"Inserted {len(records)} feature rows")
    except Exception as e:
        print(f'Error: {e}')

def main() -> None:

    with get_session() as session:
        tickers = get_all_tickers(session)
        for ticker in tickers:
            try:
                df = fetch_price_data(ticker, session, limit=500)
                df = compute_log_returns(df)
                df = compute_lag_features(df)
                df = compute_rolling_stats(df)
                df = compute_rsi(df)
                df = compute_bollinger(df)
                df = compute_volume_ratio(df)
                write_features(session, df)
                print(f"Done: {ticker}")
            except Exception as e:
                print(f"Failed {ticker}: {e}")
                continue

if __name__ == "__main__":
    main()