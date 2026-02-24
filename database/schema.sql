CREATE TABLE IF NOT EXISTS market_data(
    ticker TEXT NOT NULL,
    date TIMESTAMPTZ NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC NOT NULL,
    volume BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS crypto_prices(
    symbol TEXT NOT NULL,
    date TIMESTAMPTZ NOT NULL,
    open NUMERIC,
    high NUMERIC,
    low NUMERIC,
    close NUMERIC,
    volume NUMERIC,
    market_cap NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS economic_indicators(
    series_id TEXT NOT NULL,
    date DATE NOT NULL,
    value NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    PRIMARY KEY (series_id, date)
);

CREATE TABLE IF NOT EXISTS news_sentiment(
    id SERIAL,
    ticker TEXT,
    headline TEXT,
    source TEXT,
    published_at TIMESTAMPTZ NOT NULL,
    sentiment TEXT,
    score NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, published_at)  -- include published_at
);

CREATE TABLE IF NOT EXISTS anomalies(
    id SERIAL,
    ticker TEXT,
    date DATE,
    anomaly_score NUMERIC,
    severity TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, created_at)  -- include created_at
);

CREATE TABLE IF NOT EXISTS forecasts(
    id SERIAL,
    ticker TEXT,
    forecast_date TIMESTAMPTZ NOT NULL,
    predicted_at TIMESTAMPTZ DEFAULT NOW(),
    yhat NUMERIC,
    yhat_lower NUMERIC,
    yhat_upper NUMERIC,
    model_used TEXT,
    horizon_days INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, forecast_date)  -- include forecast_date
);

CREATE TABLE IF NOT EXISTS portfolio_weights(
    id SERIAL PRIMARY KEY,
    ticker TEXT,
    weight NUMERIC,
    method TEXT,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
    
);

CREATE TABLE IF NOT EXISTS model_runs (
    id SERIAL PRIMARY KEY,
    model_name TEXT,
    ticker TEXT,
    mae NUMERIC,
    rmse NUMERIC,
    r2 NUMERIC,
    parameters JSONB,
    trained_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS features(
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    log_return NUMERIC,
    lag_1d NUMERIC,
    lag_5d NUMERIC,
    lag_21d NUMERIC,
    lag_63d NUMERIC,
    rolling_mean_5 NUMERIC,
    rolling_std_5 NUMERIC,
    rolling_skew_5 NUMERIC,
    rolling_mean_21 NUMERIC,
    rolling_std_21 NUMERIC,
    rolling_skew_21 NUMERIC,
    rolling_mean_63 NUMERIC,
    rolling_std_63 NUMERIC,
    rolling_skew_63 NUMERIC,
    rsi_14 NUMERIC,
    bb_pct_b NUMERIC,
    volume_ratio NUMERIC,

    PRIMARY KEY (ticker, date)

);

-- Hypertables for time-series performance
SELECT create_hypertable('market_data', 'date', if_not_exists => TRUE);
SELECT create_hypertable('crypto_prices', 'date', if_not_exists => TRUE);
SELECT create_hypertable('news_sentiment', 'published_at', if_not_exists => TRUE);
SELECT create_hypertable('anomalies', 'created_at', if_not_exists => TRUE);
SELECT create_hypertable('forecasts', 'forecast_date', if_not_exists => TRUE);
SELECT create_hypertable('features', 'date', if_not_exists => TRUE);