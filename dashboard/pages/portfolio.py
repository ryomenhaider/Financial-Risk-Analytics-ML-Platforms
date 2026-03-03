
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dash, requests
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
from dashboard.theme import COLORS, PLOT_BASE, API_BASE, HEADERS  # ✅ safe
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


layout = html.Div([
    # Header
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

    # Risk metric cards
    html.Div([
        _rcard("SHARPE RATIO",   "pa-sharpe",  COLORS["green"]),
        _rcard("VAR (95%)",      "pa-var",     COLORS["red"]),
        _rcard("MAX DRAWDOWN",   "pa-mdd",     COLORS["amber"]),
        _rcard("PORTFOLIO BETA", "pa-beta",    COLORS["blue"]),
        _rcard("SORTINO",        "pa-sortino", COLORS["purple"]),
    ], style={"display":"flex","gap":"12px","marginBottom":"20px","flexWrap":"wrap"}),

    # Weights chart + treemap
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

    # Efficient frontier + rebalancing table
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
            html.Div("REBALANCING SIGNALS",
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
    [Output("pa-bar-chart","figure"), Output("pa-treemap","figure"),
     Output("pa-frontier","figure"),  Output("pa-rebalance-table","children"),
     Output("pa-sharpe","children"),  Output("pa-var","children"),
     Output("pa-mdd","children"),     Output("pa-beta","children"),
     Output("pa-sortino","children")],
    [Input("pa-method","value")],
)
def update_portfolio(method):
    empty = go.Figure()
    empty.update_layout(**PLOT_BASE)
    defaults = (empty,)*3 + (html.Div("No data"),) + ("—",)*5

    # Weights
    try:
        rw = requests.get(f"{API_BASE}/allocation/weights",
                          params={"method": method}, headers=HEADERS, timeout=6)
        weights = rw.json() if rw.status_code == 200 else {}
    except Exception:
        weights = {}

    # Risk metrics
    try:
        rr = requests.get(f"{API_BASE}/risk/portfolio", headers=HEADERS, timeout=6)
        risk = rr.json() if rr.status_code == 200 else {}
    except Exception:
        risk = {}

    # Rebalancing
    try:
        rb = requests.get(f"{API_BASE}/allocation/rebalance", headers=HEADERS, timeout=6)
        rebal = rb.json() if rb.status_code == 200 else []
    except Exception:
        rebal = []

    # Bar chart — all 3 methods side-by-side
    methods_data = {}
    for m in ["mpt","bl","kelly","blended"]:
        try:
            r = requests.get(f"{API_BASE}/allocation/weights",
                             params={"method":m}, headers=HEADERS, timeout=4)
            if r.status_code == 200:
                methods_data[m] = r.json()
        except Exception:
            pass

    fig_bar = go.Figure()
    palette = {"mpt":COLORS["blue"],"bl":COLORS["green"],"kelly":COLORS["amber"],
               "blended":COLORS["purple"]}
    tickers_all = sorted(set(k for d in methods_data.values()
                             for k in (d.keys() if isinstance(d,dict) else [])))
    for m, d in methods_data.items():
        if not isinstance(d, dict):
            continue
        fig_bar.add_trace(go.Bar(
            name=m.upper(), x=tickers_all,
            y=[d.get(t, 0)*100 for t in tickers_all],
            marker_color=palette.get(m, COLORS["blue"]), opacity=0.8,
        ))
    fig_bar.update_layout(**PLOT_BASE, barmode="group", height=300,
                           yaxis_title="Weight (%)",
                           title=dict(text="ALLOCATION BY METHOD",
                                      font=dict(size=11, color=COLORS["muted"])))

    # Treemap (blended weights)
    blend = methods_data.get("blended", weights) if isinstance(methods_data.get("blended", weights), dict) else {}
    fig_tree = go.Figure()
    if blend:
        labels = list(blend.keys())
        values = [v * 100 for v in blend.values()]
        fig_tree = go.Figure(go.Treemap(
            labels=labels, parents=[""]*len(labels), values=values,
            textinfo="label+percent root",
            textfont=dict(family="'IBM Plex Mono',monospace", size=12, color=COLORS["text"]),
            marker=dict(colors=values, colorscale=[[0, COLORS["border"]], [1, COLORS["blue"]]],
                        line=dict(width=2, color=COLORS["bg"])),
        ))
        fig_tree.update_layout(paper_bgcolor=COLORS["card"], margin=dict(l=0,r=0,t=0,b=0),
                                height=280)

    # Efficient frontier
    fig_ef = go.Figure()
    try:
        ref = requests.get(f"{API_BASE}/allocation/frontier", headers=HEADERS, timeout=5)
        if ref.status_code == 200:
            ef_data = ref.json()
            ef_df = pd.DataFrame(ef_data)
            fig_ef.add_trace(go.Scatter(
                x=ef_df["volatility"]*100, y=ef_df["return"]*100,
                mode="lines+markers", name="Efficient Frontier",
                line=dict(color=COLORS["blue"], width=2),
                marker=dict(size=4, color=COLORS["blue"]),
            ))
            # Mark current portfolio
            cr = risk.get("volatility"), risk.get("expected_return")
            if cr[0] and cr[1]:
                fig_ef.add_trace(go.Scatter(
                    x=[cr[0]*100], y=[cr[1]*100], mode="markers", name="Current",
                    marker=dict(size=12, color=COLORS["amber"], symbol="star"),
                ))
    except Exception:
        fig_ef.add_annotation(text="Frontier data unavailable", x=0.5, y=0.5,
                               showarrow=False, font=dict(color=COLORS["muted"], size=12))
    fig_ef.update_layout(**PLOT_BASE, height=240,
                          xaxis_title="Volatility (%)", yaxis_title="Expected Return (%)",
                          title=dict(text="EFFICIENT FRONTIER",
                                     font=dict(size=11, color=COLORS["muted"])))

    # Rebalancing table
    if not rebal:
        reb_table = html.Div("No rebalancing needed",
                             style={"color":COLORS["dim"],"fontFamily":"'IBM Plex Mono',monospace",
                                    "fontSize":"11px","padding":"12px"})
    else:
        sig_color = {"BUY":COLORS["green"],"SELL":COLORS["red"],"HOLD":COLORS["muted"]}
        reb_rows  = []
        for item in (rebal if isinstance(rebal, list) else []):
            sig = str(item.get("signal","HOLD")).upper()
            reb_rows.append(html.Tr([
                html.Td(item.get("ticker","—"), style=_td(COLORS["text"])),
                html.Td(f"{item.get('current_weight',0)*100:.1f}%", style=_td(COLORS["muted"])),
                html.Td(f"{item.get('target_weight',0)*100:.1f}%",  style=_td(COLORS["blue"])),
                html.Td(
                    html.Span(sig, style={"background":sig_color.get(sig,COLORS["muted"])+"22",
                                          "color":sig_color.get(sig,COLORS["muted"]),
                                          "border":f"1px solid {sig_color.get(sig,COLORS['muted'])}44",
                                          "borderRadius":"3px","padding":"1px 6px",
                                          "fontFamily":"'IBM Plex Mono',monospace",
                                          "fontSize":"9px","letterSpacing":"1px"}),
                    style={"padding":"5px 6px","borderBottom":f"1px solid {COLORS['border']}22"}),
            ]))
        reb_table = html.Table(
            [html.Thead(html.Tr([
                html.Th("TICKER", style=_th()), html.Th("CURRENT", style=_th()),
                html.Th("TARGET", style=_th()),  html.Th("ACTION", style=_th()),
            ]))] + [html.Tbody(reb_rows)],
            style={"width":"100%","borderCollapse":"collapse","fontFamily":"'IBM Plex Mono',monospace"},
        )

    # Risk KPIs
    def _fmt(k, prefix="", suffix="", decimals=3):
        v = risk.get(k)
        return f"{prefix}{v:.{decimals}f}{suffix}" if isinstance(v,(int,float)) else "—"

    return (fig_bar, fig_tree, fig_ef, reb_table,
            _fmt("sharpe_ratio"), _fmt("var_95", prefix="-$"),
            _fmt("max_drawdown", suffix="%", decimals=1),
            _fmt("beta"), _fmt("sortino_ratio"))

def _th():
    return {"fontSize":"9px","color":COLORS["dim"],"letterSpacing":"1.5px",
            "padding":"5px 6px","textAlign":"left","borderBottom":f"1px solid {COLORS['border']}"}
def _td(color):
    return {"fontFamily":"'IBM Plex Mono',monospace","fontSize":"11px","color":color,
            "padding":"6px 6px","borderBottom":f"1px solid {COLORS['border']}22"}