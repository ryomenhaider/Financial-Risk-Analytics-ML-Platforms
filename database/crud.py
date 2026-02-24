from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

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


def get_anomalies(session: Session, ticker: str) -> list[Anomaly]:
    return (
        session.query(Anomaly)
        .filter(Anomaly.ticker == ticker)
        .order_by(Anomaly.date.desc())
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
    session.bulk_insert_mappings(PortfolioWeight, rows)
    session.commit()


def get_latest_weights(session: Session) -> list[PortfolioWeight]:
    latest = (
        session.query(PortfolioWeight.calculated_at)
        .order_by(PortfolioWeight.calculated_at.desc())
        .first()
    )
    if not latest:
        return []
    return (
        session.query(PortfolioWeight)
        .filter(PortfolioWeight.calculated_at == latest[0])
        .all()
    )


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
            print(f'''
                  COIN: {row.symbol}
                  DATE:  {row.date} 
                  CLOSE: {row.close}''')

