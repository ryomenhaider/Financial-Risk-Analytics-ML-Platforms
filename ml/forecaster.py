import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import numpy as np
from prophet import Prophet
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sqlalchemy import text
from database.connection import engine, get_session
from database.crud import insert_forecasts
from config.logging_config import get_logger

logger = get_logger(__name__)

FEATURES = [
    'lag_1d', 'lag_5d', 'lag_21d', 'lag_63d',
    'rolling_mean_21', 'rolling_std_21',
    'rsi_14', 'volume_ratio', 'bb_pct_b'
]

HORIZONS = [30, 90]


def load_data(ticker: str) -> pd.DataFrame:
    query = """
        SELECT f.*, m.close
        FROM features f
        JOIN market_data m
            ON f.ticker = m.ticker
            AND f.date = m.date
        WHERE f.ticker = :ticker
        ORDER BY f.date ASC
    """
    with engine.connect() as conn:
        df = pd.read_sql(
            sql=text(query),
            con=conn,
            params={'ticker': ticker}
        )
    return df


def prepare_prophet_df(df: pd.DataFrame) -> pd.DataFrame:
    prophet_df = df[['date', 'close']].rename(columns={'date': 'ds', 'close': 'y'})
    prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])
    return prophet_df


def train_prophet(prophet_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    model = Prophet(
        daily_seasonality=False,
        weekly_seasonality=True,
        yearly_seasonality=True,
        interval_width=0.95
    )
    model.fit(prophet_df)
    future = model.make_future_dataframe(periods=horizon)
    forecast = model.predict(future)

    last_train_date = pd.Timestamp(prophet_df['ds'].max())
    result = (
        forecast[forecast['ds'] > last_train_date]
        [['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
        .head(horizon)
        .reset_index(drop=True)
    )
    return result

def walk_forward_cv(df: pd.DataFrame, horizon: int, n_splits: int = 5) -> dict:
    df_clean = df[FEATURES + ['close']].dropna()
    X = df_clean[FEATURES].values
    y = df_clean['close'].values

    fold_size = (len(X) - horizon) // n_splits
    maes, rmses = [], []

    for i in range(n_splits):
        train_end = fold_size * (i + 1)
        test_end = train_end + horizon  

        if test_end > len(X):
            break

        X_train, y_train = X[:train_end], y[:train_end]
        X_test, y_test = X[train_end:test_end], y[train_end:test_end]

        model = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)

        maes.append(mean_absolute_error(y_test, predictions))
        rmses.append(np.sqrt(mean_squared_error(y_test, predictions)))

    return {'mae': np.mean(maes), 'rmse': np.mean(rmses)}


def train_xgboost(df: pd.DataFrame, horizon: int) -> tuple:
    df_clean = df[FEATURES + ['close']].dropna()
    X = df_clean[FEATURES].values
    y = df_clean['close'].values

    cv_results = walk_forward_cv(df, horizon=horizon, n_splits=5)

    model = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
    model.fit(X, y)

    last_features = X[-1].copy()
    forecasts = []

    for i in range(horizon):
        prediction = model.predict(last_features.reshape(1, -1))[0]
        forecasts.append(prediction)
        last_features = np.roll(last_features, -1)
        last_features[-1] = prediction

    return (model, np.array(forecasts), cv_results['mae'], cv_results['rmse'])


def blend_forecasts(prophet_forecast: pd.DataFrame,
                    xgb_forecast: np.ndarray,
                    horizon: int) -> pd.DataFrame:
    df = prophet_forecast.copy()
    df['yhat'] = (df['yhat'] + xgb_forecast) / 2
    return df


def save_forecasts(forecast_df: pd.DataFrame,
                   ticker: str,
                   horizon: int) -> None:
    if forecast_df.empty:
        logger.error(f"[{ticker}] No forecasts to save")
        return

    rows = [
        {
            'ticker': ticker,
            'forecast_date': row['ds'],
            'yhat': row['yhat'],
            'yhat_upper': row['yhat_upper'],
            'yhat_lower': row['yhat_lower'],
            'model_used': 'prophet+xgboost',
            'horizon_days': horizon
        }
        for row in forecast_df.to_dict(orient='records')
    ]

    with get_session() as session:
        try:
            insert_forecasts(session, rows)
            print(f"[{ticker}] Saved forecasts to DB")
        except Exception as e:
            print(f"[{ticker}] Error saving forecasts: {e}")
            raise


def run(ticker: str) -> None:
    logger.info(f"[{ticker}] Starting forecasting...")
    df = load_data(ticker)

    if df.empty:
        logger.error(f"[{ticker}] No data found")
        return

    prophet_df = prepare_prophet_df(df)

    for horizon in HORIZONS:
        prophet_forecast = train_prophet(prophet_df, horizon=horizon)
        _, xgb_forecast, mae, rmse = train_xgboost(df, horizon=horizon)
        logger.info(f"[{ticker}] Horizon {horizon}d — MAE: {mae:.4f}, RMSE: {rmse:.4f}")
        forecast_df = blend_forecasts(prophet_forecast, xgb_forecast, horizon)
        save_forecasts(forecast_df, ticker, horizon)

    logger.info(f"[{ticker}] Forecasting complete")


if __name__ == "__main__":
    tickers = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']
    for ticker in tickers:
        run(ticker)