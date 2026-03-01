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

@router.get("/{ticker}", response_model=MarketDataResponse)
async def get_latest_price(ticker: str):
    with get_session() as session:
        try:
            rows = get_latest_prices(session, ticker, limit=1)
            if not rows:
                raise HTTPException(status_code=404,detail=f'{ticker} not found' )
            return rows[0]
        except HTTPException:
            raise  
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error") 

@router.get("/{ticker}/history", response_model=MarketDataResponse)
async def get_price_history(ticker: str, limit: int = 90):
    with get_session() as session:
        try:
            rows = get_latest_prices(session, ticker, limit)
            if not rows:
                raise HTTPException(status_code=404, detail=f'{ticker} not found')
            return {
                ticker: rows
            }
        except HTTPException:
            raise  
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")  

@router.get("/compare", response_model=MarketDataResponse)
async def compare_tickers(tickers: str):
    with get_session() as session:
        try:
            rows = {}
            tickers = tickers.split(',')
            if not tickers:
                raise HTTPException(status_code=404, detail='Say Something!')
            for ticker in tickers:
                row = get_latest_prices(session, ticker, limit=1)
                if not row:
                    raise HTTPException(status_code=404, detail=f"{ticker} Not found")
                rows[ticker] = row[0]
            return rows
        except HTTPException:
            raise  
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")  
