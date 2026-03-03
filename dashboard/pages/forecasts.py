"""
Page 3 — Price Forecasts
Actual vs predicted line chart with confidence band,
ticker / horizon selector, model accuracy metrics.
"""

import dash
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import datetime

dash.register_page(__name__, path="/forecasts", name="Price Forecasts")

TICKERS  = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
HORIZONS = [7, 30, 90]
COLORS   = dict(accent="#00e5ff", green="#00c98d", red="#ff4d6d",
                surface="#0d1117", surface2="#161b27", border="#1e2738", muted="#64748b", text="#e2e8f0")

BASES = dict(AAPL=182, MSFT=415, GOOGL=175, AMZN=195, NVDA=875, META=520, TSLA=248)

def gen_series(ticker, horizon):
    np.random.seed(hash(ticker + str(horizon)) % 2**31)
    base = BASES[ticker]
    hist_n = 90
    hist_dates  = pd.bdate_range(end=datetime.date.today(), periods=hist_n)
    hist_prices = [base]
    for _ in range(hist_n - 1):
        hist_prices.append(hist_prices[-1] * (1 + np.random.normal(0.0003, 0.015)))

    # In-sample predictions (last 30 days of history)
    insample_n = 30
    insample_pred = [p * (1 + np.random.normal(0, 0.007)) for p in hist_prices[-insample_n:]]

    # Out-of-sample forecast
    fcast_dates = pd.bdate_range(start=hist_dates[-1] + pd.Timedelta(days=1), periods=horizon)
    drift = np.random.normal(0.0002, 0.0005)
    fcast_mu = [hist_prices[-1]]
    for _ in range(horizon - 1):
        fcast_mu.append(fcast_mu[-1] * (1 + np.random.normal(drift, 0.012)))
    # Widening CI
    ci_width = [p * 0.015 * np.sqrt(i + 1) for i, p in enumerate(fcast_mu)]
    ci_upper = [m + w for m, w in zip(fcast_mu, ci_width)]
    ci_lower = [m - w for m, w in zip(fcast_mu, ci_width)]

    # Accuracy metrics
    actuals   = hist_prices[-insample_n:]
    mae   = np.mean(np.abs(np.array(actuals) - np.array(insample_pred)))
    rmse  = np.sqrt(np.mean((np.array(actuals) - np.array(insample_pred)) ** 2))
    mape  = np.mean(np.abs((np.array(actuals) - np.array(insample_pred)) / np.array(actuals))) * 100
    r2    = 1 - np.sum((np.array(actuals) - np.array(insample_pred))**2) / np.sum((np.array(actuals) - np.mean(actuals))**2)

    return dict(
        hist_dates=hist_dates, hist_prices=hist_prices,
        insample_dates=hist_dates[-insample_n:], insample_pred=insample_pred,
        fcast_dates=fcast_dates, fcast_mu=fcast_mu,
        ci_upper=ci_upper, ci_lower=ci_lower,
        mae=mae, rmse=rmse, mape=mape, r2=r2,
    )

def make_forecast_chart(data):
    fig = go.Figure()

    # Actual history (blue line)
    fig.add_trace(go.Scatter(
        x=data["hist_dates"], y=data["hist_prices"],
        mode="lines", name="Actual",
        line=dict(color="#00e5ff", width=2),
    ))

    # In-sample prediction (dashed)
    fig.add_trace(go.Scatter(
        x=data["insample_dates"], y=data["insample_pred"],
        mode="lines", name="In-sample fit",
        line=dict(color="#7c3aed", width=1.5, dash="dot"),
    ))

    # CI band (shaded)
    fig.add_trace(go.Scatter(
        x=list(data["fcast_dates"]) + list(data["fcast_dates"])[::-1],
        y=list(data["ci_upper"]) + list(data["ci_lower"])[::-1],
        fill="toself", fillcolor="rgba(0,229,255,0.08)",
        line=dict(color="rgba(0,0,0,0)"), name="95% CI",
        hoverinfo="skip",
    ))

    # Forecast mean (grey)
    fig.add_trace(go.Scatter(
        x=data["fcast_dates"], y=data["fcast_mu"],
        mode="lines", name="Forecast",
        line=dict(color="#94a3b8", width=2, dash="dash"),
    ))

    # Divider line
    fig.add_vline(
        x=str(data["hist_dates"][-1])[:10],
        line=dict(color="#64748b", width=1, dash="dot"),
        annotation_text="Forecast start",
        annotation_font=dict(color="#64748b", size=11),
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"]), height=420,
        xaxis=dict(showgrid=False, color=COLORS["muted"]),
        yaxis=dict(showgrid=True, gridcolor=COLORS["border"], color=COLORS["muted"]),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COLORS["border"]),
        margin=dict(l=10, r=10, t=20, b=10),
        hovermode="x unified",
    )
    return fig

def make_metrics(data):
    tiles = [
        ("MAE",  f"${data['mae']:.2f}",  "Mean Abs Error",     "neu"),
        ("RMSE", f"${data['rmse']:.2f}", "Root Mean Sq Error", "neg" if data["rmse"] > 5 else "pos"),
        ("MAPE", f"{data['mape']:.2f}%", "Mean Abs % Error",   "neg" if data["mape"] > 3 else "pos"),
        ("R²",   f"{data['r2']:.4f}",    "Coeff of Determination", "pos" if data["r2"] > 0.9 else "neg"),
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
            id="fc-ticker", options=[{"label": t, "value": t} for t in TICKERS],
            value="AAPL", clearable=False, style={"width": "130px"},
        ),
        html.Span("Horizon:", className="filter-label"),
        dcc.RadioItems(
            id="fc-horizon",
            options=[{"label": f"{h}d", "value": h} for h in HORIZONS],
            value=30, inline=True,
            labelStyle={"marginRight": "14px", "color": "#64748b", "fontSize": "13px"},
        ),
    ], className="filter-bar"),

    html.Div([
        html.Div("Actual vs Forecast · Confidence Band", className="dash-card-title"),
        dcc.Graph(id="fc-chart", config=dict(displayModeBar=True)),
        html.Div([
            html.Div(className="ci-box"),
            html.Span("95% Confidence Interval"),
        ], className="ci-legend"),
    ], className="dash-card"),

    html.Div([
        html.Div("Model Accuracy Metrics — In-Sample (Last 30 Days)", className="dash-card-title"),
        html.Div(id="fc-metrics", className="metric-grid"),
    ], className="dash-card"),
])

@callback(
    Output("fc-chart",   "figure"),
    Output("fc-metrics", "children"),
    Input("fc-ticker",   "value"),
    Input("fc-horizon",  "value"),
)
def refresh(ticker, horizon):
    data = gen_series(ticker, horizon)
    return make_forecast_chart(data), make_metrics(data)