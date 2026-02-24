
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import time
import pandas as pd
import requests
from datetime import datetime, timezone
from transformers import pipeline
from database.connection import get_session
from database.crud import insert_sentiment
from config.settings import NEWS_API_KEY

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
           "NVDA", "META", "JPM", "V", "JNJ"]


NEWS_BASE_URL = "https://newsapi.org/v2/everything"


def load_finbert() -> pipeline:
    pipe = pipeline("text-classification", model="ProsusAI/finbert")
    return pipe


def fetch_news(ticker: str) -> list[dict]:
    
    params = {
        "q":         ticker,
        "api_key":   NEWS_API_KEY,
        "language":  "en",
        "pageSize":  10
    }

    response = requests.get(NEWS_BASE_URL, params=params)
    response.raise_for_status()

    return response.json().get("articles", [])


def score_sentiment(pipe, headline: str) -> tuple[str, float]:
    # run headline through FinBERT
    # return (label, signed_score)
    # positive → +score, negative → -score, neutral → 0

    result = pipe(headline)[0]
    label = result['label'].lower()
    score = result['score']

    if label == 'positive':
        signed_score = score
    elif label == 'negative':
        signed_score = -score
    else:
        signed_score = 0.0
    
    return label, signed_score,


def transform(articles: list, ticker: str, pipe) -> list[dict]:
    # loop through articles
    # score each headline
    # return list of dicts matching news_sentiment schema
    record = []
    for articles in record:
        title = articles['title']
        source = articles['source']['name']
        published_at = articles['publishedAt']
        label, score = score_sentiment(pipe, title)

        record.append({
            'ticker' : ticker,
            'headline': title,
            'source': source,
            'published_at': published_at,
            'sentiment': label,
            'score': score
        })

    return record

def run():
    
    pipe = load_finbert()
    session = get_session()

    try:
        for symbol in TICKERS:
            print(f'[{symbol}] fetching news...')
            try:
                raw = fetch_news(symbol)

                if not raw:
                    print(f'[{symbol}] No News returned, skipping')
                    continue
                
                records = transform(raw, symbol, pipe)

                if not records:
                    print(f'[{symbol}] No valid records after tranformation')
                    continue

                insert_sentiment(session, records)
            except Exception as e:
                print(f'[{symbol}] Error: {e}')
                session.rollback()

            time.sleep(1)
    finally:
        session.close()

if __name__ == "__main__":
    run()