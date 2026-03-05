from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import text

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database.models import (
    MarketData, CryptoPrice, EconomicIndicator,
    NewsSentiment, Anomaly, Forecast, PortfolioWeight, ModelRun, Features
)


def insert_market_data(session: Session, rows: list[dict]) -> None:
    stmt = insert(MarketData).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["ticker", "date"])
    session.execute(stmt)
    session.commit()


def get_latest_prices(session: Session, ticker: str, limit: int = 100) -> list[MarketData]:
    return (
        session.query(MarketData)
        .filter(MarketData.ticker == ticker)
        .order_by(MarketData.date.desc())
        .limit(limit)
        .all()
    )

def get_all_tickers(session: Session) -> list[str]:
    rows = session.query(MarketData.ticker).distinct().all()
    return [row[0] for row in rows]

def insert_crypto_prices(session: Session, rows: list[dict]) -> None:
    stmt = insert(CryptoPrice).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["symbol", "date"])
    session.execute(stmt)
    session.commit()


def get_latest_crypto(session: Session, symbol: str, limit: int = 100) -> list[CryptoPrice]:
    return (
        session.query(CryptoPrice)
        .filter(CryptoPrice.symbol == symbol)
        .order_by(CryptoPrice.date.desc())
        .limit(limit)
        .all()
    )


def insert_economic_indicators(session: Session, rows: list[dict]) -> None:
    stmt = insert(EconomicIndicator).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["series_id", "date"])
    session.execute(stmt)
    session.commit()


def get_indicator(session: Session, series_id: str, limit: int = 100) -> list[EconomicIndicator]:
    return (
        session.query(EconomicIndicator)
        .filter(EconomicIndicator.series_id == series_id)
        .order_by(EconomicIndicator.date.desc())
        .limit(limit)
        .all()
    )


def insert_sentiment(session: Session, rows: list[dict]) -> None:
    session.bulk_insert_mappings(NewsSentiment, rows)
    session.commit()


def get_sentiment(session: Session, ticker: str, limit: int = 50) -> list[NewsSentiment]:
    from datetime import datetime, timedelta
    
    # If limit <= 90, treat it as days; otherwise as row limit
    if limit <= 90:
        cutoff_date = datetime.utcnow() - timedelta(days=limit)
        return (
            session.query(NewsSentiment)
            .filter(NewsSentiment.ticker == ticker)
            .filter(NewsSentiment.published_at >= cutoff_date)
            .order_by(NewsSentiment.published_at.desc())
            .all()
        )
    else:
        # For limits > 90, treat as actual row limit
        return (
            session.query(NewsSentiment)
            .filter(NewsSentiment.ticker == ticker)
            .order_by(NewsSentiment.published_at.desc())
            .limit(limit)
            .all()
        )

def insert_anomaly(session: Session, rows: list[dict]) -> None:
    session.bulk_insert_mappings(Anomaly, rows)
    session.commit()

def get_latest_anomaly(session: Session) -> Anomaly:
    return (
        session.query(Anomaly)
        .order_by(Anomaly.created_at.desc())
        .first()
    )

def get_anomalies(session: Session, ticker: str, limit: int = 30) -> list[Anomaly]:
    return (
        session.query(Anomaly)
        .filter(Anomaly.ticker == ticker)
        .order_by(Anomaly.date.desc())
        .limit(limit)
        .all()
    )


def insert_forecasts(session: Session, rows: list[dict]) -> None:
    session.bulk_insert_mappings(Forecast, rows)
    session.commit()


def get_forecasts(session: Session, ticker: str, horizon_days: int = 30) -> list[Forecast]:
    return (
        session.query(Forecast)
        .filter(Forecast.ticker == ticker)
        .filter(Forecast.horizon_days == horizon_days)
        .order_by(Forecast.forecast_date.asc())
        .all()
    )


def upsert_portfolio_weights(session: Session, rows: list[dict]) -> None:
    """
    ✅ FIXED: Delete existing rows for this method first, then insert fresh.
    Previous bulk_insert_mappings was appending duplicates and get_latest_weights
    was only returning the last millisecond's rows (one ticker).
    """
    if not rows:
        return
    method = rows[0].get("method")
    if method:
        session.execute(
            text("DELETE FROM portfolio_weights WHERE method = :method"),
            {"method": method}
        )
    session.bulk_insert_mappings(PortfolioWeight, rows)
    session.commit()


def get_latest_weights(session: Session) -> list[PortfolioWeight]:
    """
    ✅ FIXED: Get the latest calculated_at per method, then return all
    rows matching those timestamps. Previously grabbed only the single
    latest timestamp across all methods — missed every other method's rows
    since each method saves at a different millisecond.
    """
    # Get the most recent calculated_at for each method
    subquery = (
        session.query(
            PortfolioWeight.method,
            text("MAX(calculated_at) as max_ts")
        )
        .group_by(PortfolioWeight.method)
        .subquery()
    )

    results = (
        session.query(PortfolioWeight)
        .join(
            subquery,
            (PortfolioWeight.method == subquery.c.method) &
            (PortfolioWeight.calculated_at == subquery.c.max_ts)
        )
        .order_by(PortfolioWeight.method, PortfolioWeight.ticker)
        .all()
    )
    return results


def insert_model_run(session: Session, row: dict) -> None:
    session.add(ModelRun(**row))
    session.commit()


def get_model_runs(session: Session, model_name: str) -> list[ModelRun]:
    return (
        session.query(ModelRun)
        .filter(ModelRun.model_name == model_name)
        .order_by(ModelRun.trained_at.desc())
        .all()
    )

def insert_features(session: Session, rows: list[dict]) -> None:
    stmt = insert(Features).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["ticker", "date"])
    session.execute(stmt)
    session.commit()


def get_features(session: Session, ticker: str, limit: int = 100) -> list[Features]:
    return (
        session.query(Features)
        .filter(Features.ticker == ticker)
        .order_by(Features.date.desc())
        .limit(limit)
        .all()
    )


if __name__ == "__main__":
    from database.connection import get_session

    with get_session() as session:
        insert_crypto_prices(session, [
            {"symbol": "BTC", "date": date(2024, 1, 1), "close": 42000.0}
        ])
        results = get_latest_crypto(session, symbol='BTC', limit=5)
        for row in results:
            print(f"COIN: {row.symbol} DATE: {row.date} CLOSE: {row.close}")