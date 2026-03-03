"""
Page 5 — Sentiment Analysis
News feed with FinBERT score badges, 30-day sentiment timeline,
correlation between sentiment and next-day returns.
"""

import dash
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import datetime, random

dash.register_page(__name__, path="/sentiment", name="Sentiment Analysis")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
COLORS  = dict(accent="#00e5ff", green="#00c98d", red="#ff4d6d", orange="#ff8c42",
               surface="#0d1117", surface2="#161b27", border="#1e2738", muted="#64748b", text="#e2e8f0")

HEADLINES = [
    "{t} beats earnings estimates by 8% as cloud revenue surges",
    "Analysts upgrade {t} to Strong Buy ahead of product launch",
    "{t} faces regulatory scrutiny over data privacy practices",
    "{t} announces $10B share buyback programme",
    "Supply chain disruption hits {t} quarterly guidance",
    "{t} expands AI integration across flagship product line",
    "Activist investor takes stake in {t}, pushes for restructuring",
    "{t} CEO signals optimism for second-half recovery",
    "{t} misses revenue target; stock falls in after-hours trading",
    "{t} secures major government contract worth $2.4B",
    "Labour concerns at {t} facilities spark union talks",
    "{t} launches next-gen chip platform outperforming rivals",
]
SOURCES = ["Reuters", "Bloomberg", "CNBC", "WSJ", "FT", "MarketWatch", "The Verge", "Barron's"]

def gen_news(ticker, n=8):
    items = []
    base_dt = datetime.datetime.utcnow()
    for i in range(n):
        score = round(np.random.uniform(-1, 1), 3)
        dt    = base_dt - datetime.timedelta(hours=random.randint(1, 48))
        items.append(dict(
            headline=random.choice(HEADLINES).replace("{t}", ticker),
            source=random.choice(SOURCES),
            score=score,
            label="Positive" if score > 0.15 else ("Negative" if score < -0.15 else "Neutral"),
            ts=dt.strftime("%b %d · %H:%M"),
        ))
    return sorted(items, key=lambda x: x["ts"], reverse=True)

def gen_sentiment_ts(ticker, n=30):
    np.random.seed(hash(ticker) % 2**31)
    dates  = pd.bdate_range(end=datetime.date.today(), periods=n)
    scores = np.random.uniform(-0.6, 0.8, n)
    # smooth
    scores = pd.Series(scores).ewm(span=5).mean().values
    returns = scores * np.random.uniform(0.3, 0.7, n) + np.random.normal(0, 0.008, n)
    return dates, scores, returns

def make_sentiment_timeline(ticker):
    dates, scores, _ = gen_sentiment_ts(ticker)
    fig = go.Figure()
    colors = [COLORS["green"] if s > 0.1 else (COLORS["red"] if s < -0.1 else COLORS["muted"]) for s in scores]
    fig.add_trace(go.Bar(
        x=dates, y=scores, marker_color=colors, name="Daily Sentiment",
        hovertemplate="%{x|%b %d}<br>Score: %{y:.3f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=pd.Series(scores).rolling(5).mean(),
        mode="lines", line=dict(color=COLORS["accent"], width=2),
        name="5-day MA",
    ))
    fig.add_hline(y=0, line=dict(color=COLORS["border"], width=1))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"]), height=240,
        xaxis=dict(showgrid=False, color=COLORS["muted"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["border"], color=COLORS["muted"], range=[-1, 1]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=10, b=10),
        barmode="overlay",
    )
    return fig

def make_correlation_scatter(ticker):
    dates, scores, returns = gen_sentiment_ts(ticker, n=60)
    corr = np.corrcoef(scores, returns)[0, 1]
    fig = go.Figure(go.Scatter(
        x=scores, y=returns,
        mode="markers",
        marker=dict(
            color=scores, colorscale=[[0,"#ff4d6d"],[0.5,"#64748b"],[1,"#00c98d"]],
            size=7, opacity=0.75, cmid=0,
        ),
        hovertemplate="Sentiment: %{x:.3f}<br>Next-day return: %{y:.2%}<extra></extra>",
    ))
    # Trend line
    m, b = np.polyfit(scores, returns, 1)
    xs   = np.linspace(min(scores), max(scores), 50)
    fig.add_trace(go.Scatter(
        x=xs, y=m*xs+b, mode="lines",
        line=dict(color=COLORS["accent"], width=2, dash="dot"),
        name=f"Trend (r={corr:.2f})",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"]), height=240,
        xaxis=dict(title="Sentiment Score", showgrid=True, gridcolor=COLORS["border"], color=COLORS["muted"]),
        yaxis=dict(title="Next-day Return", showgrid=True, gridcolor=COLORS["border"], color=COLORS["muted"], tickformat=".1%"),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig, corr

def make_news_feed(news):
    items = []
    for n in news:
        badge_cls = "badge-pos" if n["label"] == "Positive" else ("badge-neg" if n["label"] == "Negative" else "badge-neu")
        items.append(html.Div([
            html.Div([
                html.Span(f"{n['score']:+.3f}", className=badge_cls),
            ], style={"flexShrink": "0", "paddingTop": "2px"}),
            html.Div([
                html.P(n["headline"], className="news-headline"),
                html.P(f"{n['source']} · {n['ts']}", className="news-meta"),
            ]),
        ], className="news-item"))
    return html.Div(items)

def agg_metrics(ticker):
    _, scores, returns = gen_sentiment_ts(ticker, 30)
    avg = np.mean(scores)
    pct_pos = np.mean(scores > 0.1) * 100
    corr    = np.corrcoef(scores, returns)[0, 1]
    tiles = [
        ("Avg Sentiment",  f"{avg:+.3f}",    "30-day mean",     "pos" if avg > 0 else "neg"),
        ("% Positive",     f"{pct_pos:.0f}%","Days bullish",    "pos" if pct_pos > 50 else "neg"),
        ("Sentiment–Ret Corr", f"{corr:.3f}", "Predictive power","pos" if corr > 0.1 else ("neg" if corr < -0.1 else "neu")),
    ]
    return [
        html.Div([
            html.Div(label, className="metric-tile-label"),
            html.Div(val,   className="metric-tile-value"),
            html.Div(desc,  className=f"metric-tile-delta {cls}"),
        ], className="metric-tile")
        for label, val, desc, cls in tiles
    ]

# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div([
    html.Div([
        html.Span("Ticker:", className="filter-label"),
        dcc.Dropdown(
            id="sn-ticker", options=[{"label": t, "value": t} for t in TICKERS],
            value="NVDA", clearable=False, style={"width": "130px"},
        ),
    ], className="filter-bar"),

    html.Div(id="sn-metrics", className="metric-grid", style={"marginBottom": "20px"}),

    html.Div([
        html.Div([
            html.Div("FinBERT News Feed", className="dash-card-title"),
            html.Div(id="sn-feed"),
        ], className="dash-card"),
        html.Div([
            html.Div([
                html.Div("30-Day Sentiment Timeline", className="dash-card-title"),
                dcc.Graph(id="sn-timeline", config=dict(displayModeBar=False)),
            ], className="dash-card"),
            html.Div([
                html.Div("Sentiment vs Next-Day Return", className="dash-card-title"),
                dcc.Graph(id="sn-corr", config=dict(displayModeBar=False)),
                html.Div(id="sn-corr-label", style={"marginTop": "8px", "fontSize": "12px", "color": "#64748b", "fontFamily": "JetBrains Mono"}),
            ], className="dash-card"),
        ]),
    ], className="two-col"),
])

@callback(
    Output("sn-metrics",    "children"),
    Output("sn-feed",       "children"),
    Output("sn-timeline",   "figure"),
    Output("sn-corr",       "figure"),
    Output("sn-corr-label", "children"),
    Input("sn-ticker",      "value"),
)
def refresh(ticker):
    random.seed(hash(ticker))
    np.random.seed(hash(ticker) % 2**31)
    news          = gen_news(ticker)
    timeline_fig  = make_sentiment_timeline(ticker)
    corr_fig, corr = make_correlation_scatter(ticker)
    corr_label    = f"Pearson r = {corr:.3f}  ({'positive' if corr > 0 else 'negative'} correlation)"
    return (
        agg_metrics(ticker),
        make_news_feed(news),
        timeline_fig,
        corr_fig,
        corr_label,
    )