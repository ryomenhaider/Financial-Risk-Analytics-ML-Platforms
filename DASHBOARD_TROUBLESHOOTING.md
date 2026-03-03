# Dashboard Data Fetch Troubleshooting Guide

## Issues Found & Fixed

### 1. **API_BASE URL Mismatch** ✅ FIXED
- **Problem**: Frontend was trying to reach `http://localhost:8000/api/v1/prices` but API routers are mounted at `http://localhost:8000/prices`
- **Fix**: Updated `dashboard/theme.py` to use `http://localhost:8000` instead of `http://localhost:8000/api/v1`

### 2. **API Response Format** ✅ FIXED
- **Problem**: `/prices/{ticker}/history` endpoint was returning incorrect format
- **Fix**: Updated API router to return proper list of serialized price objects

### 3. **Database Might Be Empty** ⚠️ NEEDS ATTENTION
- **Symptom**: Dashboard shows no data even with correct API endpoints
- **Cause**: Database schema/tables might not exist or seed data hasn't been loaded

## Quick Start - Initialize Everything

### Step 1: Verify Database Connection
```bash
python database/connection.py
```
Should show: `The DB has connected`

### Step 2: Initialize Database & Load Seed Data
```bash
python init_db.py
```
This will:
- Create all required tables from `database/schema.sql`
- Load sample data from `database/seed_data.sql`
- Verify data was loaded successfully

### Step 3: Test API Endpoints
```bash
python test_api.py
```
This will:
- Check API health status
- Test each endpoint (`/prices`, `/anomalies`, `/sentiment`, `/forecasts`, `/portfolio`)
- Show response formats and data
- Count records in database

Expected output should show:
- ✅ Database connected
- ✅ API responding with 200 status
- ✅ Data rows > 0 for each table

### Step 4: Start Services
```bash
# Terminal 1: Start API (if not already running)
cd /home/alpha/financial-intelligence-platform
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Start Dashboard
python -m dashboard.app
# Or use Dash CLI
# dash run dashboard/app.py --host 0.0.0.0 --port 8050
```

## API Endpoint Reference

All endpoints are at `http://localhost:8000` (not `/api/v1`):

### Prices
- `GET /prices/{ticker}` - Latest price
- `GET /prices/{ticker}/history?limit=90` - Historical data
- `GET /prices/compare?tickers=AAPL,MSFT` - Compare multiple tickers

### Anomalies
- `GET /anomalies?ticker=AAPL&days=30` - Get anomalies for ticker
- `GET /anomalies/latest` - Latest anomaly
- `POST /anomalies/detect/{ticker}` - Trigger detection

### Forecasts
- `GET /forecasts/{ticker}?horizon=30` - Get forecast
- `GET /forecasts/compare?tickers=AAPL,MSFT&horizon=30` - Compare forecasts

### Sentiment
- `GET /sentiment/timeline?ticker=AAPL&days=30` - Timeline data
- `GET /sentiment/{ticker}?days=30` - Ticker sentiment
- `GET /sentiment/heatmap` - All tickers heatmap

### Portfolio
- `GET /portfolio/weights` - Portfolio weights
- `GET /portfolio/optimize` - Run optimizer
- `GET /portfolio/backtest` - Backtest results

## Response Formats

### Market Data Response
```json
{
  "ticker": "AAPL",
  "date": "2024-01-02",
  "open": 185.12,
  "high": 186.50,
  "low": 184.30,
  "close": 185.85,
  "volume": 72345678,
  "created_at": "2024-01-02T15:30:00Z"
}
```

### Sentiment Response
```json
{
  "id": 1,
  "ticker": "AAPL",
  "headline": "Apple Vision Pro launch drives...",
  "source": "Reuters",
  "published_at": "2024-01-02T09:30:00Z",
  "sentiment": "positive",
  "score": 0.87,
  "created_at": "2024-01-02T15:30:00Z"
}
```

## Troubleshooting Checklist

- [ ] Database connection works: `python database/connection.py`
- [ ] Tables created: `python init_db.py` or check with `psql`
- [ ] Seed data loaded: Check row counts with `python test_api.py`
- [ ] API running: `python -m uvicorn api.main:app --host 0.0.0.0 --port 8000`
- [ ] Dashboard running: `python -m dashboard.app`
- [ ] API responding: Visit `http://localhost:8000/docs` for Swagger UI
- [ ] No CORS issues: Check browser console for errors
- [ ] Environment variables set: Check `DB_URL`, `FRED_API_KEY`, `NEWSDATA_API_KEY`

## Common Issues

### "No data" on Dashboard
1. Run `python init_db.py` to load seed data
2. Run `python test_api.py` to verify API returns data
3. Check browser console (F12) for network errors

### API returns 404
1. Verify correct port: 8000 (not 5000 or 8050)
2. Check endpoint path - no `/api/v1` prefix!
3. Check ticker exists in database: `python test_api.py`

### Database Connection Failed
1. Check `DB_URL` environment variable: `echo $DB_URL`
2. Verify PostgreSQL running: `psql -U postgres`
3. Check database exists: `createdb financial_platform`
4. Reset connection: Restart PostgreSQL service

### Dashboard showing "OFFLINE" status
1. Make sure API is running on port 8000
2. Check `API_HEALTH` in `dashboard/theme.py`
3. Verify HEADERS/API_KEY environment variable if needed

## Data Ingestion

The system uses Airflow DAGs for continuous data ingestion:
- `airflow/dags/dag_prices.py` - Fetches stock prices daily
- `airflow/dags/dag_news.py` - Fetches news sentiment
- `airflow/dags/dag_macro.py` - Fetches macro indicators

For testing, seed data is sufficient. For production, ensure Airflow is running.

## Next Steps

1. ✅ Fix API_BASE URL (DONE)
2. ✅ Fix API response formats (DONE)
3. Run `python init_db.py` to initialize database
4. Run `python test_api.py` to verify everything works
5. Start API and Dashboard
6. Check that data is displaying on all pages

If issues persist, share output from `python test_api.py` for debugging.
