"""
Airflow DAG: Weekly Model Retraining
Runs every Sunday. Checks drift_detector output.
Runs train_pipeline if drift detected or for scheduled weekly retrain.
Promotes new model if CV MAE improves.

Dependencies:
  - mlops/drift_detector.py
  - ml/train_pipeline.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from airflow.sdk import dag, task
from datetime import datetime
from config.logging_config import get_logger

logger = get_logger(__name__)

TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']


@dag(
    schedule="0 2 * * 0",  # Every Sunday at 2 AM
    start_date=datetime(2026, 2, 27),
    catchup=False,
    tags=["ml", "retrain", "drift"]
)
def model_retraining():
    """
    Weekly model retraining pipeline with drift detection.
    
    Flow:
    1. Check data drift for all tickers
    2. Decide if retrain is needed (drift detected or weekly schedule)
    3. Run training pipeline if needed
    4. Compare metrics and promote if improved
    """

    @task
    def check_drift():
        """
        Check data drift for all tickers.
        Returns dict with drift status per ticker.
        """
        from mlops.drift_detector import detect_drift
        
        logger.info("Starting drift detection check...")
        drift_results = {}
        
        for ticker in TICKERS:
            try:
                result = detect_drift(ticker)
                if result is None:
                    drift_results[ticker] = {
                        'has_drift': False,
                        'error': 'Insufficient data'
                    }
                else:
                    drift_results[ticker] = {
                        'has_drift': result['has_drift_alert'],
                        'drifted_features': result['drifted_features'],
                        'feature_count': len(result['features']),
                        'timestamp': result['timestamp']
                    }
                    
                    if result['has_drift_alert']:
                        logger.warning(f"[{ticker}] Drift detected: {result['drifted_features']}")
                    else:
                        logger.info(f"[{ticker}] No drift detected")
            except Exception as e:
                logger.error(f"[{ticker}] Drift detection failed: {e}")
                drift_results[ticker] = {
                    'has_drift': False,
                    'error': str(e)
                }
        
        logger.info(f"Drift check complete. Results: {drift_results}")
        return drift_results

    @task
    def decide_retrain(drift_results: dict):
        """
        Decide if retraining is needed.
        
        Criteria for retrain:
        1. Any ticker has detected drift
        2. It's a scheduled weekly retrain (always on Sunday)
        
        Returns: dict with decision and reasons
        """
        # Check if any drift detected
        tickers_with_drift = [
            ticker for ticker, result in drift_results.items()
            if result.get('has_drift', False)
        ]
        
        # It's Sunday (scheduled retrain), so always retrain
        should_retrain = True
        
        reason = "Scheduled weekly retrain"
        if tickers_with_drift:
            reason = f"Drift detected in {len(tickers_with_drift)} ticker(s): {tickers_with_drift}"
        
        decision = {
            'should_retrain': should_retrain,
            'reason': reason,
            'tickers_with_drift': tickers_with_drift,
            'all_tickers': TICKERS
        }
        
        logger.info(f"Retrain decision: {should_retrain} — {reason}")
        return decision

    @task
    def run_training(decision: dict):
        """
        Run the training pipeline for all tickers.
        Collects and returns metrics for comparison.
        
        Returns: dict with training results and metrics
        """
        from ml.train_pipeline import run_pipeline_with_metrics
        
        if not decision['should_retrain']:
            logger.info("Skipping training — no retrain needed")
            return {
                'trained': False,
                'reason': 'No retrain needed'
            }
        
        logger.info(f"Starting training pipeline for {len(decision['all_tickers'])} tickers...")
        
        try:
            # Run the full pipeline
            training_results = run_pipeline_with_metrics(decision['all_tickers'])
            
            logger.info(f"Training complete. Results: {training_results}")
            return {
                'trained': True,
                'results': training_results,
                'reason': decision['reason']
            }
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {
                'trained': False,
                'error': str(e),
                'reason': decision['reason']
            }

    @task
    def compare_and_promote(training_result: dict):
        """
        Compare new model metrics against the previous best.
        Promote new models if CV MAE improved.
        
        Returns: promotion results
        """
        from ml.model_registry import load_best_model, promote_to_production
        import mlflow
        
        if not training_result.get('trained', False):
            logger.info("Skipping promotion — no new models trained")
            return {
                'promoted': False,
                'reason': 'No trained models'
            }
        
        logger.info("Comparing metrics and promoting models...")
        promotion_results = {
            'promoted_models': [],
            'skipped_models': [],
            'errors': []
        }
        
        results = training_result.get('results', {})
        
        for ticker, metrics in results.items():
            try:
                # Get the new model's CV MAE from training results
                new_mae = metrics.get('cv_mae')
                
                if new_mae is None:
                    logger.warning(f"[{ticker}] No MAE metric found")
                    promotion_results['skipped_models'].append(ticker)
                    continue
                
                # Load best previous model's metrics from MLflow
                mlflow.set_experiment('forecaster')
                runs = mlflow.search_runs(
                    experiment_names=['forecaster'],
                    filter_string=f"tags.ticker = '{ticker}'",
                    order_by=["metrics.mae ASC"],
                    max_results=1
                )
                
                if runs.empty:
                    # No previous model, always promote the first one
                    logger.info(f"[{ticker}] No previous model found, promoting new model")
                    # Get the latest run ID from results
                    if 'run_id' in metrics:
                        promote_to_production(f'forecaster_{ticker}', metrics['run_id'])
                        promotion_results['promoted_models'].append(ticker)
                    continue
                
                previous_mae = runs.iloc[0]['metrics.mae']
                improvement = ((previous_mae - new_mae) / previous_mae) * 100
                
                if improvement > 0:
                    logger.info(f"[{ticker}] MAE improved by {improvement:.2f}% ({previous_mae:.4f} → {new_mae:.4f})")
                    if 'version' in metrics:
                        promote_to_production(f'forecaster_{ticker}', metrics['version'])
                    promotion_results['promoted_models'].append(ticker)
                else:
                    logger.info(f"[{ticker}] MAE degraded by {abs(improvement):.2f}%, keeping previous model")
                    promotion_results['skipped_models'].append(ticker)
            
            except Exception as e:
                logger.error(f"[{ticker}] Promotion check failed: {e}")
                promotion_results['errors'].append({'ticker': ticker, 'error': str(e)})
        
        logger.info(f"Promotion complete: {len(promotion_results['promoted_models'])} promoted, "
                   f"{len(promotion_results['skipped_models'])} skipped")
        
        return promotion_results

    @task
    def finalize_report(
        drift_check: dict,
        retrain_decision: dict,
        training_result: dict,
        promotion_result: dict
    ):
        """
        Finalize and log the complete retrain cycle report.
        """
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'drift_check': drift_check,
            'retrain_decision': retrain_decision,
            'training': training_result,
            'promotion': promotion_result,
            'status': 'success' if training_result.get('trained', False) else 'skipped'
        }
        
        logger.info(f"\n{'='*70}")
        logger.info("WEEKLY MODEL RETRAIN REPORT")
        logger.info(f"{'='*70}")
        logger.info(f"Status: {report['status'].upper()}")
        logger.info(f"Reason: {retrain_decision['reason']}")
        
        if drift_check:
            drift_count = sum(1 for r in drift_check.values() if r.get('has_drift', False))
            logger.info(f"Tickers with Drift: {drift_count}/{len(TICKERS)}")
        
        if training_result.get('trained', False):
            logger.info(f"Models Trained: {len(training_result['results'])} tickers")
        
        if promotion_result.get('promoted_models'):
            logger.info(f"Models Promoted: {promotion_result['promoted_models']}")
        
        logger.info(f"{'='*70}\n")
        
        return report

    # Define task dependencies
    drift_result = check_drift()
    retrain_decision = decide_retrain(drift_result)
    training_result = run_training(retrain_decision)
    promotion_result = compare_and_promote(training_result)
    final_report = finalize_report(drift_result, retrain_decision, training_result, promotion_result)
    
    # Set dependency chain
    drift_result >> retrain_decision >> training_result >> promotion_result >> final_report


# Instantiate the DAG
model_retraining()
