import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dash, requests
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
from collections import defaultdict
from dashboard.theme import COLORS, PLOT_BASE, API_BASE, HEADERS  # ✅ theme not app

dash.register_page(__name__, path="/portfolio", name="Capital Allocation", order=3)

METHOD_OPTIONS = [
    {"label":"Blended (40/40/20)","value":"blended"},
    {"label":"MPT (Max Sharpe)",  "value":"mpt"},
    {"label":"Black-Litterman",   "value":"bl"},
    {"label":"Kelly Criterion",   "value":"kelly"},
]

def _rcard(label, val_id, accent):
    return html.Div([
        html.Div(label, style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                                "letterSpacing":"2px","color":COLORS["dim"],"marginBottom":"4px"}),
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
        dcc.Dropdown(id="pa-method", options=METHOD_OPTIONS, value="blended",
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


@callback(
    [Output("pa-bar-chart",      "figure"),
     Output("pa-treemap",        "figure"),
     Output("pa-frontier",       "figure"),
     Output("pa-rebalance-table","children"),
     Output("pa-sharpe",         "children"),
     Output("pa-var",            "children"),
     Output("pa-mdd",            "children"),
     Output("pa-beta",           "children"),
     Output("pa-sortino",        "children")],
    [Input("pa-method","value")],
)
def update_portfolio(method):
    empty = _placeholder("No data")
    defaults = (empty,)*3 + (html.Div("No data"),) + ("—",)*5

    # ── 1. Fetch weights from your actual endpoint ────────────────────────────
    # GET /portfolio/weights → returns list of
    # {"id", "ticker", "weight", "method", "calculated_at", "created_at"}
    try:
        rw = requests.get(f"{API_BASE}/portfolio/weights",
                          headers=HEADERS, timeout=6)
        weights_list = rw.json() if rw.status_code == 200 else []
        if not isinstance(weights_list, list):
            weights_list = []
    except Exception:
        weights_list = []

    # Group weights by method → {"mpt": {"AAPL": 0.2, ...}, "bl": {...}, ...}
    by_method = defaultdict(dict)
    for row in weights_list:
        if isinstance(row, dict):
            m = row.get("method", "unknown")
            t = row.get("ticker", "")
            w = row.get("weight", 0)
            if t:
                by_method[m][t] = float(w)

    # ── 2. Bar chart — side by side per method ────────────────────────────────
    palette  = {"mpt":COLORS["blue"],"bl":COLORS["green"],
                "kelly":COLORS["amber"],"blended":COLORS["purple"]}
    all_tickers = sorted(set(t for d in by_method.values() for t in d))

    fig_bar = go.Figure()
    if by_method and all_tickers:
        for m, d in by_method.items():
            fig_bar.add_trace(go.Bar(
                name=m.upper(), x=all_tickers,
                y=[d.get(t, 0) * 100 for t in all_tickers],
                marker_color=palette.get(m, COLORS["blue"]), opacity=0.8,
            ))
        fig_bar.update_layout(
            **PLOT_BASE, barmode="group", height=300,
            yaxis_title="Weight (%)",
            title=dict(text="ALLOCATION BY METHOD",
                       font=dict(size=11, color=COLORS["muted"])),
        )
    else:
        fig_bar = _placeholder("No weight data — run portfolio optimizer first")

    # ── 3. Treemap — use selected method or fallback to first available ───────
    selected_weights = by_method.get(method) or \
                       (list(by_method.values())[0] if by_method else {})

    if selected_weights:
        labels = list(selected_weights.keys())
        values = [v * 100 for v in selected_weights.values()]
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

    # ── 4. Efficient frontier — /portfolio/optimize ───────────────────────────
    fig_ef = _placeholder("Run /portfolio/optimize to see frontier")
    try:
        ro = requests.get(f"{API_BASE}/portfolio/optimize",
                          headers=HEADERS, timeout=8)
        if ro.status_code == 200:
            opt = ro.json()
            # if optimize returns frontier points
            if isinstance(opt, list) and opt and "volatility" in opt[0]:
                ef_df = pd.DataFrame(opt)
                fig_ef = go.Figure()
                fig_ef.add_trace(go.Scatter(
                    x=ef_df["volatility"] * 100,
                    y=ef_df["return"] * 100,
                    mode="lines+markers",
                    name="Efficient Frontier",
                    line=dict(color=COLORS["blue"], width=2),
                    marker=dict(size=4, color=COLORS["blue"]),
                ))
                fig_ef.update_layout(
                    **PLOT_BASE, height=240,
                    xaxis_title="Volatility (%)",
                    yaxis_title="Expected Return (%)",
                    title=dict(text="EFFICIENT FRONTIER",
                               font=dict(size=11, color=COLORS["muted"])),
                )
    except Exception:
        pass

    # ── 5. Weights table — show raw data from API ─────────────────────────────
    if not weights_list:
        weights_table = html.Div(
            "No portfolio weights found. Run the optimizer first.",
            style={"color":COLORS["dim"],"fontFamily":"'IBM Plex Mono',monospace",
                   "fontSize":"11px","padding":"12px"},
        )
    else:
        method_colors = {"mpt":COLORS["blue"],"bl":COLORS["green"],
                         "kelly":COLORS["amber"],"blended":COLORS["purple"]}
        rows = []
        # filter to selected method if available, else show all
        display_rows = [r for r in weights_list if r.get("method") == method] or weights_list
        for row in sorted(display_rows, key=lambda x: x.get("weight", 0), reverse=True):
            m   = row.get("method", "—")
            col = method_colors.get(m, COLORS["muted"])
            rows.append(html.Tr([
                html.Td(row.get("ticker", "—"),          style=_td(COLORS["text"])),
                html.Td(f"{row.get('weight',0)*100:.1f}%", style=_td(COLORS["blue"])),
                html.Td(
                    html.Span(m.upper(), style={
                        "background": col + "22", "color": col,
                        "border": f"1px solid {col}44", "borderRadius": "3px",
                        "padding": "1px 6px", "fontFamily": "'IBM Plex Mono',monospace",
                        "fontSize": "9px", "letterSpacing": "1px",
                    }),
                    style={"padding":"5px 6px",
                           "borderBottom":f"1px solid {COLORS['border']}22"},
                ),
                html.Td(str(row.get("calculated_at","—"))[:10], style=_td(COLORS["dim"])),
            ]))

        weights_table = html.Table(
            [html.Thead(html.Tr([
                html.Th("TICKER",      style=_th()),
                html.Th("WEIGHT",      style=_th()),
                html.Th("METHOD",      style=_th()),
                html.Th("CALCULATED",  style=_th()),
            ]))] + [html.Tbody(rows)],
            style={"width":"100%","borderCollapse":"collapse",
                   "fontFamily":"'IBM Plex Mono',monospace"},
        )

    # ── 6. Risk KPIs — not in your API yet, show placeholder ─────────────────
    # These will populate once you add /portfolio/risk endpoint
    return (fig_bar, fig_tree, fig_ef, weights_table,
            "—", "—", "—", "—", "—")