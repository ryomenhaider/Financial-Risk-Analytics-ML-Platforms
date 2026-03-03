"""
Page 1 — Market Overview
Live prices table, 1-day sparklines, market breadth gauge, top movers, sentiment heatmap.
Refreshes every 60 seconds via dcc.Interval.
"""

import dash
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
import datetime, random

dash.register_page(__name__, path="/overview", name="Market Overview")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "GS", "SPY"]
COLORS  = dict(accent="#00e5ff", green="#00c98d", red="#ff4d6d", surface="#0d1117", surface2="#161b27", border="#1e2738", muted="#64748b", text="#e2e8f0")

# ── Helpers ───────────────────────────────────────────────────────────────────
def _rng_price(base, n=78):
    """Simulate n intraday ticks starting from base."""
    prices = [base]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + np.random.normal(0, 0.003)))
    return prices

def generate_market_data():
    bases = dict(AAPL=182, MSFT=415, GOOGL=175, AMZN=195, NVDA=875, META=520,
                 TSLA=248, JPM=198, GS=462, SPY=510)
    rows = []
    for t in TICKERS:
        prices = _rng_price(bases[t])
        chg    = (prices[-1] - prices[0]) / prices[0] * 100
        rows.append(dict(
            ticker=t, price=round(prices[-1], 2),
            change=round(chg, 2),
            volume=random.randint(5_000_000, 80_000_000),
            mktcap=round(bases[t] * random.uniform(5e9, 3e12) / 1e12, 2),
            sparkline=prices,
        ))
    return rows

def make_sparkline(prices, color):
    fig = go.Figure(go.Scatter(
        y=prices, mode="lines",
        line=dict(color=color, width=1.5),
        fill="tozeroy",
        fillcolor=color.replace(")", ", 0.1)").replace("rgb", "rgba") if "rgb" in color else color + "22",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", xaxis=dict(visible=False), yaxis=dict(visible=False),
        height=40, width=120,
    )
    return fig

def make_breadth_gauge(pct_up):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct_up,
        number=dict(suffix="%", font=dict(color=COLORS["text"], size=28, family="JetBrains Mono")),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=COLORS["muted"], tickfont=dict(color=COLORS["muted"])),
            bar=dict(color=COLORS["accent"]),
            bgcolor=COLORS["surface2"],
            bordercolor=COLORS["border"],
            steps=[
                dict(range=[0,  40], color="rgba(255,77,109,.15)"),
                dict(range=[40, 60], color="rgba(100,116,139,.1)"),
                dict(range=[60,100], color="rgba(0,201,141,.15)"),
            ],
            threshold=dict(line=dict(color=COLORS["accent"], width=2), thickness=.75, value=pct_up),
        ),
        title=dict(text="Market Breadth — % Advancing", font=dict(color=COLORS["muted"], size=11)),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font_color=COLORS["text"],
        height=220, margin=dict(l=20, r=20, t=40, b=10),
    )
    return fig

def make_sentiment_heatmap(data):
    tickers = [d["ticker"] for d in data]
    values  = [d["change"] for d in data]
    fig = go.Figure(go.Treemap(
        labels=tickers, parents=[""] * len(tickers),
        values=[abs(v) + 1 for v in values],
        customdata=list(zip(tickers, values)),
        hovertemplate="<b>%{customdata[0]}</b><br>Change: %{customdata[1]:+.2f}%<extra></extra>",
        marker=dict(
            colors=values,
            colorscale=[[0, "#ff4d6d"], [0.5, "#161b27"], [1, "#00c98d"]],
            cmid=0,
            line=dict(color="#050810", width=2),
        ),
        texttemplate="<b>%{label}</b><br>%{customdata[1]:+.2f}%",
        textfont=dict(color="white", size=13),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=0, b=0),
        height=220,
    )
    return fig

# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div([
    dcc.Interval(id="ov-refresh", interval=60_000, n_intervals=0),

    # Metric tiles (filled by callback)
    html.Div(id="ov-metrics", className="metric-grid"),

    html.Div([
        # Prices table
        html.Div([
            html.Div("Live Prices", className="dash-card-title"),
            html.Div(id="ov-table"),
        ], className="dash-card"),

        # Right column: gauge + heatmap
        html.Div([
            html.Div([
                html.Div("Market Breadth", className="dash-card-title"),
                dcc.Graph(id="ov-gauge", config=dict(displayModeBar=False)),
            ], className="dash-card"),
            html.Div([
                html.Div("Sentiment Heatmap", className="dash-card-title"),
                dcc.Graph(id="ov-heatmap", config=dict(displayModeBar=False)),
            ], className="dash-card"),
        ]),
    ], className="two-col"),

    # Top movers
    html.Div([
        html.Div("Top Movers", className="dash-card-title"),
        html.Div(id="ov-movers"),
    ], className="dash-card"),
])

# ── Callbacks ─────────────────────────────────────────────────────────────────
@callback(
    Output("ov-metrics",  "children"),
    Output("ov-table",    "children"),
    Output("ov-gauge",    "figure"),
    Output("ov-heatmap",  "figure"),
    Output("ov-movers",   "children"),
    Input("ov-refresh",   "n_intervals"),
)
def refresh(_):
    data = generate_market_data()
    advances = sum(1 for d in data if d["change"] > 0)
    pct_up   = round(advances / len(data) * 100, 1)

    # ── Metric tiles ──────────────────────────────────────────────────────────
    spy    = next(d for d in data if d["ticker"] == "SPY")
    best   = max(data, key=lambda x: x["change"])
    worst  = min(data, key=lambda x: x["change"])
    vol    = sum(d["volume"] for d in data)
    tiles  = [
        ("SPY",      f"${spy['price']}", f"{spy['change']:+.2f}%", "pos" if spy['change']>=0 else "neg"),
        ("Advancing",f"{advances}/{len(data)}", f"{pct_up}% up",  "pos" if pct_up > 50 else "neg"),
        ("Best",     best["ticker"],     f"+{best['change']:.2f}%","pos"),
        ("Worst",    worst["ticker"],    f"{worst['change']:.2f}%","neg"),
        ("Volume",   f"{vol/1e9:.1f}B",  "shares traded",          "neu"),
    ]
    metric_els = [
        html.Div([
            html.Div(label,  className="metric-tile-label"),
            html.Div(value,  className="metric-tile-value"),
            html.Div(delta,  className=f"metric-tile-delta {cls}"),
        ], className="metric-tile")
        for label, value, delta, cls in tiles
    ]

    # ── Prices table ──────────────────────────────────────────────────────────
    rows = []
    for d in data:
        color  = COLORS["green"] if d["change"] >= 0 else COLORS["red"]
        spark  = make_sparkline(d["sparkline"], color)
        badge  = "badge-pos" if d["change"] >= 0 else "badge-neg"
        rows.append(html.Tr([
            html.Td(html.Strong(d["ticker"]), style={"color": COLORS["text"]}),
            html.Td(f"${d['price']:,.2f}"),
            html.Td(html.Span(f"{d['change']:+.2f}%", className=badge)),
            html.Td(f"{d['volume']/1e6:.1f}M"),
            html.Td(f"${d['mktcap']:.2f}T"),
            html.Td(dcc.Graph(figure=spark, config=dict(displayModeBar=False), style=dict(height="40px", width="120px"))),
        ]))
    table = html.Table([
        html.Thead(html.Tr([html.Th(h) for h in ["Ticker","Price","Change","Volume","Mkt Cap","1D Spark"]])),
        html.Tbody(rows),
    ], className="dash-table")

    # ── Top movers ────────────────────────────────────────────────────────────
    sorted_data  = sorted(data, key=lambda x: x["change"], reverse=True)
    gainers = sorted_data[:3]
    losers  = sorted_data[-3:][::-1]
    mover_els = []
    for label, items, cls in [("Gainers", gainers, "pos"), ("Losers", losers, "neg")]:
        mover_els.append(html.Div([
            html.Div(label, className=f"dash-card-title {cls}"),
            html.Div([
                html.Div([
                    html.Strong(d["ticker"], style={"color": COLORS["text"], "marginRight": "10px"}),
                    html.Span(f"{d['change']:+.2f}%", className=f"badge-{'pos' if d['change']>0 else 'neg'}"),
                ], style={"padding": "8px 0", "borderBottom": f"1px solid {COLORS['border']}"})
                for d in items
            ]),
        ], style={"flex": "1"}))
    movers_layout = html.Div(mover_els, style={"display": "flex", "gap": "40px"})

    return metric_els, table, make_breadth_gauge(pct_up), make_sentiment_heatmap(data), movers_layout