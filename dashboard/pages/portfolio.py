import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import dash, requests
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from collections import defaultdict
from dashboard.theme import COLORS, PLOT_BASE, API_BASE, HEADERS

dash.register_page(__name__, path="/portfolio", name="Capital Allocation", order=3)

TICKERS = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'GOOGL']
RISK_FREE = 0.05
TRADING_DAYS = 252

METHOD_OPTIONS = [
    {"label": "Blended (40/40/20)", "value": "Blended"},
    {"label": "MPT (Max Sharpe)",   "value": "mpt"},
    {"label": "Black-Litterman",    "value": "black_litterman"},
    {"label": "Kelly Criterion",    "value": "kelly"},
]


def _rcard(label, val_id, accent):
    return html.Div([
        html.Div(label, style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                                "letter Spacing":"2px","color":COLORS["dim"],"marginBottom":"4px"}),
        html.Div(id=val_id, children="—",
                 style={"fontFamily":"'IBM Plex Mono',monospace","fontWeight":"600",
                        "fontSize":"22px","color":accent}),
    ], style={"background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
               "borderTop":f"2px solid {accent}","borderRadius":"6px",
               "padding":"14px 20px","flex":"1","minWidth":"120px"})


def _th():
    return {"fontSize":"9px","color":COLORS["dim"],"letterSpacing":"1.5px",
            "padding":"5px 6px","textAlign":"left",
            "borderBottom":f"1px solid {COLORS['border']}"}

def _td(color):
    return {"fontFamily":"'IBM Plex Mono',monospace","fontSize":"11px","color":color,
            "padding":"6px 6px","borderBottom":f"1px solid {COLORS['border']}22"}

def _placeholder(msg):
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False,
                       font=dict(color=COLORS["muted"], size=12,
                                 family="'IBM Plex Mono',monospace"))
    fig.update_layout(**PLOT_BASE, height=260)
    return fig


layout = html.Div([
    html.Div([
        html.Div([
            html.Span("CAPITAL ALLOCATION ENGINE",
                      style={"fontFamily":"'IBM Plex Mono',monospace","fontWeight":"600",
                              "fontSize":"13px","color":COLORS["text"],"letterSpacing":"3px"}),
            html.Div("MPT  ·  Black-Litterman  ·  Kelly Criterion  ·  40 / 40 / 20 Blend",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                             "color":COLORS["dim"],"marginTop":"3px"}),
        ]),
        dcc.Dropdown(id="pa-method", options=METHOD_OPTIONS, value="Blended",
                     clearable=False,
                     style={"width":"220px","fontFamily":"'IBM Plex Mono',monospace",
                            "fontSize":"12px","background":COLORS["elevated"],
                            "border":f"1px solid {COLORS['border']}"}),
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"flex-start",
              "marginBottom":"24px"}),

    html.Div([
        _rcard("SHARPE RATIO",   "pa-sharpe",  COLORS["green"]),
        _rcard("VAR (95%)",      "pa-var",     COLORS["red"]),
        _rcard("MAX DRAWDOWN",   "pa-mdd",     COLORS["amber"]),
        _rcard("PORTFOLIO BETA", "pa-beta",    COLORS["blue"]),
        _rcard("SORTINO",        "pa-sortino", COLORS["purple"]),
    ], style={"display":"flex","gap":"12px","marginBottom":"20px","flexWrap":"wrap"}),

    html.Div([
        html.Div([
            html.Div("WEIGHT COMPARISON  — MPT  ·  BL  ·  KELLY",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="circle", color=COLORS["blue"], children=[
                dcc.Graph(id="pa-bar-chart", config={"displayModeBar":False},
                          style={"height":"340px"}),
            ]),
        ], style={"flex":"2","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),

        html.Div([
            html.Div("ALLOCATION TREEMAP",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                dcc.Graph(id="pa-treemap", config={"displayModeBar":False},
                          style={"height":"310px"}),
            ]),
        ], style={"flex":"1","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
    ], style={"display":"flex","gap":"16px","marginBottom":"16px"}),

    html.Div([
        html.Div([
            html.Div("EFFICIENT FRONTIER",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                dcc.Graph(id="pa-frontier", config={"displayModeBar":False},
                          style={"height":"280px"}),
            ]),
        ], style={"flex":"1","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),

        html.Div([
            html.Div("PORTFOLIO WEIGHTS TABLE",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                html.Div(id="pa-rebalance-table",
                         style={"maxHeight":"280px","overflowY":"auto"}),
            ]),
        ], style={"width":"380px","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
    ], style={"display":"flex","gap":"16px"}),
])


def _compute_kpis(weights_dict: dict, method: str) -> dict:
    """Fetch price history and compute portfolio risk metrics."""
    try:
        prices = {}
        for ticker in weights_dict:
            r = requests.get(f"{API_BASE}/prices/{ticker}/history",
                             params={"limit": 252}, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                d = pd.DataFrame(r.json())
                if not d.empty:
                    d["date"] = pd.to_datetime(d["date"])
                    d = d.sort_values("date").set_index("date")
                    prices[ticker] = d["close"]

        if len(prices) < 2:
            return {}

        price_df  = pd.DataFrame(prices).dropna()
        returns   = np.log(price_df / price_df.shift(1)).dropna()

        w = np.array([weights_dict.get(t, 0) for t in price_df.columns])
        w = w / w.sum() if w.sum() > 0 else w

        port_returns = returns @ w

        # Sharpe
        ann_ret = port_returns.mean() * TRADING_DAYS
        ann_vol = port_returns.std() * np.sqrt(TRADING_DAYS)
        sharpe  = (ann_ret - RISK_FREE) / ann_vol if ann_vol > 0 else 0

        # VaR 95%
        var_95 = np.percentile(port_returns, 5)

        # Max drawdown
        cum = (1 + port_returns).cumprod()
        roll_max = cum.cummax()
        drawdown = (cum - roll_max) / roll_max
        mdd = drawdown.min()

        # Sortino
        downside = port_returns[port_returns < 0].std() * np.sqrt(TRADING_DAYS)
        sortino  = (ann_ret - RISK_FREE) / downside if downside > 0 else 0

        # Beta vs SPY (approximate with equal-weight market)
        market_ret = returns.mean(axis=1)
        cov   = np.cov(port_returns, market_ret)
        beta  = cov[0, 1] / cov[1, 1] if cov[1, 1] > 0 else 1.0

        return {
            "sharpe":  f"{sharpe:.2f}",
            "var":     f"{var_95*100:.2f}%",
            "mdd":     f"{mdd*100:.1f}%",
            "beta":    f"{beta:.2f}",
            "sortino": f"{sortino:.2f}",
        }
    except Exception:
        return {}


@callback(
    [Output("pa-bar-chart",       "figure"),
     Output("pa-treemap",         "figure"),
     Output("pa-frontier",        "figure"),
     Output("pa-rebalance-table", "children"),
     Output("pa-sharpe",          "children"),
     Output("pa-var",             "children"),
     Output("pa-mdd",             "children"),
     Output("pa-beta",            "children"),
     Output("pa-sortino",         "children")],
    [Input("pa-method", "value")],
)
def update_portfolio(method):
    empty    = _placeholder("No data")
    defaults = (empty,) * 3 + (html.Div("No data"),) + ("—",) * 5

    # ── Fetch weights ─────────────────────────────────────────────────────────
    try:
        rw = requests.get(f"{API_BASE}/portfolio/weights",
                          headers=HEADERS, timeout=6)
        weights_list = rw.json() if rw.status_code == 200 else []
        if not isinstance(weights_list, list):
            weights_list = []
    except Exception:
        weights_list = []

    if not weights_list:
        return defaults

    # Group by method → {method: {ticker: weight}}
    by_method = defaultdict(dict)
    for row in weights_list:
        if isinstance(row, dict):
            m = row.get("method", "unknown")
            t = row.get("ticker", "")
            w = float(row.get("weight", 0))
            if t:
                by_method[m][t] = w

    # ── Bar chart — all methods side by side ──────────────────────────────────
    palette = {
        "mpt":              COLORS["blue"],
        "black_litterman":  COLORS["green"],
        "kelly":            COLORS["amber"],
        "Blended":          COLORS["purple"],
    }
    all_tickers = sorted({t for d in by_method.values() for t in d})

    fig_bar = go.Figure()
    if by_method and all_tickers:
        for m, d in by_method.items():
            fig_bar.add_trace(go.Bar(
                name=m.upper(), x=all_tickers,
                y=[d.get(t, 0) * 100 for t in all_tickers],
                marker_color=palette.get(m, COLORS["blue"]), opacity=0.85,
            ))
        fig_bar.update_layout(
            **PLOT_BASE, barmode="group", height=300,
            yaxis_title="Weight (%)",
            title=dict(text="ALLOCATION BY METHOD",
                       font=dict(size=11, color=COLORS["muted"])),
        )
    else:
        fig_bar = _placeholder("No weight data")

    # ── Treemap — selected method ─────────────────────────────────────────────
    selected = by_method.get(method) or \
               (list(by_method.values())[0] if by_method else {})

    if selected:
        labels = list(selected.keys())
        values = [v * 100 for v in selected.values()]
        fig_tree = go.Figure(go.Treemap(
            labels=labels, parents=[""]*len(labels), values=values,
            textinfo="label+percent root",
            textfont=dict(family="'IBM Plex Mono',monospace", size=12,
                          color=COLORS["text"]),
            marker=dict(
                colors=values,
                colorscale=[[0, COLORS["border"]], [1, COLORS["blue"]]],
                line=dict(width=2, color=COLORS["bg"]),
            ),
        ))
        fig_tree.update_layout(
            paper_bgcolor=COLORS["card"],
            margin=dict(l=0, r=0, t=0, b=0),
            height=280,
        )
    else:
        fig_tree = _placeholder("No allocation data")

    # ── Efficient frontier (simulated) ────────────────────────────────────────
    fig_ef = _placeholder("Fetching frontier…")
    try:
        prices = {}
        for ticker in all_tickers:
            r = requests.get(f"{API_BASE}/prices/{ticker}/history",
                             params={"limit": 252}, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                d = pd.DataFrame(r.json())
                if not d.empty:
                    d["date"] = pd.to_datetime(d["date"])
                    prices[ticker] = d.sort_values("date").set_index("date")["close"]

        if len(prices) >= 2:
            price_df = pd.DataFrame(prices).dropna()
            returns  = np.log(price_df / price_df.shift(1)).dropna()
            mu  = returns.mean() * TRADING_DAYS
            cov = returns.cov() * TRADING_DAYS
            n   = len(mu)

            # Monte Carlo frontier
            vols, rets = [], []
            for _ in range(400):
                w = np.random.dirichlet(np.ones(n))
                vols.append(np.sqrt(w @ cov @ w))
                rets.append(w @ mu)

            fig_ef = go.Figure()
            fig_ef.add_trace(go.Scatter(
                x=[v*100 for v in vols], y=[r*100 for r in rets],
                mode="markers",
                marker=dict(size=4, color=rets,
                            colorscale="Viridis", opacity=0.6),
                name="Random Portfolios",
            ))

            # Plot each method's position
            for m, d in by_method.items():
                w = np.array([d.get(t, 0) for t in price_df.columns])
                if w.sum() > 0:
                    w /= w.sum()
                    vol = np.sqrt(w @ cov @ w) * 100
                    ret = (w @ mu) * 100
                    fig_ef.add_trace(go.Scatter(
                        x=[vol], y=[ret], mode="markers+text",
                        name=m.upper(),
                        text=[m.upper()],
                        textposition="top center",
                        textfont=dict(size=9, color=palette.get(m, COLORS["blue"])),
                        marker=dict(size=12, color=palette.get(m, COLORS["blue"]),
                                    symbol="star"),
                    ))

            fig_ef.update_layout(
                **PLOT_BASE, height=260,
                xaxis_title="Volatility (%)",
                yaxis_title="Expected Return (%)",
                title=dict(text="EFFICIENT FRONTIER",
                           font=dict(size=11, color=COLORS["muted"])),
            )
    except Exception:
        pass

    # ── Weights table ─────────────────────────────────────────────────────────
    method_colors = {"mpt": COLORS["blue"], "black_litterman": COLORS["green"],
                     "kelly": COLORS["amber"], "Blended": COLORS["purple"]}
    display_rows = [r for r in weights_list if r.get("method") == method] or weights_list
    rows = []
    for row in sorted(display_rows, key=lambda x: x.get("weight", 0), reverse=True):
        m   = row.get("method", "—")
        col = method_colors.get(m, COLORS["muted"])
        rows.append(html.Tr([
            html.Td(row.get("ticker", "—"), style=_td(COLORS["text"])),
            html.Td(f"{row.get('weight',0)*100:.1f}%", style=_td(COLORS["blue"])),
            html.Td(html.Span(m.upper(), style={
                "background": col+"22", "color": col,
                "border": f"1px solid {col}44", "borderRadius":"3px",
                "padding":"1px 6px","fontFamily":"'IBM Plex Mono',monospace",
                "fontSize":"9px","letterSpacing":"1px",
            }), style={"padding":"5px 6px","borderBottom":f"1px solid {COLORS['border']}22"}),
            html.Td(str(row.get("calculated_at","—"))[:10], style=_td(COLORS["dim"])),
        ]))

    weights_table = html.Table(
        [html.Thead(html.Tr([
            html.Th("TICKER",     style=_th()),
            html.Th("WEIGHT",     style=_th()),
            html.Th("METHOD",     style=_th()),
            html.Th("CALCULATED", style=_th()),
        ]))] + [html.Tbody(rows)],
        style={"width":"100%","borderCollapse":"collapse",
               "fontFamily":"'IBM Plex Mono',monospace"},
    ) if rows else html.Div("No weights", style={"color":COLORS["dim"],
                                                   "fontFamily":"'IBM Plex Mono',monospace",
                                                   "fontSize":"11px","padding":"12px"})

    # ── KPIs ──────────────────────────────────────────────────────────────────
    kpis = _compute_kpis(selected, method) if selected else {}

    return (
        fig_bar, fig_tree, fig_ef, weights_table,
        kpis.get("sharpe",  "—"),
        kpis.get("var",     "—"),
        kpis.get("mdd",     "—"),
        kpis.get("beta",    "—"),
        kpis.get("sortino", "—"),
    )