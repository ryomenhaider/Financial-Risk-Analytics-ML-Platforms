import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import dash, requests
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from dashboard.theme import COLORS, PLOT_BASE, API_BASE, HEADERS
from config.logging_config import get_logger

dash.register_page(__name__, path="/anomalies", name="Anomaly Intelligence", order=1)

logger = get_logger(__name__)

SEVERITY_OPTIONS = [
    {"label":"All",      "value":"all"},
    {"label":"Critical", "value":"critical"},
    {"label":"High",     "value":"high"},
    {"label":"Medium",   "value":"medium"},
    {"label":"Low",      "value":"low"},
]

# ✅ FIX: added "critical" to color map
SEV_COLORS = {
    "critical": "#FF0055",
    "high":     COLORS["red"],
    "medium":   COLORS["amber"],
    "low":      COLORS["purple"],
}

TICKERS = ["AAPL","MSFT","GOOGL","TSLA","NVDA","BTC-USD","ETH-USD","SPY"]

def _badge(text, color):
    return html.Span(text, style={
        "background": color+"22", "color": color,
        "border": f"1px solid {color}44", "borderRadius":"3px",
        "padding":"2px 7px", "fontFamily":"'IBM Plex Mono',monospace",
        "fontSize":"9px", "letterSpacing":"1px", "fontWeight":"600",
    })

layout = html.Div([
    html.Div([
        html.Div([
            html.Span("ANOMALY INTELLIGENCE", style={"fontFamily":"'IBM Plex Mono',monospace",
                                                      "fontWeight":"600","fontSize":"13px",
                                                      "color":COLORS["text"],"letterSpacing":"3px"}),
            html.Div("Isolation Forest · AutoEncoder · Ensemble Voting",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                             "color":COLORS["dim"],"marginTop":"3px"}),
        ]),
        html.Div([
            dcc.Dropdown(id="an-ticker", options=[{"label":t,"value":t} for t in TICKERS],
                         value="AAPL", clearable=False,
                         style={"width":"150px","fontFamily":"'IBM Plex Mono',monospace",
                                "fontSize":"12px","background":COLORS["elevated"],
                                "border":f"1px solid {COLORS['border']}"}),
            dcc.Dropdown(id="an-days",
                         options=[{"label":"7D","value":7},{"label":"30D","value":30},
                                  {"label":"90D","value":90}],
                         value=30, clearable=False,
                         style={"width":"90px","fontFamily":"'IBM Plex Mono',monospace",
                                "fontSize":"12px","background":COLORS["elevated"],
                                "border":f"1px solid {COLORS['border']}","marginLeft":"8px"}),
            dcc.Dropdown(id="an-severity", options=SEVERITY_OPTIONS, value="all", clearable=False,
                         style={"width":"120px","fontFamily":"'IBM Plex Mono',monospace",
                                "fontSize":"12px","background":COLORS["elevated"],
                                "border":f"1px solid {COLORS['border']}","marginLeft":"8px"}),
        ], style={"display":"flex","alignItems":"center"}),
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"flex-start",
              "marginBottom":"24px"}),

    html.Div([
        html.Div([
            html.Div("TOTAL FLAGS", style={"fontFamily":"'IBM Plex Mono',monospace",
                                            "fontSize":"9px","letterSpacing":"2px",
                                            "color":COLORS["dim"],"marginBottom":"4px"}),
            html.Div(id="an-count", style={"fontFamily":"'IBM Plex Mono',monospace",
                                            "fontWeight":"600","fontSize":"28px","color":COLORS["red"]}),
        ], style={"background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderTop":f"2px solid {COLORS['red']}","borderRadius":"6px",
                   "padding":"14px 20px","flex":"1"}),
        html.Div([
            html.Div("HIGH / CRITICAL", style={"fontFamily":"'IBM Plex Mono',monospace",
                                                "fontSize":"9px","letterSpacing":"2px",
                                                "color":COLORS["dim"],"marginBottom":"4px"}),
            html.Div(id="an-high", style={"fontFamily":"'IBM Plex Mono',monospace",
                                           "fontWeight":"600","fontSize":"28px","color":COLORS["amber"]}),
        ], style={"background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderTop":f"2px solid {COLORS['amber']}","borderRadius":"6px",
                   "padding":"14px 20px","flex":"1"}),
        html.Div([
            html.Div("AVG SCORE", style={"fontFamily":"'IBM Plex Mono',monospace",
                                          "fontSize":"9px","letterSpacing":"2px",
                                          "color":COLORS["dim"],"marginBottom":"4px"}),
            html.Div(id="an-avg", style={"fontFamily":"'IBM Plex Mono',monospace",
                                          "fontWeight":"600","fontSize":"28px","color":COLORS["purple"]}),
        ], style={"background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderTop":f"2px solid {COLORS['purple']}","borderRadius":"6px",
                   "padding":"14px 20px","flex":"1"}),
    ], style={"display":"flex","gap":"12px","marginBottom":"20px"}),

    dcc.Loading(type="circle", color=COLORS["red"], children=[
        dcc.Graph(id="an-price-chart", config={"displayModeBar":False},
                  style={"borderRadius":"6px","border":f"1px solid {COLORS['border']}",
                         "marginBottom":"20px"}),
    ]),

    html.Div([
        html.Div([
            html.Div("ANOMALY SCORE TIMELINE",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["red"], children=[
                dcc.Graph(id="an-score-chart", config={"displayModeBar":False},
                          style={"height":"240px"}),
            ]),
        ], style={"flex":"1","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
        html.Div([
            html.Div("FLAGGED EVENTS",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["red"], children=[
                html.Div(id="an-events-table", style={"maxHeight":"260px","overflowY":"auto"}),
            ]),
        ], style={"width":"420px","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
    ], style={"display":"flex","gap":"16px"}),
])


@callback(
    [Output("an-price-chart","figure"), Output("an-score-chart","figure"),
     Output("an-events-table","children"), Output("an-count","children"),
     Output("an-high","children"), Output("an-avg","children")],
    [Input("an-ticker","value"), Input("an-days","value"), Input("an-severity","value")],
    prevent_initial_call=False,
)
def update_anomaly(ticker, days, severity):
    empty = go.Figure()
    empty.update_layout(**PLOT_BASE)
    defaults = (empty, empty, html.Div("No data"), "—", "—", "—")

    # Fetch prices
    try:
        rp = requests.get(f"{API_BASE}/prices/{ticker}/history",
                          params={"limit": days}, headers=HEADERS, timeout=6)
        if rp.status_code != 200:
            return defaults
        prices = pd.DataFrame(rp.json())
        if prices.empty:
            return defaults
        prices["date"] = pd.to_datetime(prices["date"], utc=True).dt.tz_localize(None)
        
        # ✅ FIX: Convert numeric columns
        for col in ["open", "high", "low", "close", "volume"]:
            if col in prices.columns:
                prices[col] = pd.to_numeric(prices[col], errors="coerce")
        
        # Normalize to date only for merging
        prices["date_only"] = prices["date"].dt.date
        prices = prices.sort_values("date")
    except Exception as e:
        logger.error(f"Prices fetch error: {e}")
        return defaults

    # Fetch anomalies
    try:
        ra = requests.get(f"{API_BASE}/anomalies",
                          params={"ticker": ticker, "days": days},
                          headers=HEADERS, timeout=6)
        anomalies = pd.DataFrame(ra.json()) if ra.status_code == 200 else pd.DataFrame()
    except Exception:
        anomalies = pd.DataFrame()

    # Parse anomaly dates
    if not anomalies.empty:
        date_col = "date" if "date" in anomalies.columns else "created_at"
        anomalies["date"] = pd.to_datetime(anomalies[date_col], utc=True).dt.tz_localize(None)
        anomalies["date_only"] = anomalies["date"].dt.date

        # ✅ Deduplicate: one anomaly per date (keep highest score)
        anomalies = (anomalies.sort_values("anomaly_score", ascending=False)
                               .drop_duplicates(subset=["date_only"], keep="first"))

        if severity != "all" and "severity" in anomalies.columns:
            anomalies = anomalies[anomalies["severity"] == severity]

    # Price chart
    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(
        x=prices["date"], y=prices["close"], name="Close",
        line=dict(color=COLORS["blue"], width=1.5), mode="lines",
    ))

    if not anomalies.empty and "date_only" in anomalies.columns:
        try:
            # Build a date→close lookup from prices
            price_lookup = prices.set_index("date_only")["close"].to_dict()
            anomalies["close_price"] = anomalies["date_only"].map(price_lookup)

            # ✅ FIX: use SEV_COLORS which includes "critical"
            for sev, color in SEV_COLORS.items():
                grp = anomalies[anomalies.get("severity", pd.Series()) == sev] if "severity" in anomalies.columns \
                      else pd.DataFrame()
                if anomalies.empty or "severity" not in anomalies.columns:
                    grp = anomalies  # no severity column, plot all as one group
                else:
                    grp = anomalies[anomalies["severity"] == sev]

                grp = grp.dropna(subset=["close_price"])
                if not grp.empty:
                    fig_price.add_trace(go.Scatter(
                        x=grp["date"], y=grp["close_price"],
                        mode="markers", name=sev.upper(),
                        marker=dict(symbol="x", size=12, color=color,
                                    line=dict(width=2)),
                    ))
        except Exception as e:
            logger.error(f"Anomaly marker error: {e}")

    fig_price.update_layout(**PLOT_BASE, height=340,
                             title=dict(text=f"<b>{ticker}</b>  ·  Price + Anomaly Events",
                                        font=dict(size=12, color=COLORS["text"])))

    # Score timeline
    fig_score = go.Figure()
    if not anomalies.empty and "anomaly_score" in anomalies.columns:
        an_sorted = anomalies.sort_values("date")
        fig_score.add_trace(go.Scatter(
            x=an_sorted["date"], y=an_sorted["anomaly_score"],
            mode="lines+markers",
            line=dict(color=COLORS["red"], width=1.5),
            marker=dict(size=5, color=COLORS["amber"]),
            fill="tozeroy", fillcolor="rgba(255, 77, 109, 0.13)", name="Score",
        ))
        fig_score.add_hline(y=0.7, line_dash="dot", line_color=COLORS["amber"],
                             annotation_text="Threshold", annotation_position="right")
    fig_score.update_layout(**PLOT_BASE, height=240,
                             title=dict(text="ANOMALY SCORE  (0–1)",
                                        font=dict(size=11, color=COLORS["muted"])),
                             yaxis_range=[0, 1])

    # Events table
    if anomalies.empty:
        table = html.Div("No anomalies detected",
                        style={"color":COLORS["dim"],"fontFamily":"'IBM Plex Mono',monospace",
                               "fontSize":"11px","padding":"16px"})
    else:
        rows = []
        for _, row in anomalies.sort_values("date", ascending=False).head(20).iterrows():
            date_str = str(row.get("date", "—"))[:16]
            sev      = row.get("severity", "low")
            score    = row.get("anomaly_score", 0)
            model    = row.get("model_used", "—")
            color    = SEV_COLORS.get(sev, COLORS["muted"])  # ✅ safe lookup
            rows.append(html.Tr([
                html.Td(date_str, style=_td(COLORS["muted"])),
                html.Td(model,    style=_td(COLORS["text"])),
                html.Td(_badge(sev.upper(), color),
                        style={"padding":"5px 6px","borderBottom":f"1px solid {COLORS['border']}22"}),
                html.Td(f"{score:.3f}", style=_td(COLORS["amber"])),
            ]))
        table = html.Table(
            [html.Thead(html.Tr([
                html.Th("TIMESTAMP", style=_th()), html.Th("MODEL", style=_th()),
                html.Th("SEVERITY",  style=_th()), html.Th("SCORE", style=_th()),
            ]))] + [html.Tbody(rows)],
            style={"width":"100%","borderCollapse":"collapse","fontFamily":"'IBM Plex Mono',monospace"},
        )

    total   = len(anomalies) if not anomalies.empty else 0
    highs   = len(anomalies[anomalies["severity"].isin(["high","critical"])]) \
              if not anomalies.empty and "severity" in anomalies.columns else 0
    avg_sc  = f"{anomalies['anomaly_score'].mean():.3f}" \
              if not anomalies.empty and "anomaly_score" in anomalies.columns else "—"

    return fig_price, fig_score, table, str(total), str(highs), avg_sc


def _th():
    return {"fontSize":"9px","color":COLORS["dim"],"letterSpacing":"1.5px",
            "padding":"5px 6px","textAlign":"left","borderBottom":f"1px solid {COLORS['border']}"}

def _td(color):
    return {"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px","color":color,
            "padding":"5px 6px","borderBottom":f"1px solid {COLORS['border']}22"}