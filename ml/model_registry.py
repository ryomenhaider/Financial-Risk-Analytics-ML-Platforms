import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mlflow
import mlflow.sklearn
from mlflow.tracking import MlflowClient
from config.logging_config import get_logger

logger = get_logger(__name__)

MLFLOW_URI = "http://localhost:5000"
mlflow.set_tracking_uri(MLFLOW_URI)
client = MlflowClient(MLFLOW_URI)


def save_model(model, model_name: str, ticker: str,
               metrics: dict, params: dict) -> str:

    # set which experiment this run belongs to
    # think of experiment = folder name in MLflow UI
    mlflow.set_experiment(model_name)

    # start a new run — like opening a new git commit
    with mlflow.start_run(run_name=f"{model_name}_{ticker}") as run:
        
        # save a tag so we can search by ticker later
        mlflow.set_tag("ticker", ticker)
        
        # save hyperparameters — n_estimators, learning_rate etc
        mlflow.log_params(params)
        
        # save performance metrics — MAE, RMSE etc
        mlflow.log_metrics(metrics)
        
        # save the actual model file
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path=model_name,
            registered_model_name=f"{model_name}_{ticker}"
        )
        
        logger.info(f"Saved {model_name} for {ticker} — run_id: {run.info.run_id}")
        return run.info.run_id


def load_best_model(model_name: str, ticker: str):
    runs = mlflow.search_runs(
        experiment_names=[model_name],
        filter_string=f"tags.ticker = '{ticker}'",
        order_by=["metrics.mae ASC"]
    )
    if runs.empty:
        logger.error(f"No runs found for {model_name} {ticker}")
        return None
    best_run_id = runs.iloc[0]['run_id']
    model = mlflow.sklearn.load_model(f"runs:/{best_run_id}/{model_name}")
    return model

def list_models(model_name: str) -> None:
    
    versions = client.search_model_versions(f"name LIKE '{model_name}%'")
    
    if not versions:
        print(f"No models found for {model_name}")
        return
    
    for v in versions:
        print(f"Model: {v.name} | Version: {v.version} | Stage: {v.current_stage}")

def promote_to_production(model_name: str, version: str) -> None:
    client.transition_model_version_stage(
        name=model_name, 
        version=version, 
        stage="Production"
    )
    
    logger.info(f'{model_name} has been promoted to Production')

if __name__ == "__main__":
    from sklearn.ensemble import IsolationForest
    import numpy as np

    X = np.random.randn(100, 5)
    model = IsolationForest(
        n_estimators=100,
        random_state=42
    )
    model.fit(X)
    run_id = save_model(
        model=model,
        model_name='anomaly_detection',
        ticker='AAPL',
        metrics={
            'mae': 32.5,
            'detection_rate': 0.052   
        },
        params={
            'n_estimators': 100,
            'random_state': 42
        }
    )
    print(f"Model {model} Saved, run_Id: {run_id}")
    list_models('anomaly_detection')