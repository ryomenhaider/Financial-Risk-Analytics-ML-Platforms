import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import dash, requests
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
from dashboard.theme import COLORS, PLOT_BASE, API_BASE, HEADERS
from config.logging_config import get_logger

logger = get_logger(__name__)

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

def _th():
    return {"fontSize":"9px","color":COLORS["dim"],"letterSpacing":"2px",
            "padding":"6px 8px","textAlign":"left","borderBottom":f"1px solid {COLORS['border']}"}

def _td(color):
    return {"fontSize":"12px","color":color,"padding":"7px 8px",
            "borderBottom":f"1px solid {COLORS['border']}22"}

layout = html.Div([
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
            dcc.Dropdown(id="ticker-select",
                         options=[{"label":t,"value":t} for t in TICKERS],
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

    html.Div([
        _card("LAST CLOSE",   "kpi-close",  "kpi-chg",    COLORS["blue"]),
        _card("DAILY VOLUME", "kpi-vol",    None,          COLORS["purple"]),
        _card("RSI (14)",     "kpi-rsi",    "kpi-rsi-sig", COLORS["amber"]),
        _card("52W HIGH",     "kpi-52h",    None,          COLORS["green"]),
        _card("52W LOW",      "kpi-52l",    None,          COLORS["red"]),
    ], style={"display":"flex","gap":"12px","marginBottom":"20px","flexWrap":"wrap"}),

    dcc.Loading(type="circle", color=COLORS["blue"], children=[
        dcc.Graph(id="candle-chart", config={"displayModeBar":False},
                  style={"borderRadius":"6px","border":f"1px solid {COLORS['border']}",
                         "marginBottom":"20px"}),
    ]),

    html.Div([
        html.Div([
            html.Div("MACRO INDICATORS",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                dcc.Graph(id="macro-chart", config={"displayModeBar":False},
                          style={"height":"260px"}),
            ]),
        ], style={"flex":"1","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),

        html.Div([
            html.Div("TOP MOVERS  (24H)",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                html.Div(id="top-movers-table"),
            ]),
        ], style={"width":"340px","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
    ], style={"display":"flex","gap":"16px"}),

    dcc.Interval(id="overview-refresh", interval=60_000, n_intervals=0),
])


@callback(
    [Output("candle-chart","figure"),
     Output("kpi-close","children"),   Output("kpi-chg","children"),
     Output("kpi-vol","children"),     Output("kpi-rsi","children"),
     Output("kpi-rsi-sig","children"), Output("kpi-52h","children"),
     Output("kpi-52l","children"),     Output("last-update-time","children")],
    [Input("ticker-select","value"), Input("days-select","value"),
     Input("overview-refresh","n_intervals")],
    prevent_initial_call=False,
)
def update_candle(ticker, days, _):
    empty = go.Figure()
    empty.update_layout(**PLOT_BASE, title="No data")
    defaults = (empty,) + ("—",) * 8

    try:
        r = requests.get(f"{API_BASE}/prices/{ticker}/history",
                         params={"limit": days}, headers=HEADERS, timeout=6)
        if r.status_code != 200:
            logger.error(f"API returned {r.status_code} for {ticker}: {r.text[:200]}")
            return defaults
        data = r.json()
        if not data:
            logger.warning(f"No data returned from API for {ticker}")
            return defaults

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None)
        df = df.sort_values("date").reset_index(drop=True)
        
        # ✅ FIX: Ensure numeric columns are float type
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        # Drop rows with NaN in critical columns
        df = df.dropna(subset=["close"])
        
        if df.empty:
            logger.warning(f"No valid data after type conversion for {ticker}")
            return defaults
        
        logger.info(f"Loaded {len(df)} records for {ticker}")

    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}", exc_info=True)
        return defaults

    # ── Chart ────────────────────────────────────────────────────────────────
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        row_heights=[0.72, 0.28], vertical_spacing=0.02)

    fig.add_trace(go.Candlestick(
        x=df["date"], open=df["open"], high=df["high"],
        low=df["low"],  close=df["close"], name=ticker,
        increasing_line_color=COLORS["green"],
        decreasing_line_color=COLORS["red"],
        increasing_fillcolor=COLORS["green"],
        decreasing_fillcolor=COLORS["red"],
        opacity=0.7,
    ), row=1, col=1)

    # Bollinger bands if present
    if "bb_upper" in df.columns and "bb_lower" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["bb_upper"],
            line=dict(color="rgba(168, 85, 247, 0.5)", width=1, dash="dot"),
            showlegend=False,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["bb_lower"],
            line=dict(color="rgba(168, 85, 247, 0.5)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(168, 85, 247, 0.1)",
            showlegend=False,
        ), row=1, col=1)

    colors_v = [COLORS["green"] if c >= o else COLORS["red"]
                for c, o in zip(df["close"], df["open"])]
    fig.add_trace(go.Bar(
        x=df["date"], y=df["volume"],
        marker_color=colors_v, opacity=0.6, showlegend=False,
    ), row=2, col=1)

    # Apply dark theme to the combined figure
    layout_update = {
        **PLOT_BASE,
        "xaxis_rangeslider_visible": False,
        "title": dict(
            text=f"<b>{ticker}</b>  |  {days}D",
            font=dict(family="'IBM Plex Mono',monospace", size=13, color=COLORS["text"]),
        ),
        "height": 460,
    }
    fig.update_layout(**layout_update)
    fig.update_xaxes(showgrid=True, gridcolor=COLORS["border"])
    fig.update_yaxes(showgrid=True, gridcolor=COLORS["border"])

    # ── KPIs ─────────────────────────────────────────────────────────────────
    try:
        last = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else last
        
        # Ensure values are numeric
        close_val = float(last["close"])
        prev_close = float(prev["close"])
        chg = (close_val - prev_close) / prev_close * 100
        chg_str = f"{'▲' if chg >= 0 else '▼'} {abs(chg):.2f}%"
        chg_col = COLORS["green"] if chg >= 0 else COLORS["red"]

        # ✅ FIX: safely read rsi — your API doesn't always return it
        rsi_val = None
        if "rsi" in df.columns:
            raw = last["rsi"]
            try:
                rsi_val = float(raw) if raw is not None and str(raw) not in ("", "nan", "None") else None
            except (ValueError, TypeError):
                rsi_val = None

        rsi_str = f"{rsi_val:.1f}" if rsi_val is not None else "N/A"
        rsi_sig = ("OVERBOUGHT" if rsi_val and rsi_val > 70 else
                   "OVERSOLD"   if rsi_val and rsi_val < 30 else
                   "NEUTRAL")

        vol_m = f"{float(last['volume']) / 1_000_000:.1f}M" if last["volume"] else "—"
        hi52  = f"${float(df['high'].max()):.2f}"
        lo52  = f"${float(df['low'].min()):.2f}"
        ts    = f"Updated {datetime.utcnow().strftime('%H:%M UTC')}"
    except Exception as e:
        logger.error(f"Error calculating KPIs for {ticker}: {e}", exc_info=True)
        return defaults

    return (
        fig,
        f"${last['close']:.2f}",
        html.Span(chg_str, style={"color": chg_col}),
        vol_m, rsi_str, rsi_sig, hi52, lo52, ts,
    )


@callback(Output("macro-chart","figure"), [Input("overview-refresh","n_intervals")], prevent_initial_call=False)
def update_macro(_):
    fig = go.Figure()
    fig.add_annotation(
        text="Macro endpoint coming soon<br><span style='font-size:11px'>Add /macro route to FastAPI</span>",
        x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
        font=dict(color=COLORS["muted"], size=13, family="'IBM Plex Mono',monospace"),
    )
    fig.update_layout(**PLOT_BASE, height=220)
    return fig


@callback(Output("top-movers-table","children"), [Input("overview-refresh","n_intervals")], prevent_initial_call=False)
def update_movers(_):
    rows = []
    for t in TICKERS[:10]:
        try:
            r = requests.get(f"{API_BASE}/prices/{t}/history",
                             params={"limit": 2}, headers=HEADERS, timeout=4)
            if r.status_code != 200:
                continue
            d = r.json()
            if not d or len(d) < 2:
                continue
            df = pd.DataFrame(d)
            df["date"] = pd.to_datetime(df["date"])
            # ✅ FIX: Convert numeric columns
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df = df.sort_values("date")
            c   = float(df.iloc[-1]["close"])
            p   = float(df.iloc[-2]["close"])
            chg = (c - p) / p * 100
            rows.append((t, c, chg))
        except Exception as e:
            logger.debug(f"Error fetching {t}: {e}")

    if not rows:
        return html.Div("No data", style={"color":COLORS["dim"],
                                           "fontFamily":"'IBM Plex Mono',monospace",
                                           "fontSize":"11px","padding":"12px"})

    rows.sort(key=lambda x: abs(x[2]), reverse=True)

    return html.Table(
        [html.Thead(html.Tr([
            html.Th("TICKER", style=_th()),
            html.Th("PRICE",  style=_th()),
            html.Th("CHG %",  style=_th()),
        ]))] +
        [html.Tbody([
            html.Tr([
                html.Td(r[0], style=_td(COLORS["text"])),
                html.Td(f"${r[1]:.2f}", style=_td(COLORS["muted"])),
                html.Td(f"{'▲' if r[2]>=0 else '▼'} {abs(r[2]):.2f}%",
                        style=_td(COLORS["green"] if r[2]>=0 else COLORS["red"])),
            ]) for r in rows
        ])],
        style={"width":"100%","borderCollapse":"collapse","fontFamily":"'IBM Plex Mono',monospace"},
    )