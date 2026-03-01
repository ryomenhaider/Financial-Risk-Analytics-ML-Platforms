import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import APIRouter, HTTPException
from typing import List
from config.logging_config import get_logger
from database.crud import get_forecasts as fetch_forcast
from api.schemas import ForecastResponse
from database.connection import get_session

logger = get_logger(__name__)
router = APIRouter()

@router.get("/{ticker}", response_model=list[ForecastResponse])
async def get_forcast(ticker:str, horizon: int = 30 ):
    with get_session() as session:
        try:
            row = fetch_forcast(session, ticker, horizon_days=horizon)
            if not row:
                raise HTTPException(status_code=404, detail=f'No forcast for {ticker}')
            return row
        except HTTPException:
            raise  
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error") 


@router.get('/compare')
async def compare_forecast(tickers:str, horizon: int = 30):
    with get_session() as session:
        try:
            rows = {}
            tickers = tickers.split(',')
            if not tickers:
                raise HTTPException(status_code=404, detail='Say Something!')
            for ticker in tickers:
                row = fetch_forcast(session, ticker, horizon_days=horizon)
                if not row:
                    raise HTTPException(status_code=404, detail=f"{ticker} Not found")
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