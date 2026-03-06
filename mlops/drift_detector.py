import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import numpy as np
from scipy.stats import ks_2samp
from datetime import datetime, timedelta
from sqlalchemy import text
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

from database.connection import engine, get_session
from config.logging_config import get_logger

logger = get_logger(__name__)

PSI_THRESHOLD = 0.2  # PSI alert threshold
KS_THRESHOLD = 0.05  # KS test p-value threshold

MONITORED_FEATURES = [
    'log_return',
    'lag_1d', 'lag_5d', 'lag_21d', 'lag_63d',
    'rolling_mean_21', 'rolling_std_21', 'rolling_skew_21',
    'rsi_14', 'bb_pct_b', 'volume_ratio'
]

BASELINE_DAYS = 180
PRODUCTION_DAYS = 30


def calculate_psi(baseline: pd.Series, production: pd.Series, bins: int = 10) -> float:
    baseline = baseline.dropna()
    production = production.dropna()
    
    if len(baseline) == 0 or len(production) == 0:
        return 0.0
    
    breakpoints = np.percentile(baseline, np.linspace(0, 100, bins + 1))
    breakpoints[0] = baseline.min() - 0.001
    breakpoints[-1] = baseline.max() + 0.001
    
    baseline_binned, _ = np.histogram(baseline, bins=breakpoints)
    production_binned, _ = np.histogram(production, bins=breakpoints)
    
    baseline_pct = baseline_binned / len(baseline)
    production_pct = production_binned / len(production)
    
    psi = 0.0
    for b_pct, p_pct in zip(baseline_pct, production_pct):
        if b_pct > 0 and p_pct > 0:
            psi += (p_pct - b_pct) * np.log(p_pct / b_pct) 
        elif b_pct == 0 and p_pct > 0:
            psi += p_pct * np.log(p_pct / 0.001)  # Small constant to avoid log(0)
    
    return psi


def calculate_ks_test(baseline: pd.Series, production: pd.Series) -> tuple:
    baseline = baseline.dropna()
    production = production.dropna()
    
    if len(baseline) == 0 or len(production) == 0:
        return 0.0, 1.0
    
    statistic, p_value = ks_2samp(baseline, production)
    return statistic, p_value


def load_baseline_data(ticker: str, days: int = BASELINE_DAYS) -> pd.DataFrame:
    cutoff_date = datetime.utcnow() - timedelta(days=days * 3)  # Go further back to get enough data
    
    query = """
        SELECT date, log_return, lag_1d, lag_5d, lag_21d, lag_63d,
               rolling_mean_21, rolling_std_21, rolling_skew_21,
               rsi_14, bb_pct_b, volume_ratio
        FROM features
        WHERE ticker = :ticker AND date >= :cutoff_date
        ORDER BY date ASC
        LIMIT :limit
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(
            sql=text(query),
            con=conn,
            params={
                'ticker': ticker,
                'cutoff_date': cutoff_date.date(),
                'limit': days
            }
        )
    
    return df


def load_production_data(ticker: str, days: int = PRODUCTION_DAYS) -> pd.DataFrame:
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = """
        SELECT date, log_return, lag_1d, lag_5d, lag_21d, lag_63d,
               rolling_mean_21, rolling_std_21, rolling_skew_21,
               rsi_14, bb_pct_b, volume_ratio
        FROM features
        WHERE ticker = :ticker AND date >= :cutoff_date
        ORDER BY date ASC
    """
    
    with engine.connect() as conn:
        df = pd.read_sql(
            sql=text(query),
            con=conn,
            params={
                'ticker': ticker,
                'cutoff_date': cutoff_date.date()
            }
        )
    
    return df


def detect_drift(ticker: str, 
                 baseline_days: int = BASELINE_DAYS, 
                 production_days: int = PRODUCTION_DAYS
                 
                 # at this point i am mentally ill 
                 ) -> dict:
    
    baseline_df = load_baseline_data(ticker, baseline_days)
    production_df = load_production_data(ticker, production_days)
    
    if len(baseline_df) == 0 or len(production_df) == 0:
        logger.warning(f"[{ticker}] Insufficient data for drift detection")
        return None
    
    results = {
        'ticker': ticker,
        'timestamp': datetime.utcnow().isoformat(),
        'baseline_size': len(baseline_df),
        'production_size': len(production_df),
        'features': [],
        'drifted_features': [],
        'has_drift_alert': False,
    }
    
    for feature in MONITORED_FEATURES:
        if feature not in baseline_df.columns or feature not in production_df.columns:
            continue
        
        baseline_series = pd.to_numeric(baseline_df[feature], errors='coerce')
        production_series = pd.to_numeric(production_df[feature], errors='coerce')
        
        psi = calculate_psi(baseline_series, production_series)
        ks_stat, ks_pval = calculate_ks_test(baseline_series, production_series)
        
        is_drifted = psi > PSI_THRESHOLD
        
        feature_result = {
            'feature': feature,
            'psi': float(psi),
            'ks_statistic': float(ks_stat),
            'ks_p_value': float(ks_pval),
            'is_drifted': is_drifted,
            'baseline_mean': float(baseline_series.mean()),
            'baseline_std': float(baseline_series.std()),
            'production_mean': float(production_series.mean()),
            'production_std': float(production_series.std()),
        }
        
        results['features'].append(feature_result)
        
        if is_drifted:
            results['drifted_features'].append(feature)
            results['has_drift_alert'] = True
    
    return results


def send_email_alert(drift_results: dict, recipient_email: str = None) -> bool:
    try:
        smtp_server = os.getenv('SMTP_SERVER')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_user = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASSWORD')
        sender_email = os.getenv('ALERT_EMAIL_FROM', smtp_user)
        
        if not all([smtp_server, smtp_user, smtp_password, sender_email]):
            logger.warning("Email configuration incomplete, skipping email alert")
            return False
        
        if not recipient_email:
            recipient_email = os.getenv('ALERT_EMAIL_TO')
        
        if not recipient_email:
            logger.warning("No recipient email configured")
            return False
        
        # Build email body
        ticker = drift_results['ticker']
        drifted = drift_results['drifted_features']
        
        subject = f"⚠️ Data Drift Alert: {ticker}"
        
        body = f"""
DRIFT DETECTION ALERT
{'='*60}

Ticker: {ticker}
Timestamp: {drift_results['timestamp']}
Baseline Size: {drift_results['baseline_size']} days
Production Size: {drift_results['production_size']} days

DRIFTED FEATURES (PSI > {PSI_THRESHOLD}):
{'-'*60}
"""
        
        for feature_result in drift_results['features']:
            if feature_result['is_drifted']:
                body += f"\n{feature_result['feature']}:"
                body += f"\n  PSI: {feature_result['psi']:.4f}"
                body += f"\n  Baseline Mean: {feature_result['baseline_mean']:.4f}"
                body += f"\n  Production Mean: {feature_result['production_mean']:.4f}"
                body += f"\n  KS p-value: {feature_result['ks_p_value']:.4f}"
        
        body += f"\n\n{'='*60}\n"
        body += "Please investigate the production data distribution changes.\n"
        
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        logger.info(f"Drift alert email sent to {recipient_email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send email alert: {e}")
        return False


def send_slack_alert(drift_results: dict, webhook_url: str = None) -> bool:
    try:
        if not webhook_url:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        
        if not webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False
        
        ticker = drift_results['ticker']
        drifted = drift_results['drifted_features']
        
        # Build Slack message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 Data Drift Alert",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Ticker:*\n{ticker}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Timestamp:*\n{drift_results['timestamp']}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Drifted Features:*\n{len(drifted)}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Baseline Size:*\n{drift_results['baseline_size']} days"
                    }
                ]
            }
        ]
        
        drift_text = ""
        for feature_result in drift_results['features']:
            if feature_result['is_drifted']:
                drift_text += f"• *{feature_result['feature']}*: PSI={feature_result['psi']:.4f}\n"
        
        if drift_text:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Features with Drift (PSI > {PSI_THRESHOLD}):*\n{drift_text}"
                }
            })
        
        response = requests.post(webhook_url, json={"blocks": blocks})
        
        if response.status_code == 200:
            logger.info(f"Drift alert posted to Slack for {ticker}")
            return True
        else:
            logger.error(f"Slack webhook returned {response.status_code}")
            return False
    
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {e}")
        return False


def run_drift_check(ticker: str, send_alerts: bool = False) -> dict:
    logger.info(f"Starting drift detection for {ticker}")
    
    results = detect_drift(ticker)
    
    if results is None:
        return None
    
    if results['has_drift_alert'] and send_alerts:
        logger.warning(f"Drift detected in {ticker}: {results['drifted_features']}")
        send_email_alert(results)
        send_slack_alert(results)
    
    return results


if __name__ == "__main__":
    import argparse
    from tabulate import tabulate
    
    parser = argparse.ArgumentParser(description="MLOps Drift Detection")
    parser.add_argument('--tickers', default='AAPL,MSFT,GOOGL,TSLA,NVDA',
                       help='Comma-separated tickers to check')
    parser.add_argument('--send-alerts', action='store_true',
                       help='Send email/Slack alerts on drift')
    
    args = parser.parse_args()
    tickers = args.tickers.split(',')
    
    print("\n" + "="*80)
    print("MLOPS DRIFT DETECTION REPORT")
    print("="*80)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    print(f"Baseline Period: {BASELINE_DAYS} days | Production Period: {PRODUCTION_DAYS} days")
    print(f"PSI Threshold: {PSI_THRESHOLD} | KS p-value Threshold: {KS_THRESHOLD}\n")
    
    all_results = []
    
    for ticker in tickers:
        print(f"\n{'─'*80}")
        print(f"Ticker: {ticker}")
        print(f"{'─'*80}")
        
        drift_results = run_drift_check(ticker, send_alerts=args.send_alerts)
        
        if drift_results is None:
            print(f"⚠️  Insufficient data for {ticker}")
            continue
        
        all_results.append(drift_results)
        
        # Build table
        table_data = []
        for feature_result in drift_results['features']:
            feature = feature_result['feature']
            psi = feature_result['psi']
            ks_pval = feature_result['ks_p_value']
            is_drifted = "🚩 YES" if feature_result['is_drifted'] else "✓ No"
            
            table_data.append([
                feature,
                f"{psi:.4f}",
                f"{ks_pval:.4f}",
                is_drifted,
                f"{feature_result['baseline_mean']:.4f}",
                f"{feature_result['production_mean']:.4f}",
            ])
        
        headers = ["Feature", "PSI", "KS p-val", "Drifted?", "Base Mean", "Prod Mean"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
        
        if drift_results['drifted_features']:
            print(f"\n⚠️  DRIFT DETECTED: {len(drift_results['drifted_features'])} feature(s)")
            print(f"   Features: {', '.join(drift_results['drifted_features'])}")
        else:
            print(f"\n✓ No drift detected")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    total_drifted = sum(len(r['drifted_features']) for r in all_results)
    print(f"Total Tickers Checked: {len(all_results)}")
    print(f"Total Drifted Features: {total_drifted}")
    
    if total_drifted > 0:
        print("\n⚠️  ACTION REQUIRED: Data drift detected. Review production data.")
        sys.exit(1)
    else:
        print("\n✓ All distributions stable.")
        sys.exit(0)
