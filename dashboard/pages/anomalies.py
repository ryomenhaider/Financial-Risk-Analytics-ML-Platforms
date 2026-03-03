"""
Page 2 — Anomaly Dashboard
Candlestick chart with anomaly markers, severity filter,
anomaly timeline, SHAP explanation panel.
"""

import dash
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import datetime

dash.register_page(__name__, path="/anomalies", name="Anomaly Detector")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
COLORS  = dict(accent="#00e5ff", green="#00c98d", red="#ff4d6d", orange="#ff8c42",
               surface="#0d1117", surface2="#161b27", border="#1e2738", muted="#64748b", text="#e2e8f0")

SHAP_FEATURES = ["Volume spike", "Bollinger break", "RSI divergence", "MACD cross", "News sentiment", "Intraday gap"]

def _gen_ohlc(n=120, base=182.0):
    dates  = pd.bdate_range(end=datetime.date.today(), periods=n)
    closes = [base]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + np.random.normal(0, 0.015)))
    opens  = [closes[0]] + closes[:-1]
    highs  = [max(o, c) * (1 + abs(np.random.normal(0, .005))) for o, c in zip(opens, closes)]
    lows   = [min(o, c) * (1 - abs(np.random.normal(0, .005))) for o, c in zip(opens, closes)]
    return pd.DataFrame(dict(date=dates, open=opens, high=highs, low=lows, close=closes))

def _gen_anomalies(df, severity="all"):
    n = len(df)
    idx = sorted(np.random.choice(n, size=max(4, n // 15), replace=False))
    rows = []
    for i in idx:
        sev = np.random.choice(["high", "medium", "low"], p=[.25, .45, .3])
        if severity != "all" and sev != severity:
            continue
        rows.append(dict(
            date=df.iloc[i]["date"],
            price=df.iloc[i]["close"],
            severity=sev,
            score=round(np.random.uniform(0.6, 0.99), 3),
            shap={f: round(np.random.uniform(-1, 1), 3) for f in SHAP_FEATURES},
        ))
    return rows

def make_candle_chart(df, anomalies):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing=dict(line=dict(color=COLORS["green"]), fillcolor=COLORS["green"] + "55"),
        decreasing=dict(line=dict(color=COLORS["red"]),   fillcolor=COLORS["red"]   + "55"),
        name="OHLC",
    ))
    color_map = {"high": COLORS["red"], "medium": COLORS["orange"], "low": COLORS["accent"]}
    symbol_map= {"high": "x-open", "medium": "triangle-up-open", "low": "circle-open"}
    for sev in ["high", "medium", "low"]:
        pts = [a for a in anomalies if a["severity"] == sev]
        if pts:
            fig.add_trace(go.Scatter(
                x=[p["date"] for p in pts],
                y=[p["price"] * 1.025 for p in pts],
                mode="markers",
                marker=dict(symbol=symbol_map[sev], color=color_map[sev], size=12, line=dict(width=2)),
                name=f"{sev.title()} severity",
                customdata=[[p["score"]] for p in pts],
                hovertemplate=f"<b>{sev.title()} Anomaly</b><br>Score: %{{customdata[0]:.3f}}<extra></extra>",
            ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"]), height=380,
        xaxis=dict(showgrid=False, zeroline=False, color=COLORS["muted"], rangeslider=dict(visible=False)),
        yaxis=dict(showgrid=True, gridcolor=COLORS["border"], zeroline=False, color=COLORS["muted"]),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COLORS["border"]),
        margin=dict(l=10, r=10, t=20, b=10),
        hovermode="x unified",
    )
    return fig

def make_timeline(anomalies):
    if not anomalies:
        return go.Figure()
    color_map = {"high": COLORS["red"], "medium": COLORS["orange"], "low": COLORS["accent"]}
    fig = go.Figure()
    for sev in ["high", "medium", "low"]:
        pts = [a for a in anomalies if a["severity"] == sev]
        if pts:
            fig.add_trace(go.Scatter(
                x=[p["date"] for p in pts], y=[p["score"] for p in pts],
                mode="markers+lines",
                marker=dict(color=color_map[sev], size=8),
                line=dict(color=color_map[sev], width=1, dash="dot"),
                name=sev.title(),
            ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"]), height=160,
        xaxis=dict(showgrid=False, color=COLORS["muted"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["border"], color=COLORS["muted"],
                   title="Anomaly Score", range=[0, 1]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig

def shap_panel(anomaly):
    if not anomaly:
        return html.P("Click an anomaly marker to see SHAP explanation.", style={"color": COLORS["muted"], "fontSize": "13px"})
    shap  = anomaly["shap"]
    total = sum(abs(v) for v in shap.values())
    items = sorted(shap.items(), key=lambda x: abs(x[1]), reverse=True)
    bars  = []
    for feat, val in items:
        pct   = abs(val) / total * 100
        color = COLORS["green"] if val > 0 else COLORS["red"]
        bars.append(html.Div([
            html.Div(feat,  className="shap-feature"),
            html.Div(html.Div(style={"width": f"{pct:.0f}%", "background": color}, className="shap-bar-fill"), className="shap-bar-bg"),
            html.Div(f"{val:+.3f}", className="shap-val", style={"color": color}),
        ], className="shap-bar-wrap"))
    badge_cls = f"badge-sev-{anomaly['severity']}"
    return html.Div([
        html.Div([
            html.Strong(f"Anomaly — {str(anomaly['date'])[:10]}", style={"color": COLORS["text"]}),
            html.Span(anomaly["severity"].title(), className=badge_cls, style={"marginLeft": "10px"}),
            html.Span(f"Score: {anomaly['score']:.3f}", style={"color": COLORS["muted"], "fontSize": "12px", "marginLeft": "10px", "fontFamily": "JetBrains Mono"}),
        ], style={"marginBottom": "14px"}),
        *bars,
    ])

# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div([
    # Filter bar
    html.Div([
        html.Span("Ticker:", className="filter-label"),
        dcc.Dropdown(
            id="an-ticker", options=[{"label": t, "value": t} for t in TICKERS],
            value="AAPL", clearable=False,
            style={"width": "130px", "background": "#161b27"},
        ),
        html.Span("Severity:", className="filter-label"),
        dcc.RadioItems(
            id="an-severity",
            options=[{"label": s.title(), "value": s} for s in ["all", "high", "medium", "low"]],
            value="all", inline=True,
            labelStyle={"marginRight": "14px", "color": "#64748b", "fontSize": "13px"},
        ),
    ], className="filter-bar"),

    # Candlestick chart
    html.Div([
        html.Div("Candlestick · Anomaly Markers", className="dash-card-title"),
        dcc.Graph(id="an-candle", config=dict(displayModeBar=True)),
    ], className="dash-card"),

    # Timeline
    html.Div([
        html.Div("Anomaly Timeline", className="dash-card-title"),
        dcc.Graph(id="an-timeline", config=dict(displayModeBar=False)),
    ], className="dash-card"),

    # Table + SHAP
    html.Div([
        html.Div([
            html.Div("Detected Anomalies", className="dash-card-title"),
            html.Div(id="an-table"),
        ], className="dash-card"),
        html.Div([
            html.Div("SHAP Feature Importance", className="dash-card-title"),
            html.Div(id="an-shap"),
        ], className="dash-card"),
    ], className="two-col"),
])

_store = {}  # server-side cache keyed by ticker

@callback(
    Output("an-candle",   "figure"),
    Output("an-timeline", "figure"),
    Output("an-table",    "children"),
    Output("an-shap",     "children"),
    Input("an-ticker",    "value"),
    Input("an-severity",  "value"),
)
def refresh(ticker, severity):
    np.random.seed(hash(ticker) % 2**31)
    df = _gen_ohlc(120, base={"AAPL":182,"MSFT":415,"GOOGL":175,"AMZN":195,"NVDA":875}[ticker])
    all_anoms = _gen_anomalies(df, "all")
    _store["anomalies"] = all_anoms
    filtered  = [a for a in all_anoms if severity == "all" or a["severity"] == severity]

    candle   = make_candle_chart(df, filtered)
    timeline = make_timeline(filtered)

    # Table
    rows = [html.Tr([
        html.Td(str(a["date"])[:10]),
        html.Td(f"${a['price']:.2f}"),
        html.Td(html.Span(a["severity"].title(), className=f"badge-sev-{a['severity']}")),
        html.Td(f"{a['score']:.3f}", style={"fontFamily":"JetBrains Mono"}),
    ]) for a in filtered]
    table = html.Table([
        html.Thead(html.Tr([html.Th(h) for h in ["Date","Price","Severity","Score"]])),
        html.Tbody(rows),
    ], className="dash-table")

    # SHAP — use first anomaly as default
    shap = shap_panel(filtered[0] if filtered else None)
    return candle, timeline, table, shap