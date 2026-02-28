import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sqlalchemy import text
from database.connection import engine, get_session
from database.crud import upsert_portfolio_weights
from config.logging_config import get_logger
from datetime import datetime, timezone

logger = get_logger(__name__)
TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']
RISK_FREE_RATE = 0.05   # 5% annual
TRADING_DAYS = 252       # days in a trading year
def neg_sharpe(weights, mean_returns, cov_matrix):
    port_returns = np.sum(mean_returns * weights ) * TRADING_DAYS
    port_volatility = np.sqrt(weights @ cov_matrix @ weights) * np.sqrt(TRADING_DAYS)
    sharpe = (port_returns - RISK_FREE_RATE) / port_volatility
    return -sharpe

def load_prices(tickers: list) -> pd.DataFrame:
    query = """
            SELECT date, ticker, close
            FROM market_data
            WHERE ticker = ANY(:tickers)
            ORDER BY date ASC
            """
    with engine.connect() as conn:
        df = pd.read_sql(
            sql=text(query),
            con=conn,
            params={'tickers': tickers}
        )
    df = df.pivot(index='date', columns='ticker', values='close')
    return df


def load_sentiment(tickers: list) -> dict:

    query = """
            SELECT ticker, score
            FROM news_sentiment
            WHERE ticker = ANY(:tickers)
            """
    with engine.connect() as conn:
        df = pd.read_sql(
            sql=text(query),
            con=conn,
            params={'tickers': tickers}
        )
    sentiment = df.groupby('ticker')['score'].mean().to_dict()
    return sentiment


def compute_returns(prices_df: pd.DataFrame) -> pd.DataFrame:
    returns = np.log(prices_df / prices_df.shift(1))
    return returns.dropna()

def mpt_optimize(returns_df: pd.DataFrame) -> np.ndarray:
    mean_returns = returns_df.mean()
    cov_matrix = returns_df.cov()
    n = len(returns_df.columns)
    initial_weights = np.ones(n) / n

    result = minimize(
        neg_sharpe,
        x0 = initial_weights,
        args=(mean_returns, cov_matrix),
        method='SLSQP',
        bounds=[(0,1)] * n,
        constraints=[{'type': 'eq', 'fun': lambda w:np.sum(w)-1}]
    )
    return result.x

def black_litterman(returns_df: pd.DataFrame, 
                    sentiment: dict) -> np.ndarray:
    n = len(returns_df.columns)
    cov_matrix = returns_df.cov()
    equal_weight = np.ones(n)/n
    implied_returns = 2.5 * cov_matrix @ equal_weight
    our_views = np.array([sentiment[t] for t in returns_df.columns]) * 0.05
    bl_returns = implied_returns + 0.05 * our_views
    result = minimize(
        neg_sharpe,
        x0 = equal_weight,
        args=(bl_returns, cov_matrix),
        method='SLSQP',
        bounds=[(0,1)] * n,
        constraints=[{'type': 'eq', 'fun': lambda w:np.sum(w)-1}]
    )
    return result.x

    


def kelly_criterion(returns_df: pd.DataFrame) -> np.ndarray:
    b = returns_df[returns_df > 0].mean() / returns_df[returns_df < 0].mean().abs()
    p = (returns_df > 0).mean()
    q = 1 - p
    kelly = (b*p - q) / b 
    kelly = kelly.clip(lower=0)
    kelly = kelly / kelly.sum()
    return kelly.values

def blend_weights(mpt_w: np.ndarray,
                  bl_w: np.ndarray,
                  kelly_w: np.ndarray) -> np.ndarray:
    final = 0.4 * mpt_w + 0.4 * bl_w + 0.2 * kelly_w
    final = final / final.sum()
    return final 

def save_weights(weights: np.ndarray, method: str) -> None:
    
    if len(weights) == 0:
        logger.error(f"No weights")
        return

    rows = [
        {
        'ticker': TICKERS[i],
        'weight': float(weights[i]),
        'method': method, 
        'calculated_at': datetime.now(timezone.utc)
        }
        for i in range(len(TICKERS))
        ]

    with get_session() as session:
        try:
            upsert_portfolio_weights(session, rows)
            session.commit()
            print(f"Weights save to DB")
        except Exception as e:
            print(f"[Error: {e}")
            raise
        finally:
            session.close()

def run() -> None:
    
    prices_df = load_prices(TICKERS)
    sentiment = load_sentiment(TICKERS)

    if prices_df.empty:
        logger.error('No prices')
        return
    if len(sentiment) == 0:
        logger.error('No sentiment')
        return

    return_df = compute_returns(prices_df)
    mpt_w = mpt_optimize(return_df)
    bl_w = black_litterman(return_df, sentiment)
    kelly_w = kelly_criterion(return_df)
    weights = blend_weights(mpt_w, bl_w, kelly_w)

    save_weights(mpt_w,    'mpt')
    save_weights(bl_w,     'black_litterman')
    save_weights(kelly_w,  'kelly')
    save_weights(weights, 'Blended')

    logger.info(f"Optimization complete")



if __name__ == "__main__":
    run()