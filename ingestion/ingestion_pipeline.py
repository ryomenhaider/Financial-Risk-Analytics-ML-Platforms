import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time
import traceback

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def header(msg: str) -> None:
    print(f"\n{BOLD}{CYAN}{'─' * 60}{RESET}")
    print(f"{BOLD}{CYAN}  {msg}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * 60}{RESET}")

def success(msg: str) -> None:
    print(f"{GREEN}  ✔  {msg}{RESET}")

def failure(msg: str) -> None:
    print(f"{RED}  ✘  {msg}{RESET}")

def info(msg: str) -> None:
    print(f"{YELLOW}  ➤  {msg}{RESET}")


def run_price_fetcher() -> bool:
    from ingestion.price_fetcher import run
    run()
    return True


def run_crypto_fetcher() -> bool:
    from ingestion.crypto_fetcher import run
    run()
    return True


def run_macro_fetcher() -> bool:
    from ingestion.macro_fetcher import run
    run()
    return True


def run_news_fetcher() -> bool:
    from ingestion.news_fetcher import run
    run()
    return True


def run_feature_engineer() -> bool:
    from ingestion.feature_engineer import main
    main()
    return True


STAGES = [
    {
        "name":        "Stock Prices     (yfinance)",
        "fn":          run_price_fetcher,
        "description": "Fetching 10y daily OHLCV for AAPL, MSFT, GOOGL …",
    },
    {
        "name":        "Crypto Prices    (CCXT / Binance)",
        "fn":          run_crypto_fetcher,
        "description": "Fetching 365d daily OHLCV for BTC, ETH, BNB, SOL, ADA …",
    },
    {
        "name":        "Macro Indicators (FRED)",
        "fn":          run_macro_fetcher,
        "description": "Fetching Fed Funds Rate, CPI, Unemployment, GDP, VIX …",
    },
    {
        "name":        "News Sentiment   (newsdata.io + FinBERT)",
        "fn":          run_news_fetcher,
        "description": "Fetching headlines and scoring sentiment …",
    },
    {
        "name":        "Feature Engineering",
        "fn":          run_feature_engineer,
        "description": "Computing log-returns, RSI, Bollinger Bands, rolling stats …",
        "depends_on":  "Stock Prices",  
    },
]

def run_pipeline(stages: list[dict] | None = None) -> None:
    stages = stages or STAGES

    total   = len(stages)
    results = {}         
    t_start = time.time()

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  INGESTION PIPELINE  —  {total} stage(s) queued{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}")

    for idx, stage in enumerate(stages, start=1):
        name  = stage["name"]
        fn    = stage["fn"]
        desc  = stage.get("description", "")

        header(f"[{idx}/{total}]  {name}")
        info(desc)

        t0 = time.time()
        try:
            fn()
            elapsed = time.time() - t0
            success(f"Completed in {elapsed:.1f}s")
            results[name] = True

        except Exception as exc:
            elapsed = time.time() - t0
            failure(f"Failed after {elapsed:.1f}s — {exc}")
            traceback.print_exc()
            results[name] = False

    total_elapsed = time.time() - t_start
    passed = sum(v for v in results.values())
    failed = total - passed

    print(f"\n{BOLD}{'═' * 60}{RESET}")
    print(f"{BOLD}  PIPELINE SUMMARY  —  finished in {total_elapsed:.1f}s{RESET}")
    print(f"{BOLD}{'═' * 60}{RESET}")

    for name, ok in results.items():
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  [{status}]  {name}")

    print()
    if failed == 0:
        print(f"{GREEN}{BOLD}  All {total} stage(s) completed successfully.{RESET}\n")
    else:
        print(f"{RED}{BOLD}  {failed}/{total} stage(s) failed. Check logs above.{RESET}\n")



if __name__ == "__main__":
    run_pipeline()