import sys
from pathlib import Path
sys.path.insert(0, str(Path(__name__).resolve().parent[1]))

import pandas as pd
import numpy as np
from database.connection import get_session
from database.crud import get_latest_prices
import scipy as sp


def fetch_price_data(ticker:str, limit: int = 100) -> pd.DataFrame:
    session = get_session()
    price = get_latest_prices(session, ticker, limit)
    return price

def compute_log_return(ticker:str, limit: int=100) -> pd.DataFrame:

    prices = fetch_price_data(ticker, limit)
    
    if prices is None:
        return 
    prices = prices.sort_values('timestamps').reset_index(drop=True)

    prices['log_return'] = np.log(prices['price']/prices['price'].shift(1))

    return prices

def compute_lag_features(ticker: str, limit:int = 100) -> pd.DataFrame:
    
    log_values = compute_log_return(ticker, limit)

    if log_values is None:
        return
    log_values = log_values.sort_values('timestamps').reset_index(drop=True)

    log_values['lag_1d'] = log_values['log_returns'].shift(1)
    log_values['lag_5d'] = log_values['log_returns'].shift(5)
    log_values['lag_21d'] = log_values['log_returns'].shift(21)
    log_values['lag_63d'] = log_values['log_returns'].shift(63)

    return log_values

def compute_rolling_stats(ticker: str, limit:int = 100) -> pd.DataFrame:
    
    log_values = compute_log_return(ticker, limit)

    required_col = "log_return"
    if required_col not in log_values.columns:
        raise ValueError("log_return column missing")
    
    log_values = log_values.sort_values('timestamps').reset_index(drop=True)

    rollings = [5,21, 63]

    for rolling in rollings:
        rolling = log_values['log_return'].rolling(rollings=rolling)

        log_values['roll_mean_{rolling}d'] = rolling.mean()
        log_values['roll_std_{rolling}d'] = rolling.std()
        log_values['roll_skew_{rolling}d'] = rolling.skew()

    return log_values

def compute_rsi(df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    # to be continued
    return df