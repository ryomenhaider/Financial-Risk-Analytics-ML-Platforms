import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import APIRouter, HTTPException
from typing import List
from config.logging_config import get_logger
from database.crud import get_sentiment as fetch_sentiment, get_all_tickers
from api.schemas import SentimentResponse
from database.connection import get_session

logger = get_logger(__name__)
router = APIRouter()


@router.get("/heatmap")
async def get_sentiment_heatmap():
    with get_session() as session:
        try:
            tickers = get_all_tickers(session)
            if not tickers:
                raise HTTPException(status_code=404, detail="No tickers found")
            heatmap = {}
            for ticker in tickers:
                rows = fetch_sentiment(session, ticker, limit=1)
                if rows:
                    heatmap[ticker] = rows[0]
            if not heatmap:
                raise HTTPException(status_code=404, detail="No sentiment data found")
            return heatmap
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error fetching sentiment heatmap: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/timeline", response_model=List[SentimentResponse])
async def get_sentiment_timeline(ticker: str, days: int = 30):
    with get_session() as session:
        try:
            rows = fetch_sentiment(session, ticker, limit=days)
            if not rows:
                raise HTTPException(status_code=404, detail=f"No sentiment timeline for {ticker} found")
            return rows
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error fetching sentiment timeline for {ticker}: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{ticker}", response_model=List[SentimentResponse])
async def get_ticker_sentiment(ticker: str, days: int = 30):
    with get_session() as session:
        try:
            rows = fetch_sentiment(session, ticker, limit=days)
            if not rows:
                raise HTTPException(status_code=404, detail=f"No sentiment data for {ticker} found")
            return rows
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error fetching sentiment for {ticker}: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")