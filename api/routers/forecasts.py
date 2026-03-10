import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import APIRouter, HTTPException
from typing import List
from config.logging_config import get_logger
from database.crud import get_forecasts as fetch_forecast
from api.schemas import ForecastResponse
from database.connection import get_session

logger = get_logger(__name__)
router = APIRouter()

# FIX: /compare and /accuracy must be declared BEFORE /{ticker}
# otherwise FastAPI matches "compare"/"accuracy" as ticker values

@router.get('/compare')
async def compare_forecast(tickers: str, horizon: int = 30):
    with get_session() as session:
        try:
            ticker_list = [t.strip() for t in tickers.split(',') if t.strip()]
            if not ticker_list:
                raise HTTPException(status_code=400, detail='Provide at least one ticker')
            rows = {}
            for ticker in ticker_list:
                row = fetch_forecast(session, ticker, horizon_days=horizon)
                if not row:
                    raise HTTPException(status_code=404, detail=f"{ticker} not found")
                rows[ticker] = row[0]
            return rows
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")


@router.get('/accuracy')
async def forecast_accuracy():
    return {"message": "coming soon"}


@router.get("/{ticker}", response_model=List[ForecastResponse])
async def get_forecast(ticker: str, horizon: int = 30):
    with get_session() as session:
        try:
            row = fetch_forecast(session, ticker, horizon_days=horizon)
            if not row:
                raise HTTPException(status_code=404, detail=f'No forecast for {ticker}')
            return row
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")