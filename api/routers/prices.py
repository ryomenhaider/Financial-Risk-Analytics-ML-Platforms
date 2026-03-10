import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import APIRouter, HTTPException
from typing import List
from config.logging_config import get_logger
from database.crud import get_latest_prices
from api.schemas import MarketDataResponse
from database.connection import get_session

logger = get_logger(__name__)
router = APIRouter()

# FIX: /compare MUST be declared before /{ticker} and /{ticker}/history
# otherwise FastAPI matches "compare" as a ticker value and this route is never reached
@router.get("/compare")
async def compare_tickers(tickers: str):
    with get_session() as session:
        try:
            result = {}
            ticker_list = [t.strip() for t in tickers.split(',') if t.strip()]
            if not ticker_list:
                raise HTTPException(status_code=400, detail='Provide at least one ticker')
            for ticker in ticker_list:
                row = get_latest_prices(session, ticker, limit=1)
                if not row:
                    raise HTTPException(status_code=404, detail=f"{ticker} not found")
                result[ticker] = {
                    "ticker":     row[0].ticker,
                    "date":       row[0].date.isoformat() if hasattr(row[0].date, 'isoformat') else str(row[0].date),
                    "open":       float(row[0].open)  if row[0].open  else None,
                    "high":       float(row[0].high)  if row[0].high  else None,
                    "low":        float(row[0].low)   if row[0].low   else None,
                    "close":      float(row[0].close),
                    "volume":     row[0].volume,
                    "created_at": row[0].created_at.isoformat() if hasattr(row[0].created_at, 'isoformat') else str(row[0].created_at),
                }
            return result
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{ticker}", response_model=MarketDataResponse)
async def get_latest_price(ticker: str):
    with get_session() as session:
        try:
            rows = get_latest_prices(session, ticker, limit=1)
            if not rows:
                raise HTTPException(status_code=404, detail=f'{ticker} not found')
            return rows[0]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{ticker}/history")
async def get_price_history(ticker: str, limit: int = 90):
    with get_session() as session:
        try:
            rows = get_latest_prices(session, ticker, limit)
            if not rows:
                raise HTTPException(status_code=404, detail=f'{ticker} not found')
            return [
                {
                    "ticker":     row.ticker,
                    "date":       row.date.isoformat() if hasattr(row.date, 'isoformat') else str(row.date),
                    "open":       float(row.open)  if row.open  else None,
                    "high":       float(row.high)  if row.high  else None,
                    "low":        float(row.low)   if row.low   else None,
                    "close":      float(row.close),
                    "volume":     row.volume,
                    "created_at": row.created_at.isoformat() if hasattr(row.created_at, 'isoformat') else str(row.created_at),
                }
                for row in rows
            ]
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")