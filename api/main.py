import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from config.logging_config import get_logger
from api.routers.prices import router as prices_router
from api.routers.anomalies import router as anomalies_router
from api.routers.forecasts import router as forecasts_router
from api.routers.portfolio import router as portfolio_router
from api.routers.sentiment import router as sentiment_router

logger = get_logger(__name__)

app = FastAPI(
    title="Financial Intelligence Platform",
    description="A production-grade system that ingests real-time and historical financial data, detects anomalies, forecasts price movements, and visualizes everything in a Bloomberg-style dashboard.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    response.headers["X-Process-Time"] = f"{duration:.4f}s"
    logger.info(f"{request.method} {request.url.path} | {response.status_code} | {duration:.4f}s")
    return response

@app.on_event("startup")
async def startup():
    try:
        from database.connection import test_connection
        db_ok = test_connection()
        if db_ok:
            logger.info(f"FIP API v{app.version} started successfully | Database: connected")
        else:
            logger.warning(f"FIP API v{app.version} started | Database: unreachable")
    except Exception as e:
        logger.error(f"Startup error: {e}")

@app.get("/health")
async def health():
    from database.connection import test_connection
    db_ok = test_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
        "version": app.version
    }

app.include_router(prices_router, prefix="/prices", tags=["Prices"])
app.include_router(anomalies_router, prefix="/anomalies", tags=["Anomalies"])
app.include_router(forecasts_router, prefix="/forecasts", tags=["Forecasts"])
app.include_router(portfolio_router, prefix="/portfolio", tags=["Portfolio"])
app.include_router(sentiment_router, prefix="/sentiment", tags=["Sentiment"])

if __name__ == "__main__":
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)