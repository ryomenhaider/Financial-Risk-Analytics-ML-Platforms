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
RISK_FREE_RATE = 0.05
TRADING_DAYS = 252


def neg_sharpe(weights, mean_returns, cov_matrix):
    port_returns   = np.sum(mean_returns * weights) * TRADING_DAYS
    port_volatility = np.sqrt(weights @ cov_matrix @ weights) * np.sqrt(TRADING_DAYS)
    if port_volatility == 0:
        return 0
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
        df = pd.read_sql(sql=text(query), con=conn, params={"tickers": tickers})
    df = df.pivot(index="date", columns="ticker", values="close")
    return df


def load_sentiment(tickers: list) -> dict:
    query = """
        SELECT ticker, score
        FROM news_sentiment
        WHERE ticker = ANY(:tickers)
    """
    with engine.connect() as conn:
        df = pd.read_sql(sql=text(query), con=conn, params={"tickers": tickers})

    sentiment = df.groupby("ticker")["score"].mean().to_dict()

    # ✅ FIX: fill missing tickers with 0 so black_litterman never gets a KeyError
    for t in tickers:
        if t not in sentiment:
            logger.warning(f"No sentiment for {t}, defaulting to 0")
            sentiment[t] = 0.0

    return sentiment


def compute_returns(prices_df: pd.DataFrame) -> pd.DataFrame:
    returns = np.log(prices_df / prices_df.shift(1))
    return returns.dropna()


def mpt_optimize(returns_df: pd.DataFrame) -> np.ndarray:
    mean_returns = returns_df.mean()
    cov_matrix   = returns_df.cov()
    n            = len(returns_df.columns)

    result = minimize(
        neg_sharpe,
        x0=np.ones(n) / n,
        args=(mean_returns, cov_matrix),
        method="SLSQP",
        bounds=[(0, 1)] * n,
        constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1}],
    )
    return result.x


def black_litterman(returns_df: pd.DataFrame, sentiment: dict) -> np.ndarray:
    n            = len(returns_df.columns)
    cov_matrix   = returns_df.cov()
    equal_weight = np.ones(n) / n
    implied_returns = 2.5 * cov_matrix @ equal_weight

    # ✅ FIX: safe lookup — sentiment is now guaranteed to have all tickers
    our_views   = np.array([sentiment.get(t, 0.0) for t in returns_df.columns]) * 0.05
    bl_returns  = implied_returns + 0.05 * our_views

    result = minimize(
        neg_sharpe,
        x0=equal_weight,
        args=(bl_returns, cov_matrix),
        method="SLSQP",
        bounds=[(0, 1)] * n,
        constraints=[{"type": "eq", "fun": lambda w: np.sum(w) - 1}],
    )
    return result.x


def kelly_criterion(returns_df: pd.DataFrame) -> np.ndarray:
    b     = returns_df[returns_df > 0].mean() / returns_df[returns_df < 0].mean().abs()
    p     = (returns_df > 0).mean()
    q     = 1 - p
    kelly = (b * p - q) / b
    kelly = kelly.clip(lower=0)
    total = kelly.sum()
    if total == 0:
        return np.ones(len(returns_df.columns)) / len(returns_df.columns)
    return (kelly / total).values


def blend_weights(mpt_w, bl_w, kelly_w) -> np.ndarray:
    final = 0.4 * mpt_w + 0.4 * bl_w + 0.2 * kelly_w
    return final / final.sum()


def save_weights(weights: np.ndarray, tickers: list, method: str) -> None:
    if len(weights) == 0:
        logger.error("No weights to save")
        return

    rows = [
        {
            "ticker":        tickers[i],
            "weight":        float(weights[i]),
            "method":        method,
            "calculated_at": datetime.now(timezone.utc),
        }
        for i in range(len(tickers))
    ]

    with get_session() as session:
        try:
            upsert_portfolio_weights(session, rows)
            session.commit()
            logger.info(f"Saved {method} weights for {tickers}")
        except Exception as e:
            logger.error(f"Error saving {method} weights: {e}")
            raise
        finally:
            session.close()


def run() -> None:
    logger.info(f"Starting portfolio optimization for {TICKERS}")

    prices_df = load_prices(TICKERS)
    if prices_df.empty:
        logger.error("No price data found — aborting")
        return

    # Drop tickers with insufficient data
    prices_df = prices_df.dropna(axis=1, thresh=30)
    active_tickers = list(prices_df.columns)
    if len(active_tickers) < 2:
        logger.error(f"Not enough tickers with data: {active_tickers}")
        return

    logger.info(f"Optimizing with tickers: {active_tickers}")

    sentiment  = load_sentiment(active_tickers)
    # ✅ FIX: was `return_df` (typo) — crashed silently leaving only GOOGL saved
    returns_df = compute_returns(prices_df)

    mpt_w   = mpt_optimize(returns_df)
    bl_w    = black_litterman(returns_df, sentiment)
    kelly_w = kelly_criterion(returns_df)
    blended = blend_weights(mpt_w, bl_w, kelly_w)

    save_weights(mpt_w,   active_tickers, "mpt")
    save_weights(bl_w,    active_tickers, "black_litterman")
    save_weights(kelly_w, active_tickers, "kelly")
    save_weights(blended, active_tickers, "Blended")

    logger.info("Portfolio optimization complete")


if __name__ == "__main__":
    run()