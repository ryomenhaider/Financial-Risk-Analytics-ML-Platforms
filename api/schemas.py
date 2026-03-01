from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class MarketDataResponse(BaseModel):
    ticker: str
    date: date                
    open: Optional[float]      
    high: Optional[float]
    low: Optional[float]
    close: float
    volume: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class AnomalyResponse(BaseModel):
    id: int
    ticker: Optional[str]
    date: Optional[date]
    anomaly_score: Optional[float]
    severity: Optional[str]
    model_used: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ForecastResponse(BaseModel):
    id: int
    ticker: Optional[str]
    forecast_date: Optional[date] 
    predicted_at: Optional[datetime]
    yhat: Optional[float]
    yhat_upper: Optional[float]
    yhat_lower: Optional[float]
    model_used: Optional[str]
    horizon_days: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class PortfolioWeightResponse(BaseModel):
    id: int
    ticker: Optional[str]
    weight: Optional[float]
    method: Optional[str]
    calculated_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class SentimentResponse(BaseModel):
    id: int
    ticker: Optional[str]
    headline: Optional[str]
    source: Optional[str]
    published_at: datetime
    sentiment: Optional[str]
    score: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}