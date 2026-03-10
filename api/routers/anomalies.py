import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi import APIRouter, HTTPException
from typing import List
from config.logging_config import get_logger
from database.crud import get_anomalies as fetch_anomalies, get_latest_anomaly as fetch_latest_anomaly
from api.schemas import AnomalyResponse
from database.connection import get_session

logger = get_logger(__name__)
router = APIRouter()

# FIX: /latest and /detect/{ticker} declared before implicit path params
# to avoid route shadowing

@router.get("/latest", response_model=AnomalyResponse)
async def get_latest_anomaly_endpoint():
    with get_session() as session:
        try:
            row = fetch_latest_anomaly(session)
            if not row:
                raise HTTPException(status_code=404, detail="No latest anomaly found")
            return row
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")


# GET /anomalies?ticker=AAPL&days=30
@router.get("/", response_model=List[AnomalyResponse])
async def get_anomalies(ticker: str, days: int = 30):
    with get_session() as session:
        try:
            rows = fetch_anomalies(session, ticker, limit=days)
            if not rows:
                return []
            return rows 
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Error: {e}')
            raise HTTPException(status_code=500, detail="Internal server error")


# POST /anomalies/detect/{ticker} — trigger on-demand detection
@router.post("/detect/{ticker}")
async def detect_anomalies(ticker: str):
    try:
        from ml.anomaly_detector import run
        run(ticker)
        return {"status": "ok", "ticker": ticker, "message": f"Anomaly detection completed for {ticker}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error: {e}')
        raise HTTPException(status_code=500, detail="Internal server error")