import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import dash, requests, traceback
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
from dashboard.theme import COLORS, PLOT_BASE, API_BASE, HEADERS

dash.register_page(__name__, path="/sentiment", name="Sentiment Analysis", order=4)

TICKERS = ["AAPL","MSFT","GOOGL","TSLA","NVDA","BTC-USD","ETH-USD","SPY"]

SENT_COLORS = {
    "positive": COLORS["green"],
    "negative": COLORS["red"],
    "neutral":  COLORS["muted"],
}

layout = html.Div([
    html.Div([
        html.Div([
            html.Span("SENTIMENT ANALYSIS", style={"fontFamily":"'IBM Plex Mono',monospace",
                                                    "fontWeight":"600","fontSize":"13px",
                                                    "color":COLORS["text"],"letterSpacing":"3px"}),
            html.Div("FinBERT NLP · News sentiment scoring",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
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
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"flex-start",
              "marginBottom":"24px"}),

    html.Div(id="sent-kpi-bar", style={"display":"flex","gap":"12px",
                                        "marginBottom":"20px","flexWrap":"wrap"}),
    html.Div([
        html.Div([
            html.Div("SENTIMENT SCORE TIMELINE",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="circle", color=COLORS["blue"], children=[
                dcc.Graph(id="sent-timeline", config={"displayModeBar":False},
                          style={"height":"280px"}),
            ]),
        ], style={"flex":"2","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
        html.Div([
            html.Div("OVERALL SENTIMENT",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                dcc.Graph(id="sent-gauge", config={"displayModeBar":False},
                          style={"height":"250px"}),
            ]),
        ], style={"flex":"1","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
    ], style={"display":"flex","gap":"16px","marginBottom":"16px"}),
    html.Div([
        html.Div([
            html.Div("SENTIMENT HEATMAP (ALL TICKERS)",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                dcc.Graph(id="sent-heatmap", config={"displayModeBar":False},
                          style={"height":"220px"}),
            ]),
        ], style={"flex":"1","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
        html.Div([
            html.Div("LATEST NEWS",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                html.Div(id="sent-news-feed", style={"maxHeight":"240px","overflowY":"auto"}),
            ]),
        ], style={"width":"420px","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
    ], style={"display":"flex","gap":"16px"}),
])


@callback(
    [Output("sent-timeline","figure"),
     Output("sent-gauge","figure"),
     Output("sent-heatmap","figure"),
     Output("sent-news-feed","children"),
     Output("sent-kpi-bar","children")],
    [Input("sent-ticker","value"), Input("sent-days","value")],
)
def update_sentiment(ticker, days):
    empty = go.Figure()
    empty.update_layout(**PLOT_BASE)
    defaults = (empty, empty, empty, html.Div("No data"), [])

    try:
        print(f"\nDEBUG sentiment: ticker={ticker} days={days} API_BASE={API_BASE}")

        r = requests.get(f"{API_BASE}/sentiment/{ticker}",
                         params={"days": days}, headers=HEADERS, timeout=6)
        print(f"DEBUG status={r.status_code} url={r.url}")
        print(f"DEBUG response[:300]={r.text[:300]}")

        if r.status_code != 200:
            return defaults

        payload = r.json()
        if not payload:
            return defaults

        df = pd.DataFrame(payload)
        print(f"DEBUG df shape={df.shape} cols={df.columns.tolist()}")

        df["published_at"] = pd.to_datetime(df["published_at"], utc=True).dt.tz_localize(None)
        df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0.0)
        df = df.sort_values("published_at")

        # ── Timeline ─────────────────────────────────────────────────────────
        fig_timeline = go.Figure()
        for sent, color in SENT_COLORS.items():
            grp = df[df["sentiment"] == sent]
            if not grp.empty:
                fig_timeline.add_trace(go.Scatter(
                    x=grp["published_at"], y=grp["score"],
                    mode="markers", name=sent.upper(),
                    marker=dict(size=8, color=color, opacity=0.8),
                ))
        if len(df) > 2:
            fig_timeline.add_trace(go.Scatter(
                x=df["published_at"],
                y=df["score"].rolling(3, min_periods=1).mean(),
                mode="lines", name="3-pt avg",
                line=dict(color=COLORS["blue"], width=2, dash="dot"),
            ))
        fig_timeline.update_layout(
            **PLOT_BASE, height=260,
            title=dict(text=f"<b>{ticker}</b>  ·  Sentiment Scores",
                       font=dict(size=12, color=COLORS["text"])),
        )
        fig_timeline.update_yaxes(range=[-1.1, 1.1])
        fig_timeline.add_hline(y=0, line_dash="dot",
                                line_color=COLORS["border"], line_width=1)

        # ── Gauge ─────────────────────────────────────────────────────────────
        avg_score = float(df["score"].mean())
        gauge_color = (COLORS["green"] if avg_score > 0.1 else
                       COLORS["red"]   if avg_score < -0.1 else
                       COLORS["muted"])

        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=round(avg_score, 3),
            number={"font":{"color":gauge_color,
                            "family":"'IBM Plex Mono',monospace","size":28}},
            gauge={
                "axis":{"range":[-1,1],"tickcolor":COLORS["muted"],
                        "tickfont":{"color":COLORS["muted"],"size":10}},
                "bar":{"color":gauge_color,"thickness":0.3},
                "bgcolor":COLORS["elevated"],
                "bordercolor":COLORS["border"],
                "steps":[
                    {"range":[-1,-0.1],  "color":"rgba(255,77,109,0.13)"},
                    {"range":[-0.1,0.1], "color":"rgba(139,154,179,0.13)"},
                    {"range":[0.1,1],    "color":"rgba(0,255,148,0.13)"},
                ],
                "threshold":{"line":{"color":COLORS["amber"],"width":2},
                             "thickness":0.75,"value":avg_score},
            },
        ))
        fig_gauge.update_layout(
            paper_bgcolor=COLORS["card"], plot_bgcolor=COLORS["card"],
            font=dict(color=COLORS["text"], family="'IBM Plex Mono',monospace"),
            margin=dict(l=30, r=30, t=30, b=20), height=230,
        )

        # ── Heatmap ───────────────────────────────────────────────────────────
        heatmap_tickers, heatmap_scores = [], []
        for t in TICKERS:
            try:
                rh = requests.get(f"{API_BASE}/sentiment/{t}",
                                  params={"days":7}, headers=HEADERS, timeout=3)
                if rh.status_code == 200:
                    d = rh.json()
                    if d:
                        avg = pd.to_numeric(pd.DataFrame(d)["score"],
                                            errors="coerce").fillna(0).mean()
                        heatmap_tickers.append(t)
                        heatmap_scores.append(round(float(avg), 3))
            except Exception:
                pass

        if heatmap_tickers:
            colors_hm = [COLORS["green"] if s > 0.1 else
                         COLORS["red"]   if s < -0.1 else
                         COLORS["muted"] for s in heatmap_scores]
            fig_heatmap = go.Figure(go.Bar(
                x=heatmap_tickers, y=heatmap_scores,
                marker_color=colors_hm, opacity=0.85,
            ))
            fig_heatmap.update_layout(
                **PLOT_BASE, height=200,
                title=dict(text="AVG SENTIMENT BY TICKER",
                           font=dict(size=11, color=COLORS["muted"])),
            )
            fig_heatmap.update_yaxes(range=[-1.1, 1.1])
            fig_heatmap.add_hline(y=0, line_dash="dot",
                                   line_color=COLORS["border"], line_width=1)
        else:
            fig_heatmap = go.Figure()
            fig_heatmap.update_layout(**PLOT_BASE, height=200)

        # ── News feed ─────────────────────────────────────────────────────────
        news_items = []
        for _, row in df.sort_values("published_at", ascending=False).head(15).iterrows():
            sent  = row.get("sentiment", "neutral")
            score = float(row.get("score", 0.0))
            color = SENT_COLORS.get(sent, COLORS["muted"])
            date_str = str(row["published_at"])[:16]
            news_items.append(html.Div([
                html.Div([
                    html.Span(sent.upper(), style={
                        "background":color+"22","color":color,
                        "border":f"1px solid {color}44","borderRadius":"3px",
                        "padding":"1px 6px","fontFamily":"'IBM Plex Mono',monospace",
                        "fontSize":"8px","letterSpacing":"1px","marginRight":"6px",
                    }),
                    html.Span(f"{score:+.2f}", style={
                        "fontFamily":"'IBM Plex Mono',monospace",
                        "fontSize":"10px","color":color,
                    }),
                    html.Span(date_str, style={
                        "fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                        "color":COLORS["dim"],"marginLeft":"8px",
                    }),
                ], style={"marginBottom":"3px"}),
                html.Div(row.get("headline",""), style={
                    "fontSize":"11px","color":COLORS["text"],"lineHeight":"1.4",
                }),
            ], style={"padding":"10px 0",
                      "borderBottom":f"1px solid {COLORS['border']}22"}))

        news_feed = html.Div(news_items) if news_items else \
                    html.Div("No news data", style={"color":COLORS["dim"],
                                                     "fontFamily":"'IBM Plex Mono',monospace",
                                                     "fontSize":"11px","padding":"12px"})

        # ── KPI bar ───────────────────────────────────────────────────────────
        total     = len(df)
        positives = len(df[df["sentiment"] == "positive"])
        negatives = len(df[df["sentiment"] == "negative"])
        neutrals  = len(df[df["sentiment"] == "neutral"])

        def _kpi(label, val, accent):
            return html.Div([
                html.Div(label, style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                                        "letterSpacing":"2px","color":COLORS["dim"],"marginBottom":"4px"}),
                html.Div(str(val), style={"fontFamily":"'IBM Plex Mono',monospace",
                                           "fontWeight":"600","fontSize":"22px","color":accent}),
            ], style={"background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                       "borderTop":f"2px solid {accent}","borderRadius":"6px",
                       "padding":"14px 20px","flex":"1"})

        kpi_bar = [
            _kpi("TOTAL NEWS", total,               COLORS["blue"]),
            _kpi("POSITIVE",   positives,            COLORS["green"]),
            _kpi("NEGATIVE",   negatives,            COLORS["red"]),
            _kpi("NEUTRAL",    neutrals,             COLORS["muted"]),
            _kpi("AVG SCORE",  f"{avg_score:+.3f}",  gauge_color),
        ]

        print("DEBUG sentiment callback SUCCESS")
        return fig_timeline, fig_gauge, fig_heatmap, news_feed, kpi_bar

    except Exception as e:
        traceback.print_exc()
        return (empty, empty, empty,
                html.Div(f"Error: {str(e)}", style={"color":COLORS["red"],
                                                      "fontFamily":"'IBM Plex Mono',monospace",
                                                      "padding":"12px"}),
                [])