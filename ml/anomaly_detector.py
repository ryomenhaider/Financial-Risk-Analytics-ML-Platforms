import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler

from pyod.models.iforest import IForest
from pyod.models.lof import LOF

from sqlalchemy import text
from database.connection import engine
from database.crud import insert_anomaly
from config.logging_config import get_logger
from database.connection import get_session

logger = get_logger(__name__)

FEATURES = [
    'log_return',
    'volume_ratio',
    'rolling_std_21',
    'rsi_14',
    'bb_pct_b',
]

CONTAMINATION = 0.05  # expect ~5% anomalies


def load_data(ticker: str) -> pd.DataFrame:
    query = """
             SELECT *
            FROM features
            WHERE ticker = :ticker
            ORDER BY date ASC
            """
    with engine.connect() as conn:
        df = pd.read_sql(
            sql=text(query),
            con=conn,
            params={'ticker': ticker}
        )
    return df


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURES].dropna().values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Isolation Forest (fast, good for financial data)
    iso = IForest(
        n_estimators=100,
        contamination=CONTAMINATION,
        random_state=42
    )
    iso.fit(X_scaled)
    iso_score = iso.decision_scores_

    # Local Outlier Factor (catches local density anomalies)
    lof = LOF(
        n_neighbors=20,
        contamination=CONTAMINATION
    )
    lof.fit(X_scaled)
    lof_score = lof.decision_scores_

    # Normalize and ensemble both scores
    iso_normalized = MinMaxScaler().fit_transform(iso_score.reshape(-1, 1)).flatten()
    lof_normalized = MinMaxScaler().fit_transform(lof_score.reshape(-1, 1)).flatten()

    ensemble_score = (iso_normalized + lof_normalized) / 2

    valid_idx = df[FEATURES].dropna().index
    df.loc[valid_idx, 'anomaly_score'] = ensemble_score
    df['anomaly_score'] = df['anomaly_score'].fillna(0)

    return df


def label_severity(anomaly_score: float) -> str:
    if anomaly_score >= 0.8:
        return 'critical'
    elif anomaly_score >= 0.6:
        return 'high'
    elif anomaly_score >= 0.4:
        return 'medium'
    else:
        return 'low'


def save_anomalies(df: pd.DataFrame, ticker: str) -> None:
    anomalies_df = df[df['anomaly_score'] > 0.4].copy()

    if anomalies_df.empty:
        logger.info(f"[{ticker}] No anomalies to save")
        return

    rows = [
        {
            'ticker': ticker,
            'date': row['date'],
            'anomaly_score': row['anomaly_score'],
            'severity': label_severity(row['anomaly_score']),
            'model_used': 'isolation_forest+lof'
        }
        for row in anomalies_df.to_dict(orient="records")
    ]

    session = get_session()
    try:
        insert_anomaly(session, rows)
        logger.info(f"[{ticker}] Saved {len(rows)} anomalies to DB")
        session.commit()
        print(f"[{ticker}] Saved {len(rows)} anomalies to DB")
    except Exception as e:
        session.rollback()
        logger.error(f"[{ticker}] Failed to save anomalies: {e}")
        raise
    finally:
        session.close()


def run(ticker: str) -> None:
    """Main entry point."""
    logger.info(f'Running Anomaly detection for {ticker}')
    df = load_data(ticker)

    if df.empty:
        logger.error(f'{ticker} is empty')
        return

    df = detect_anomalies(df)

    anomaly_count = (df['anomaly_score'] > 0.4).sum()
    rate = anomaly_count / len(df) * 100

    print(f"{ticker}: {anomaly_count}/{len(df)} anomalies ({rate:.1f}%)")

    save_anomalies(df, ticker)


if __name__ == "__main__":
    tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']
    for ticker in tickers:
        run(ticker)