
from sqlalchemy import Column, Date, Text, Numeric, BigInteger, Integer, text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import TIMESTAMP

class Base(DeclarativeBase):
    pass


class MarketData(Base):
    __tablename__ = "market_data"
    
    ticker = Column(Text, primary_key=True, nullable=False)
    date = Column(Date, primary_key=True, nullable=False)
    open = Column(Numeric)
    high = Column(Numeric)
    low = Column(Numeric)
    close = Column(Numeric, nullable=False)
    volume = Column(BigInteger)
    created_at = Column(TIMESTAMP(timezone=True),server_default=text("NOW()"))
    

class CryptoPrice(Base):
    __tablename__ = "crypto_prices"
    
    symbol = Column(Text,primary_key=True, nullable=False)
    date = Column(Date, primary_key=True, nullable=False)
    open = Column(Numeric)
    high = Column(Numeric)
    low = Column(Numeric)
    close = Column(Numeric)
    volume = Column(Numeric)
    market_cap = Column(Numeric)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('NOW()'))


class EconomicIndicator(Base):
    __tablename__ = "economic_indicators"

    series_id = Column(Text,primary_key=True, nullable=False)
    date = Column(Date,primary_key=True, nullable=False)
    value = Column(Numeric)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('NOW()'))

class NewsSentiment(Base):
    __tablename__ = "news_sentiment"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(Text)
    headline = Column(Text)
    source = Column(Text)
    published_at = Column(TIMESTAMP(timezone=True))
    sentiment = Column(Text)
    score = Column(Numeric)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('NOW()'))

class Anomaly(Base):
    __tablename__ = "anomalies"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(Text)
    date = Column(Date)
    anomaly_score = Column(Numeric)
    severity = Column(Text)
    model_used = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('NOW()'))


class Forecast(Base):
    __tablename__ = "forecasts"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(Text)
    forecast_date = Column(Date)
    predicted_at = Column(TIMESTAMP(timezone=True), server_default=text('NOW()'))
    yhat = Column(Numeric)
    yhat_lower=  Column(Numeric)
    yhat_upper = Column(Numeric)
    model_used = Column(Text)
    horizon_days=  Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('NOW()'))


class PortfolioWeight(Base):
    __tablename__ = "portfolio_weights"
    
    id = Column(Integer, primary_key=True)
    ticker = Column(Text)
    weight = Column(Numeric)
    method = Column(Text)
    calculated_at = Column(TIMESTAMP(timezone=True), server_default=text('NOW()'))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('NOW()'))


class ModelRun(Base):
    __tablename__ = "model_runs"
    
    id = Column(Integer, primary_key=True)
    model_name = Column(Text)
    ticker = Column(Text)
    mae = Column(Numeric)
    rmse = Column(Numeric)
    r2 = Column(Numeric)
    parameters = Column(JSONB)
    trained_at = Column(TIMESTAMP(timezone=True), server_default=text('NOW()'))
    created_at = Column(TIMESTAMP(timezone=True), server_default=text('NOW()'))


class Features(Base):
    __tablename__ = "features"

    ticker = Column(Text, primary_key=True, nullable=False)
    date = Column(Date, primary_key=True, nullable=False)
    log_return = Column(Numeric)
    lag_1d = Column(Numeric)
    lag_5d = Column(Numeric)
    lag_21d = Column(Numeric)
    lag_63d = Column(Numeric)
    rolling_mean_21 = Column(Numeric)
    rolling_std_21 = Column(Numeric)
    rolling_skew_21 = Column(Numeric)
    rsi_14 = Column(Numeric)
    bb_pct_b = Column(Numeric)
    volume_ratio = Column(Numeric)