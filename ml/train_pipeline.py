import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.logging_config import get_logger
import ml.anomaly_detector as anomaly
import ml.forecaster as forecaster
import ml.portfolio_optimizer as portfolio
import ml.sentiment_engine as sentiment
import ml.feature_store as feature_store
from ml.model_registry import save_model
import mlflow

logger = get_logger(__name__)

TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']


def run_pipeline() -> None:
    """Legacy pipeline without metrics tracking."""
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


def run_pipeline_with_metrics(tickers: list = None) -> dict:
    """
    Enhanced training pipeline that collects and returns metrics.
    
    Used by dag_retrain.py to track model performance and decide on promotion.
    
    Args:
        tickers: List of tickers to train. Defaults to TICKERS.
    
    Returns:
        dict mapping ticker -> {cv_mae, rmse, version, run_id}
    """
    if tickers is None:
        tickers = TICKERS
    
    logger.info(f"Starting enhanced training pipeline for {len(tickers)} tickers...")
    metrics_dict = {}
    
    try:
        # Step 1: Warm up feature store
        logger.info(f"Step 1 — Warming up feature store for {len(tickers)} tickers...")
        for ticker in tickers:
            try:
                feature_store.get_features(ticker)
            except Exception as e:
                logger.warning(f"[{ticker}] Feature store warm-up failed: {e}")
        
        # Step 2: Anomaly detection
        logger.info("Step 2 — Running anomaly detection...")
        for ticker in tickers:
            try:
                anomaly.run(ticker)
            except Exception as e:
                logger.warning(f"[{ticker}] Anomaly detection failed: {e}")
        
        # Step 3: Forecasting with metrics collection
        logger.info("Step 3 — Running forecasts with CV metrics...")
        for ticker in tickers:
            try:
                # Load data and compute cross-validation metrics
                df = forecaster.load_data(ticker)
                
                if df.empty:
                    logger.warning(f"[{ticker}] No data for forecasting")
                    metrics_dict[ticker] = {
                        'cv_mae': None,
                        'rmse': None,
                        'error': 'No data'
                    }
                    continue
                
                # Run walk-forward CV on both horizons and average
                cv_metrics_30 = forecaster.walk_forward_cv(df, horizon=30, n_splits=5)
                cv_metrics_90 = forecaster.walk_forward_cv(df, horizon=90, n_splits=5)
                
                avg_mae = (cv_metrics_30['mae'] + cv_metrics_90['mae']) / 2
                avg_rmse = (cv_metrics_30['rmse'] + cv_metrics_90['rmse']) / 2
                
                logger.info(f"[{ticker}] CV Metrics — MAE: {avg_mae:.4f}, RMSE: {avg_rmse:.4f}")
                
                # Save model to MLflow registry
                try:
                    mlflow.set_experiment('forecaster')
                    with mlflow.start_run(run_name=f"forecaster_{ticker}") as run:
                        mlflow.set_tag("ticker", ticker)
                        mlflow.log_metrics({
                            'mae': avg_mae,
                            'rmse': avg_rmse,
                            'average_of_30_90_horizons': True
                        })
                        
                        metrics_dict[ticker] = {
                            'cv_mae': avg_mae,
                            'rmse': avg_rmse,
                            'run_id': run.info.run_id,
                            'version': str(run.info.run_id),  # Use run_id as version for MLflow
                        }
                        
                        logger.info(f"[{ticker}] Logged to MLflow — run_id: {run.info.run_id}")
                except Exception as e:
                    logger.error(f"[{ticker}] Failed to save to MLflow: {e}")
                    metrics_dict[ticker] = {
                        'cv_mae': avg_mae,
                        'rmse': avg_rmse,
                        'error': f'MLflow save failed: {e}'
                    }
                
                # Run actual forecasting
                forecaster.run(ticker)
            
            except Exception as e:
                logger.error(f"[{ticker}] Forecasting failed: {e}")
                metrics_dict[ticker] = {
                    'cv_mae': None,
                    'rmse': None,
                    'error': str(e)
                }
        
        # Step 4: Sentiment signals
        logger.info("Step 4 — Running sentiment signals...")
        for ticker in tickers:
            try:
                sentiment.run(ticker)
            except Exception as e:
                logger.warning(f"[{ticker}] Sentiment analysis failed: {e}")
        
        # Step 5: Portfolio optimization
        logger.info("Step 5 — Running portfolio optimization...")
        try:
            portfolio.run()
        except Exception as e:
            logger.warning(f"Portfolio optimization failed: {e}")
        
        logger.info(f"Enhanced pipeline complete. Metrics collected for {len(metrics_dict)} tickers.")
        return metrics_dict
    
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        return {'error': str(e)}


if __name__ == "__main__":
    # Run with metrics if requested via environment variable
    import os
    if os.getenv('WITH_METRICS', '').lower() == 'true':
        results = run_pipeline_with_metrics()
        print("\n" + "="*70)
        print("TRAINING PIPELINE RESULTS")
        print("="*70)
        for ticker, metrics in results.items():
            if ticker != 'error':
                print(f"{ticker}: MAE={metrics.get('cv_mae', 'N/A'):.4f if metrics.get('cv_mae') else 'N/A'}, "
                      f"RMSE={metrics.get('rmse', 'N/A'):.4f if metrics.get('rmse') else 'N/A'}")
    else:
        run_pipeline()