import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from airflow.sdk import dag, task
from datetime import datetime

@dag(schedule="0 6,12,16,20 * * *", start_date=datetime(2026, 2, 27), catchup=False)
def news_ingestion():

    @task
    def task_one():
        from ingestion.news_fetcher import run
        run()

    task_one()

news_ingestion()