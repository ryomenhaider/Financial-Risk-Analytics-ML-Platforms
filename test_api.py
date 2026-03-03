#!/usr/bin/env python3
"""
Quick API diagnostic script to check if data is being returned
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import requests
import json
from pprint import pprint

API_BASE = "http://localhost:8000"
HEADERS = {"X-API-Key": "changeme"}

def test_health():
    print("=" * 60)
    print("1. Testing /health endpoint")
    print("=" * 60)
    try:
        r = requests.get(f"{API_BASE}/health", headers=HEADERS, timeout=3)
        print(f"Status: {r.status_code}")
        pprint(r.json())
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

def test_prices():
    print("=" * 60)
    print("2. Testing /prices/AAPL endpoint")
    print("=" * 60)
    try:
        r = requests.get(f"{API_BASE}/prices/AAPL", headers=HEADERS, timeout=3)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("Response structure:")
            pprint(r.json(), depth=2)
        else:
            print(f"Error: {r.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

def test_prices_history():
    print("=" * 60)
    print("3. Testing /prices/AAPL/history endpoint")
    print("=" * 60)
    try:
        r = requests.get(f"{API_BASE}/prices/AAPL/history", 
                        params={"limit": 5}, headers=HEADERS, timeout=3)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("Response structure:")
            data = r.json()
            print(f"Type: {type(data)}")
            if isinstance(data, dict):
                print("Keys:", list(data.keys())[:3])
            elif isinstance(data, list):
                print(f"List length: {len(data)}")
            pprint(data, depth=2)
        else:
            print(f"Error: {r.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

def test_anomalies():
    print("=" * 60)
    print("4. Testing /anomalies endpoint")
    print("=" * 60)
    try:
        r = requests.get(f"{API_BASE}/anomalies", 
                        params={"ticker": "AAPL", "days": 30}, 
                        headers=HEADERS, timeout=3)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("Response structure:")
            pprint(r.json(), depth=2)
        else:
            print(f"Error: {r.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

def test_sentiment():
    print("=" * 60)
    print("5. Testing /sentiment/timeline endpoint")
    print("=" * 60)
    try:
        r = requests.get(f"{API_BASE}/sentiment/timeline", 
                        params={"ticker": "AAPL", "days": 30}, 
                        headers=HEADERS, timeout=3)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            print("Response structure:")
            pprint(r.json(), depth=2)
        else:
            print(f"Error: {r.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

def test_database():
    print("=" * 60)
    print("6. Testing Database Connection")
    print("=" * 60)
    try:
        from database.connection import test_connection
        result = test_connection()
        print(f"Database connected: {result}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

def check_database_data():
    print("=" * 60)
    print("7. Checking Database Data")
    print("=" * 60)
    try:
        from database.connection import get_session
        with get_session() as session:
            from database.models import MarketData, NewsSentiment, Anomaly, Forecast
            
            market_count = session.query(MarketData).count()
            sentiment_count = session.query(NewsSentiment).count()
            anomaly_count = session.query(Anomaly).count()
            forecast_count = session.query(Forecast).count()
            
            print(f"MarketData rows: {market_count}")
            print(f"NewsSentiment rows: {sentiment_count}")
            print(f"Anomaly rows: {anomaly_count}")
            print(f"Forecast rows: {forecast_count}")
            
            if market_count > 0:
                sample = session.query(MarketData).first()
                print(f"\nSample MarketData: {sample.__dict__ if sample else 'None'}")
    except Exception as e:
        print(f"❌ Error: {e}")
    print()

if __name__ == "__main__":
    test_health()
    test_database()
    check_database_data()
    test_prices()
    test_prices_history()
    test_anomalies()
    test_sentiment()
    
    print("=" * 60)
    print("Diagnostic complete!")
    print("=" * 60)
