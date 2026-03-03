
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dash, requests
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from dashboard.theme import COLORS, PLOT_BASE, API_BASE, HEADERS  # ✅ safe
dash.register_page(__name__, path="/", name="Market Overview", order=0)

TICKERS = ["AAPL","MSFT","GOOGL","TSLA","NVDA","AMZN","META","BTC-USD","ETH-USD","SPY"]

def _card(label, value_id, delta_id=None, accent=COLORS["blue"]):
    return html.Div([
        html.Div(label, style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                                "letterSpacing":"2px","color":COLORS["dim"],"marginBottom":"6px"}),
        html.Div(id=value_id, children="—",
                 style={"fontFamily":"'IBM Plex Mono',monospace","fontWeight":"600",
                        "fontSize":"22px","color":accent}),
        html.Div(id=delta_id, children="", style={"fontSize":"11px","color":COLORS["muted"],
                                                    "marginTop":"2px"}) if delta_id else None,
    ], style={"background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
              "borderTop":f"2px solid {accent}","borderRadius":"6px",
              "padding":"16px 20px","flex":"1","minWidth":"140px"})

layout = html.Div([
    # Header
    html.Div([
        html.Div([
            html.Span("MARKET OVERVIEW", style={"fontFamily":"'IBM Plex Mono',monospace",
                                                 "fontWeight":"600","fontSize":"13px",
                                                 "color":COLORS["text"],"letterSpacing":"3px"}),
            html.Div(id="last-update-time", style={"fontFamily":"'IBM Plex Mono',monospace",
                                                     "fontSize":"10px","color":COLORS["dim"],
                                                     "marginTop":"3px"}),
        ]),
        html.Div([
            dcc.Dropdown(id="ticker-select", options=[{"label":t,"value":t} for t in TICKERS],
                         value="AAPL", clearable=False,
                         style={"width":"160px","fontFamily":"'IBM Plex Mono',monospace",
                                "fontSize":"12px","background":COLORS["elevated"],
                                "color":COLORS["text"],"border":f"1px solid {COLORS['border']}"}),
            dcc.Dropdown(id="days-select",
                         options=[{"label":"7D","value":7},{"label":"30D","value":30},
                                  {"label":"90D","value":90},{"label":"1Y","value":365}],
                         value=90, clearable=False,
                         style={"width":"100px","fontFamily":"'IBM Plex Mono',monospace",
                                "fontSize":"12px","background":COLORS["elevated"],
                                "color":COLORS["text"],"border":f"1px solid {COLORS['border']}",
                                "marginLeft":"8px"}),
        ], style={"display":"flex","alignItems":"center"}),
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"flex-start",
              "marginBottom":"24px"}),

    # KPI Cards row
    html.Div([
        _card("LAST CLOSE",   "kpi-close",  "kpi-chg",    COLORS["blue"]),
        _card("DAILY VOLUME", "kpi-vol",    None,          COLORS["purple"]),
        _card("RSI (14)",     "kpi-rsi",    "kpi-rsi-sig", COLORS["amber"]),
        _card("52W HIGH",     "kpi-52h",    None,          COLORS["green"]),
        _card("52W LOW",      "kpi-52l",    None,          COLORS["red"]),
    ], style={"display":"flex","gap":"12px","marginBottom":"20px","flexWrap":"wrap"}),

    # Main chart — candlestick + volume
    dcc.Loading(type="circle", color=COLORS["blue"], children=[
        dcc.Graph(id="candle-chart", config={"displayModeBar":False},
                  style={"borderRadius":"6px","border":f"1px solid {COLORS['border']}",
                         "marginBottom":"20px"}),
    ]),

    # Bottom row: macro chart + top movers
    html.Div([
        html.Div([
            html.Div("MACRO INDICATORS", style={"fontFamily":"'IBM Plex Mono',monospace",
                                                  "fontSize":"10px","letterSpacing":"2px",
                                                  "color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                dcc.Graph(id="macro-chart", config={"displayModeBar":False},
                          style={"height":"260px"}),
            ]),
        ], style={"flex":"1","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),

        html.Div([
            html.Div("TOP MOVERS  (24H)", style={"fontFamily":"'IBM Plex Mono',monospace",
                                                    "fontSize":"10px","letterSpacing":"2px",
                                                    "color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                html.Div(id="top-movers-table"),
            ]),
        ], style={"width":"340px","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
    ], style={"display":"flex","gap":"16px"}),

    dcc.Interval(id="overview-refresh", interval=60_000, n_intervals=0),
])


# ── Candlestick + Volume ──────────────────────────────────────────────────────
@callback(
    [Output("candle-chart","figure"),
     Output("kpi-close","children"), Output("kpi-chg","children"),
     Output("kpi-vol","children"),   Output("kpi-rsi","children"),
     Output("kpi-rsi-sig","children"),Output("kpi-52h","children"),
     Output("kpi-52l","children"),   Output("last-update-time","children")],
    [Input("ticker-select","value"), Input("days-select","value"),
     Input("overview-refresh","n_intervals")],
)
def update_candle(ticker, days, _):
    from datetime import datetime
    empty = go.Figure()
    empty.update_layout(**PLOT_BASE, title="No data")
    defaults = (empty,) + ("—",)*7 + ("—",)

    try:
        r = requests.get(f"{API_BASE}/prices/{ticker}/history",
                         params={"days": days}, headers=HEADERS, timeout=6)
        if r.status_code != 200:
            return defaults
        data = r.json()
        if not data:
            return defaults
        df = pd.DataFrame(data)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
    except Exception:
        return defaults

    # Chart
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.72, 0.28], vertical_spacing=0.02)
    # Candles
    fig.add_trace(go.Candlestick(
        x=df["timestamp"], open=df["open"], high=df["high"],
        low=df["low"], close=df["close"], name=ticker,
        increasing_line_color=COLORS["green"], decreasing_line_color=COLORS["red"],
        increasing_fillcolor=COLORS["green"]+"55", decreasing_fillcolor=COLORS["red"]+"55",
    ), row=1, col=1)
    # Bollinger
    if "bb_upper" in df.columns:
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["bb_upper"], name="BB Upper",
                                  line=dict(color=COLORS["purple"]+"88", width=1, dash="dot"),
                                  showlegend=False), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["timestamp"], y=df["bb_lower"], name="BB Lower",
                                  line=dict(color=COLORS["purple"]+"88", width=1, dash="dot"),
                                  fill="tonexty", fillcolor=COLORS["purple"]+"11",
                                  showlegend=False), row=1, col=1)
    # Volume
    colors_v = [COLORS["green"] if c >= o else COLORS["red"]
                for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(x=df["timestamp"], y=df["volume"], name="Volume",
                          marker_color=colors_v, opacity=0.6,
                          showlegend=False), row=2, col=1)

    layout_update = {**PLOT_BASE,
                     "xaxis_rangeslider_visible": False,
                     "title": dict(text=f"<b>{ticker}</b>  |  {days}D",
                                   font=dict(family="'IBM Plex Mono',monospace",
                                             size=13, color=COLORS["text"])),
                     "height": 460}
    fig.update_layout(**layout_update)
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["border"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["border"])

    # KPIs
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    chg = (last["close"] - prev["close"]) / prev["close"] * 100
    chg_str = f"{'▲' if chg >= 0 else '▼'} {abs(chg):.2f}%"
    chg_col = COLORS["green"] if chg >= 0 else COLORS["red"]
    rsi_val  = round(last.get("rsi", 0), 1) if "rsi" in last else "—"
    rsi_sig  = "OVERBOUGHT" if rsi_val != "—" and rsi_val > 70 else \
               "OVERSOLD" if rsi_val != "—" and rsi_val < 30 else "NEUTRAL"
    vol_m    = f"{last['volume']/1_000_000:.1f}M"
    hi52     = f"${df['high'].max():.2f}"
    lo52     = f"${df['low'].min():.2f}"
    ts       = f"Updated {datetime.utcnow().strftime('%H:%M UTC')}"

    return (fig, f"${last['close']:.2f}",
            html.Span(chg_str, style={"color":chg_col}),
            vol_m, f"{rsi_val}", rsi_sig, hi52, lo52, ts)


# ── Macro Chart ───────────────────────────────────────────────────────────────
@callback(Output("macro-chart","figure"),
          [Input("overview-refresh","n_intervals")])
def update_macro(_):
    try:
        r = requests.get(f"{API_BASE}/macro", headers=HEADERS, timeout=6)
        if r.status_code != 200:
            raise ValueError
        data = r.json()
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
    except Exception:
        fig = go.Figure()
        fig.update_layout(**PLOT_BASE, title="Macro data unavailable", height=220)
        return fig

    fig = go.Figure()
    palette = [COLORS["blue"], COLORS["amber"], COLORS["green"], COLORS["purple"], COLORS["red"]]
    for i, indicator in enumerate(df["indicator_name"].unique()[:5]):
        sub = df[df["indicator_name"] == indicator].sort_values("date")
        fig.add_trace(go.Scatter(x=sub["date"], y=sub["value"], name=indicator,
                                  line=dict(color=palette[i], width=1.5), mode="lines"))
    fig.update_layout(**PLOT_BASE, height=220,
                      title=dict(text="MACRO INDICATORS",
                                 font=dict(size=11, color=COLORS["muted"])))
    return fig


# ── Top Movers ────────────────────────────────────────────────────────────────
@callback(Output("top-movers-table","children"),
          [Input("overview-refresh","n_intervals")])
def update_movers(_):
    rows = []
    for t in TICKERS[:10]:
        try:
            r = requests.get(f"{API_BASE}/prices/{t}/history",
                             params={"days":2}, headers=HEADERS, timeout=4)
            if r.status_code != 200:
                continue
            d = r.json()
            if len(d) < 2:
                continue
            df = pd.DataFrame(d).sort_values("timestamp")
            c, p = df.iloc[-1]["close"], df.iloc[-2]["close"]
            chg = (c - p) / p * 100
            rows.append((t, c, chg))
        except Exception:
            pass

    rows.sort(key=lambda x: abs(x[2]), reverse=True)
    return html.Table(
        [html.Thead(html.Tr([
            html.Th("TICKER", style=_th()), html.Th("PRICE", style=_th()),
            html.Th("CHG %", style=_th()),
        ]))] +
        [html.Tbody([
            html.Tr([
                html.Td(r[0], style=_td(COLORS["text"])),
                html.Td(f"${r[1]:.2f}", style=_td(COLORS["muted"])),
                html.Td(
                    f"{'▲' if r[2]>=0 else '▼'} {abs(r[2]):.2f}%",
                    style=  _td(COLORS["green"] if r[2]>=0 else COLORS["red"]),
                ),
            ]) for r in rows
        ])],
        style={"width":"100%","borderCollapse":"collapse","fontFamily":"'IBM Plex Mono',monospace"},
    )

def _th():
    return {"fontSize":"9px","color":COLORS["dim"],"letterSpacing":"2px",
            "padding":"6px 8px","textAlign":"left","borderBottom":f"1px solid {COLORS['border']}"}
def _td(color):
    return {"fontSize":"12px","color":color,"padding":"7px 8px",
            "borderBottom":f"1px solid {COLORS['border']}22"}