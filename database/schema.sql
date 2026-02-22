CREATE TABLE IF NOT EXISTS market_data(
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
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
    date DATE NOT NULL,
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
    id SERIAL PRIMARY KEY,
    ticker TEXT,
    headline TEXT,
    source TEXT,
    published_at TIMESTAMPTZ,
    sentiment TEXT,
    score NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS anomalies(
    id SERIAL PRIMARY KEY,
    ticker TEXT,
    date DATE,
    anomaly_score NUMERIC,
    severity TEXT,
    model_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS forecasts(
    id SERIAL PRIMARY KEY,
    ticker TEXT,
    forecast_date DATE,
    predicted_at TIMESTAMPTZ DEFAULT NOW(),
    yhat NUMERIC,
    yhat_lower NUMERIC,
    yhat_upper NUMERIC,
    model_used TEXT,
    horizon_days INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
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

CREATE INDEX idx_market_data_ticker_date 
ON market_data (ticker, date DESC);

CREATE INDEX idx_market_data_date 
ON market_data (date DESC);

CREATE INDEX idx_crypto_prices_symbol_date 
ON crypto_prices (symbol, date DESC);

