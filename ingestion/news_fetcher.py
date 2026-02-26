import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time
import requests
from transformers import pipeline
from database.connection import get_session
from database.crud import insert_sentiment
from config.settings import NEWSDATA_API_KEY

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"]
NEWS_BASE_URL = "https://newsdata.io/api/1/news"


def load_finbert() -> pipeline:
    return pipeline("text-classification", model="ProsusAI/finbert")


def fetch_news(ticker: str) -> list[dict]:
    params = {
        "q": ticker,
        "apikey": NEWSDATA_API_KEY,   # newsdata.io uses "apikey" not "api_key"
        "language": "en",
        "category": "business",        # optional: focus on business/finance news
    }
    response = requests.get(NEWS_BASE_URL, params=params)
    response.raise_for_status()
    data = response.json()

    if data.get("status") != "success":
        raise ValueError(f"newsdata.io error: {data.get('results', 'Unknown error')}")

    return data.get("results", [])     # newsdata.io returns "results", not "articles"


def score_sentiment(pipe, headline: str) -> tuple[str, float]:
    result = pipe(headline, truncation=True, max_length=512)[0]
    label = result["label"].lower()
    score = result["score"]

    if label == "positive":
        signed_score = score
    elif label == "negative":
        signed_score = -score
    else:
        signed_score = 0.0

    return label, signed_score


def transform(articles: list, ticker: str, pipe) -> list[dict]:
    records = []
    for article in articles:
        title = article.get("title")
        if not title:                  # skip articles with no headline
            continue

        # newsdata.io field names differ from newsapi.org
        source = article.get("source_id", "unknown")
        published_at = article.get("pubDate")  # format: "YYYY-MM-DD HH:MM:SS"

        label, score = score_sentiment(pipe, title)

        records.append({
            "ticker": ticker,
            "headline": title,
            "source": source,
            "published_at": published_at,
            "sentiment": label,
            "score": score,
        })

    return records


def run():
    pipe = load_finbert()
    session = get_session()

    try:
        for symbol in TICKERS:
            print(f"[{symbol}] Fetching news...")
            try:
                raw = fetch_news(symbol)
                if not raw:
                    print(f"[{symbol}] No news returned, skipping")
                    continue

                records = transform(raw, symbol, pipe)
                if not records:
                    print(f"[{symbol}] No valid records after transformation, skipping")
                    continue

                insert_sentiment(session, records)
                print(f"[{symbol}] Inserted {len(records)} records")

            except Exception as e:
                print(f"[{symbol}] Error: {e}")
                session.rollback()

            time.sleep(1)  # stay within rate limits

    finally:
        session.close()


if __name__ == "__main__":
    run()