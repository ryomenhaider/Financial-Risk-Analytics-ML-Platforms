"""
Page 4 — Portfolio Optimiser
Pie chart of optimal weights, efficient frontier scatter,
Sharpe/Sortino metrics, rebalancing suggestions.
"""

import dash
from dash import html, dcc, Input, Output, callback
import plotly.graph_objects as go
import numpy as np

dash.register_page(__name__, path="/portfolio", name="Portfolio Optimiser")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "GS"]
COLORS  = dict(accent="#00e5ff", green="#00c98d", red="#ff4d6d", orange="#ff8c42",
               surface="#0d1117", surface2="#161b27", border="#1e2738", muted="#64748b", text="#e2e8f0")
PALETTE = ["#00e5ff","#7c3aed","#00c98d","#ff8c42","#ff4d6d","#38bdf8","#a78bfa","#34d399","#fbbf24"]

def simulate_frontier(n_portfolios=600, n_assets=9, seed=42):
    np.random.seed(seed)
    mu    = np.random.uniform(0.06, 0.22, n_assets)
    sigma = np.random.uniform(0.12, 0.35, n_assets)
    corr  = np.eye(n_assets)
    for i in range(n_assets):
        for j in range(i+1, n_assets):
            r = np.random.uniform(0.1, 0.7)
            corr[i,j] = corr[j,i] = r
    cov = np.outer(sigma, sigma) * corr

    vols, rets, sharpes, weights = [], [], [], []
    for _ in range(n_portfolios):
        w = np.random.dirichlet(np.ones(n_assets))
        r = w @ mu
        v = np.sqrt(w @ cov @ w)
        s = r / v
        vols.append(v); rets.append(r); sharpes.append(s); weights.append(w)

    best_idx = int(np.argmax(sharpes))
    return dict(
        vols=vols, rets=rets, sharpes=sharpes,
        opt_vol=vols[best_idx], opt_ret=rets[best_idx], opt_sharpe=sharpes[best_idx],
        opt_weights=weights[best_idx],
        mu=mu, sigma=sigma,
    )

def make_frontier(data):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=data["vols"], y=data["rets"],
        mode="markers",
        marker=dict(
            color=data["sharpes"], colorscale="Turbo",
            size=5, opacity=0.6,
            colorbar=dict(title="Sharpe", tickfont=dict(color=COLORS["muted"]), titlefont=dict(color=COLORS["muted"])),
        ),
        name="Portfolios",
        hovertemplate="Vol: %{x:.1%}<br>Ret: %{y:.1%}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[data["opt_vol"]], y=[data["opt_ret"]],
        mode="markers",
        marker=dict(symbol="star", color=COLORS["accent"], size=16, line=dict(color="white", width=1)),
        name=f"Optimal (Sharpe={data['opt_sharpe']:.2f})",
        hovertemplate=f"Optimal Portfolio<br>Vol: {data['opt_vol']:.1%}<br>Ret: {data['opt_ret']:.1%}<br>Sharpe: {data['opt_sharpe']:.2f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"]), height=360,
        xaxis=dict(title="Volatility (Ann.)", showgrid=True, gridcolor=COLORS["border"], color=COLORS["muted"], tickformat=".0%"),
        yaxis=dict(title="Return (Ann.)",    showgrid=True, gridcolor=COLORS["border"], color=COLORS["muted"], tickformat=".0%"),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COLORS["border"]),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    return fig

def make_pie(weights):
    fig = go.Figure(go.Pie(
        labels=TICKERS,
        values=[round(w, 4) for w in weights],
        hole=0.45,
        marker=dict(colors=PALETTE, line=dict(color="#050810", width=2)),
        textinfo="label+percent",
        textfont=dict(size=12, color="white"),
        hovertemplate="<b>%{label}</b><br>Weight: %{value:.1%}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text"]), height=300,
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        margin=dict(l=0, r=0, t=0, b=0),
        annotations=[dict(text="Optimal", x=0.5, y=0.5, font_size=14, showarrow=False, font_color=COLORS["muted"])],
    )
    return fig

def metrics_tiles(data, current_weights):
    rf = 0.052
    ann_ret   = data["opt_ret"]
    ann_vol   = data["opt_vol"]
    sharpe    = (ann_ret - rf) / ann_vol
    sortino_v = ann_vol * 0.7
    sortino   = (ann_ret - rf) / sortino_v
    max_dd    = np.random.uniform(-0.18, -0.08)
    tiles = [
        ("Sharpe Ratio",  f"{sharpe:.3f}",  "> 1.0 target",    "pos" if sharpe > 1 else "neg"),
        ("Sortino Ratio", f"{sortino:.3f}", "> 1.5 target",    "pos" if sortino > 1.5 else "neg"),
        ("Ann. Return",   f"{ann_ret:.1%}", "Expected",        "pos"),
        ("Ann. Volatility",f"{ann_vol:.1%}","Portfolio risk",  "neu"),
        ("Max Drawdown",  f"{max_dd:.1%}",  "Historical",      "neg"),
    ]
    return [
        html.Div([
            html.Div(label, className="metric-tile-label"),
            html.Div(val,   className="metric-tile-value"),
            html.Div(desc,  className=f"metric-tile-delta {cls}"),
        ], className="metric-tile")
        for label, val, desc, cls in tiles
    ]

def rebalance_table(opt_weights, current_weights):
    rows = []
    for t, opt, cur in zip(TICKERS, opt_weights, current_weights):
        diff  = opt - cur
        cls   = "badge-pos" if diff > 0.005 else ("badge-neg" if diff < -0.005 else "badge-neu")
        label = "BUY" if diff > 0.005 else ("SELL" if diff < -0.005 else "HOLD")
        rows.append(html.Tr([
            html.Td(t), html.Td(f"{cur:.1%}"), html.Td(f"{opt:.1%}"),
            html.Td(f"{diff:+.1%}", className="pos" if diff > 0 else "neg"),
            html.Td(html.Span(label, className=cls)),
        ]))
    return html.Table([
        html.Thead(html.Tr([html.Th(h) for h in ["Ticker","Current","Optimal","Δ Weight","Action"]])),
        html.Tbody(rows),
    ], className="dash-table")

# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div([
    html.Div([
        html.Span("Objective:", className="filter-label"),
        dcc.RadioItems(
            id="po-objective",
            options=[{"label": l, "value": v} for l, v in [("Max Sharpe","sharpe"),("Min Volatility","minvol"),("Max Return","maxret")]],
            value="sharpe", inline=True,
            labelStyle={"marginRight": "14px", "color": "#64748b", "fontSize": "13px"},
        ),
        html.Span("Risk-free rate:", className="filter-label"),
        dcc.Input(id="po-rf", type="number", value=5.2, min=0, max=15, step=0.1,
                  style={"width": "80px", "background": "#161b27", "border": "1px solid #1e2738",
                         "color": "#e2e8f0", "borderRadius": "4px", "padding": "4px 8px"}),
        html.Span("%", style={"color": "#64748b"}),
    ], className="filter-bar"),

    html.Div([
        html.Div([
            html.Div("Optimal Portfolio Weights", className="dash-card-title"),
            dcc.Graph(id="po-pie", config=dict(displayModeBar=False)),
        ], className="dash-card"),
        html.Div([
            html.Div("Efficient Frontier", className="dash-card-title"),
            dcc.Graph(id="po-frontier", config=dict(displayModeBar=True)),
        ], className="dash-card"),
    ], className="two-col"),

    html.Div([
        html.Div("Risk / Return Metrics", className="dash-card-title"),
        html.Div(id="po-metrics", className="metric-grid"),
    ], className="dash-card"),

    html.Div([
        html.Div("Rebalancing Suggestions vs Current Allocation", className="dash-card-title"),
        html.Div(id="po-rebalance"),
    ], className="dash-card"),
])

@callback(
    Output("po-pie",       "figure"),
    Output("po-frontier",  "figure"),
    Output("po-metrics",   "children"),
    Output("po-rebalance", "children"),
    Input("po-objective",  "value"),
    Input("po-rf",         "value"),
)
def refresh(objective, rf):
    data = simulate_frontier()
    # Simulate current (sub-optimal) allocation
    np.random.seed(99)
    current = np.random.dirichlet(np.ones(len(TICKERS)))
    return (
        make_pie(data["opt_weights"]),
        make_frontier(data),
        metrics_tiles(data, current),
        rebalance_table(data["opt_weights"], current),
    )