"""
Page 5 — Sentiment Analysis
FinBERT scores over time, news feed with badges, correlation heatmap.
"""
import dash, requests
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
from dashboard.theme import COLORS, PLOT_BASE, API_BASE, HEADERS

dash.register_page(__name__, path="/sentiment", name="Sentiment Analysis", order=4)

TICKERS = ["AAPL","MSFT","GOOGL","TSLA","NVDA","AMZN","META","BTC-USD","ETH-USD","SPY"]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _score_color(score):
    if score >= 0.2:  return COLORS["green"]
    if score <= -0.2: return COLORS["red"]
    return COLORS["amber"]

def _score_label(score):
    if score >= 0.2:  return "POSITIVE"
    if score <= -0.2: return "NEGATIVE"
    return "NEUTRAL"

def _badge(text, color):
    return html.Span(text, style={
        "background": color + "22", "color": color,
        "border": f"1px solid {color}44", "borderRadius": "3px",
        "padding": "1px 7px", "fontFamily": "'IBM Plex Mono',monospace",
        "fontSize": "9px", "letterSpacing": "1px", "fontWeight": "600",
    })

def _empty_fig(msg="No data available"):
    fig = go.Figure()
    fig.add_annotation(text=msg, x=0.5, y=0.5, xref="paper", yref="paper",
                       showarrow=False, font=dict(color=COLORS["muted"], size=12))
    fig.update_layout(**PLOT_BASE, height=240)
    return fig

def _safe_fetch(url, params=None):
    """Returns parsed JSON or None on any error."""
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=6)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None

def _find_col(df, candidates):
    """Return the first matching column name from candidates list."""
    for c in candidates:
        if c in df.columns:
            return c
    return None


# ── Helper card ───────────────────────────────────────────────────────────────
def _kpi_chip(ticker, score):
    col = _score_color(score)
    return html.Div([
        html.Div(ticker, style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                                 "color":COLORS["dim"],"letterSpacing":"1px","marginBottom":"2px"}),
        html.Div(f"{score:+.2f}", style={"fontFamily":"'IBM Plex Mono',monospace",
                                          "fontWeight":"600","fontSize":"14px","color":col}),
    ], style={"background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
               "borderBottom":f"2px solid {col}","borderRadius":"4px",
               "padding":"8px 14px","textAlign":"center"})


# ── Layout ────────────────────────────────────────────────────────────────────
layout = html.Div([
    html.Div([
        html.Div([
            html.Span("SENTIMENT ANALYSIS", style={
                "fontFamily":"'IBM Plex Mono',monospace","fontWeight":"600",
                "fontSize":"13px","color":COLORS["text"],"letterSpacing":"3px"}),
            html.Div("FinBERT  ·  Financial NLP  ·  NewsAPI Headlines", style={
                "fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                "color":COLORS["dim"],"marginTop":"3px"}),
        ]),
        html.Div([
            dcc.Dropdown(id="sent-ticker",
                         options=[{"label":t,"value":t} for t in TICKERS],
                         value="AAPL", clearable=False,
                         style={"width":"150px","fontFamily":"'IBM Plex Mono',monospace",
                                "fontSize":"12px","background":COLORS["elevated"],
                                "border":f"1px solid {COLORS['border']}"}),
            dcc.Dropdown(id="sent-days",
                         options=[{"label":"7D","value":7},{"label":"30D","value":30},
                                  {"label":"90D","value":90}],
                         value=30, clearable=False,
                         style={"width":"90px","fontFamily":"'IBM Plex Mono',monospace",
                                "fontSize":"12px","background":COLORS["elevated"],
                                "border":f"1px solid {COLORS['border']}","marginLeft":"8px"}),
        ], style={"display":"flex","alignItems":"center"}),
    ], style={"display":"flex","justifyContent":"space-between",
              "alignItems":"flex-start","marginBottom":"24px"}),

    # KPI bar
    html.Div(id="sent-kpi-bar", style={"marginBottom":"20px"}),

    # Timeline + gauge
    html.Div([
        html.Div([
            html.Div("SENTIMENT TIMELINE", style={
                "fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="circle", color=COLORS["purple"], children=[
                dcc.Graph(id="sent-timeline", config={"displayModeBar":False},
                          style={"height":"280px"}),
            ]),
        ], style={"flex":"2","background":COLORS["card"],
                   "border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),

        html.Div([
            html.Div("CURRENT SCORE", style={
                "fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["purple"], children=[
                dcc.Graph(id="sent-gauge", config={"displayModeBar":False},
                          style={"height":"250px"}),
            ]),
        ], style={"flex":"1","background":COLORS["card"],
                   "border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
    ], style={"display":"flex","gap":"16px","marginBottom":"16px"}),

    # Heatmap + news feed
    html.Div([
        html.Div([
            html.Div("CROSS-ASSET SENTIMENT HEATMAP", style={
                "fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["purple"], children=[
                dcc.Graph(id="sent-heatmap", config={"displayModeBar":False},
                          style={"height":"300px"}),
            ]),
        ], style={"flex":"1","background":COLORS["card"],
                   "border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),

        html.Div([
            html.Div("LATEST HEADLINES", style={
                "fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["purple"], children=[
                html.Div(id="sent-news-feed",
                         style={"maxHeight":"300px","overflowY":"auto"}),
            ]),
        ], style={"width":"420px","background":COLORS["card"],
                   "border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
    ], style={"display":"flex","gap":"16px"}),
])


# ── Callback ──────────────────────────────────────────────────────────────────
@callback(
    [Output("sent-timeline", "figure"),
     Output("sent-gauge",    "figure"),
     Output("sent-heatmap",  "figure"),
     Output("sent-news-feed","children"),
     Output("sent-kpi-bar",  "children")],
    [Input("sent-ticker","value"),
     Input("sent-days",  "value")],
)
def update_sentiment(ticker, days):
    # ── 1. Timeline data ──────────────────────────────────────────────────────
    timeline_data = _safe_fetch(f"{API_BASE}/sentiment/{ticker}/timeline",
                                params={"days": days})
    timeline = pd.DataFrame(timeline_data) if timeline_data else pd.DataFrame()

    ts_col    = _find_col(timeline, ["published_at","date","timestamp"]) if not timeline.empty else None
    score_col = _find_col(timeline, ["sentiment_score","score"]) if not timeline.empty else None

    if ts_col and not timeline.empty:
        timeline[ts_col] = pd.to_datetime(timeline[ts_col], errors="coerce")
        timeline = timeline.dropna(subset=[ts_col]).sort_values(ts_col)

    # ── 2. Timeline figure ────────────────────────────────────────────────────
    if timeline.empty or not score_col:
        fig_timeline = _empty_fig("No sentiment timeline data")
    else:
        sc   = timeline[score_col]
        cols = [COLORS["green"] if v >= 0 else COLORS["red"] for v in sc]

        fig_timeline = go.Figure()
        fig_timeline.add_trace(go.Bar(
            x=timeline[ts_col], y=sc,
            marker_color=cols, opacity=0.75, name="Sentiment",
        ))
        if len(sc) >= 7:
            fig_timeline.add_trace(go.Scatter(
                x=timeline[ts_col], y=sc.rolling(7).mean(),
                line=dict(color=COLORS["blue"], width=2, dash="dash"),
                name="7D Avg", mode="lines",
            ))
        fig_timeline.update_layout(
            **PLOT_BASE, height=240,
            yaxis_range=[-1, 1],
            shapes=[dict(type="line", x0=0, x1=1, xref="paper", y0=0, y1=0,
                         line=dict(color=COLORS["border"], width=1))],
            title=dict(text=f"{ticker}  SENTIMENT  (-1 to +1)",
                       font=dict(size=11, color=COLORS["muted"])),
        )

    # ── 3. Current score ──────────────────────────────────────────────────────
    current_score = 0.0
    # Try dedicated endpoint first
    spot = _safe_fetch(f"{API_BASE}/sentiment/{ticker}")
    if spot and isinstance(spot, dict):
        current_score = float(spot.get("score", spot.get("sentiment_score", 0)) or 0)
    elif not timeline.empty and score_col:
        current_score = float(timeline[score_col].iloc[-1])

    # ── 4. Gauge figure ───────────────────────────────────────────────────────
    gauge_color = _score_color(current_score)
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(current_score, 3),
        gauge=dict(
            axis=dict(range=[-1, 1], tickcolor=COLORS["muted"],
                      tickfont=dict(color=COLORS["muted"], size=9)),
            bar=dict(color=gauge_color, thickness=0.25),
            bgcolor=COLORS["elevated"],
            borderwidth=1, bordercolor=COLORS["border"],
            steps=[
                dict(range=[-1,  -0.2], color=COLORS["red"]   + "22"),
                dict(range=[-0.2, 0.2], color=COLORS["amber"] + "22"),
                dict(range=[ 0.2,   1], color=COLORS["green"] + "22"),
            ],
        ),
        number=dict(font=dict(family="'IBM Plex Mono',monospace",
                               size=32, color=gauge_color)),
        title=dict(text=ticker,
                   font=dict(family="'IBM Plex Mono',monospace",
                              size=11, color=COLORS["muted"])),
    ))
    fig_gauge.update_layout(
        paper_bgcolor=COLORS["card"], font_color=COLORS["text"],
        height=220, margin=dict(l=20, r=20, t=30, b=10),
    )

    # ── 5. Heatmap — fetch all tickers ────────────────────────────────────────
    heatmap_scores = {}
    for t in TICKERS[:8]:
        data = _safe_fetch(f"{API_BASE}/sentiment/{t}")
        if data and isinstance(data, dict):
            v = data.get("score", data.get("sentiment_score", None))
            if v is not None:
                try:
                    heatmap_scores[t] = float(v)
                except (TypeError, ValueError):
                    pass

    if heatmap_scores:
        tks  = list(heatmap_scores.keys())
        vals = [heatmap_scores[t] for t in tks]
        fig_heat = go.Figure(go.Heatmap(
            z=[vals], x=tks, y=["SCORE"],
            colorscale=[[0, COLORS["red"]], [0.5, COLORS["amber"]], [1, COLORS["green"]]],
            zmin=-1, zmax=1, showscale=True,
            colorbar=dict(tickfont=dict(color=COLORS["muted"], size=9),
                          len=0.8, thickness=12,
                          title=dict(text="Score",
                                     font=dict(color=COLORS["muted"]))),
            text=[[f"{v:.2f}" for v in vals]],
            texttemplate="%{text}",
            textfont=dict(family="'IBM Plex Mono',monospace",
                          size=11, color=COLORS["text"]),
        ))
        fig_heat.update_layout(
            **PLOT_BASE, height=260,
            title=dict(text="REAL-TIME SENTIMENT SCORES",
                       font=dict(size=11, color=COLORS["muted"])),
        )
    else:
        fig_heat = _empty_fig("Sentiment scores unavailable")

    # ── 6. News feed ──────────────────────────────────────────────────────────
    news_data = _safe_fetch(f"{API_BASE}/sentiment/{ticker}/news",
                            params={"days": min(days, 7)})
    news = news_data if isinstance(news_data, list) else []

    if not news:
        news_div = html.Div(
            "No recent headlines",
            style={"color":COLORS["dim"],"fontFamily":"'IBM Plex Mono',monospace",
                   "fontSize":"11px","padding":"12px"},
        )
    else:
        cards = []
        for item in news[:15]:
            if not isinstance(item, dict):
                continue
            sc    = float(item.get("sentiment_score", item.get("score", 0)) or 0)
            col   = _score_color(sc)
            label = _score_label(sc)
            title = item.get("headline", item.get("title", "—"))
            src   = item.get("source", "—")
            date  = str(item.get("published_at", item.get("date", "")))[:10]

            cards.append(html.Div([
                html.Div([
                    _badge(label, col),
                    html.Span(f" {sc:+.3f}", style={
                        "fontFamily":"'IBM Plex Mono',monospace",
                        "fontSize":"10px","color":col,"marginLeft":"6px"}),
                ], style={"marginBottom":"4px"}),
                html.Div(title, style={"fontSize":"11px","color":COLORS["text"],
                                        "lineHeight":"1.5","marginBottom":"4px"}),
                html.Div(f"{src}  ·  {date}", style={
                    "fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                    "color":COLORS["dim"]}),
            ], style={"padding":"10px 0",
                       "borderBottom":f"1px solid {COLORS['border']}22"}))

        news_div = html.Div(cards)

    # ── 7. KPI bar ────────────────────────────────────────────────────────────
    kpi_bar = html.Div(
        [_kpi_chip(t, s) for t, s in heatmap_scores.items()] or
        [html.Div("No scores available",
                  style={"color":COLORS["dim"],"fontFamily":"'IBM Plex Mono',monospace",
                          "fontSize":"11px"})],
        style={"display":"flex","gap":"8px","flexWrap":"wrap"},
    )

    return fig_timeline, fig_gauge, fig_heat, news_div, kpi_bar