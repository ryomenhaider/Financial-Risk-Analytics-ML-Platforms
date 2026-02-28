import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.logging_config import get_logger
import ml.anomaly_detector as anomaly
import ml.forecaster as forecaster
import ml.portfolio_optimizer as portfolio
import ml.sentiment_engine as sentiment
import ml.feature_store as feature_store

logger = get_logger(__name__)

TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']


def run_pipeline() -> None:
    logger.info("Starting full training pipeline...")

    logger.info("Starting full training pipeline...")

    logger.info("Step 1 — Warming up feature store...")
    for ticker in TICKERS:
        feature_store.get_features(ticker)

    logger.info("Step 2 — Running anomaly detection...")
    for ticker in TICKERS:
        anomaly.run(ticker)

    logger.info("Step 3 — Running forecasts...")
    for ticker in TICKERS:
        forecaster.run(ticker)

    logger.info("Step 4 — Running sentiment signals...")
    for ticker in TICKERS:
        sentiment.run(ticker)

    logger.info("Step 5 — Running portfolio optimization...")
    portfolio.run()

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    run_pipeline()