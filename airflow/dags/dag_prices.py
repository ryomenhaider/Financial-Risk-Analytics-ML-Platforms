import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from airflow.sdk import dag, task
from datetime import datetime
@dag(schedule="0 18 * * *", start_date=datetime(2026, 2, 27), catchup=False)
def stock_ingestion():

    @task
    def task_one():
        from ingestion.price_fetcher import run
        run()

    @task
    def task_two():
        from ingestion.feature_engineer import main
        main()

    task_one() >> task_two()

stock_ingestion()