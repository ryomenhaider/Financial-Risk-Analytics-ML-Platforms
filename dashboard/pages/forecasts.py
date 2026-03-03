
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import dash, requests
from dash import dcc, html, Input, Output, callback, State
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
from dashboard.theme import COLORS, PLOT_BASE, API_BASE, HEADERS  # ✅ safe
dash.register_page(__name__, path="/forecasts", name="Forecasting Center", order=2)

TICKERS  = ["AAPL","MSFT","GOOGL","TSLA","NVDA","BTC-USD","ETH-USD","SPY"]
HORIZONS = [{"label":"7 Days","value":7}, {"label":"30 Days","value":30},
            {"label":"90 Days","value":90}]

def _metric_card(label, val_id, accent):
    return html.Div([
        html.Div(label, style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                                "letterSpacing":"2px","color":COLORS["dim"],"marginBottom":"4px"}),
        html.Div(id=val_id, children="—", style={"fontFamily":"'IBM Plex Mono',monospace",
                                                   "fontWeight":"600","fontSize":"20px","color":accent}),
    ], style={"background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
               "borderTop":f"2px solid {accent}","borderRadius":"6px",
               "padding":"14px 20px","flex":"1","minWidth":"110px"})



layout = html.Div([
    html.Div(
        "⚠  MODEL PREDICTIONS ONLY — NOT INVESTMENT ADVICE",
        style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px","letterSpacing":"2px",
               "color":COLORS["amber"],"background":COLORS["amber"]+"11",
               "border":f"1px solid {COLORS['amber']}33","borderRadius":"4px",
               "padding":"8px 16px","marginBottom":"20px","textAlign":"center"},
    ),

    html.Div([
        html.Div([
            html.Span("FORECASTING CENTER", style={"fontFamily":"'IBM Plex Mono',monospace",
                                                    "fontWeight":"600","fontSize":"13px",
                                                    "color":COLORS["text"],"letterSpacing":"3px"}),
            html.Div("Prophet (trend + seasonality)  ·  XGBoost (feature-based ensemble)",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"9px",
                             "color":COLORS["dim"],"marginTop":"3px"}),
        ]),
        html.Div([
            dcc.Dropdown(id="fc-ticker", options=[{"label":t,"value":t} for t in TICKERS],
                         value="AAPL", clearable=False,
                         style={"width":"150px","fontFamily":"'IBM Plex Mono',monospace",
                                "fontSize":"12px","background":COLORS["elevated"],
                                "border":f"1px solid {COLORS['border']}"}),
            dcc.Dropdown(id="fc-horizon", options=HORIZONS, value=30, clearable=False,
                         style={"width":"120px","fontFamily":"'IBM Plex Mono',monospace",
                                "fontSize":"12px","background":COLORS["elevated"],
                                "border":f"1px solid {COLORS['border']}","marginLeft":"8px"}),
        ], style={"display":"flex","alignItems":"center"}),
    ], style={"display":"flex","justifyContent":"space-between","alignItems":"flex-start",
              "marginBottom":"24px"}),

    # Metric cards
    html.Div([
        _metric_card("YHAT",       "fc-latest", COLORS["blue"]),
        _metric_card("YHAT_UPPER", "fc-upper",  COLORS["green"]),
        _metric_card("YHAT_LOWER", "fc-lower",  COLORS["red"]),
        _metric_card("MODEL",      "fc-model",  COLORS["purple"]),
        _metric_card("HORIZON",    "fc-horiz",  COLORS["muted"]),
    ], style={"display":"flex","gap":"12px","marginBottom":"20px","flexWrap":"wrap"}),

    # Main forecast chart
    dcc.Loading(type="circle", color=COLORS["blue"], children=[
        dcc.Graph(id="fc-main-chart", config={"displayModeBar":False},
                  style={"borderRadius":"6px","border":f"1px solid {COLORS['border']}",
                         "marginBottom":"20px"}),
    ]),

    # Comparison section
    html.Div([
        html.Div("FORECAST COMPARISON", style={"fontFamily":"'IBM Plex Mono',monospace",
                                                 "fontSize":"10px","letterSpacing":"2px",
                                                 "color":COLORS["dim"],"marginBottom":"12px"}),
        html.Div([
            dcc.Input(id="fc-compare-tickers", type="text", placeholder="Enter tickers (e.g., AAPL,MSFT,GOOGL)",
                      style={"flex":"1","padding":"8px 12px","fontFamily":"'IBM Plex Mono',monospace",
                             "fontSize":"12px","background":COLORS["elevated"],
                             "border":f"1px solid {COLORS['border']}","borderRadius":"4px",
                             "color":COLORS["text"]}),
            html.Button("COMPARE", id="fc-compare-btn", n_clicks=0,
                       style={"marginLeft":"8px","padding":"8px 16px","fontFamily":"'IBM Plex Mono',monospace",
                              "fontSize":"10px","fontWeight":"600","background":COLORS["blue"],
                              "color":COLORS["bg"],"border":"none","borderRadius":"4px","cursor":"pointer"}),
        ], style={"display":"flex","gap":"8px","marginBottom":"16px"}),
        dcc.Loading(type="dot", color=COLORS["blue"], children=[
            dcc.Graph(id="fc-compare-chart", config={"displayModeBar":False},
                      style={"borderRadius":"6px","border":f"1px solid {COLORS['border']}"}),
        ]),
    ], style={"background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
              "borderRadius":"6px","padding":"16px","marginBottom":"20px"}),

    # Forecast table
    html.Div([
        html.Div("FORECAST TABLE (NEXT 10 DAYS)",
                 style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                         "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
        dcc.Loading(type="dot", color=COLORS["blue"], children=[
            html.Div(id="fc-table"),
        ]),
    ], style={"background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
              "borderRadius":"6px","padding":"16px"}),
])



@callback(
    [Output("fc-main-chart","figure"), Output("fc-table","children"),
     Output("fc-latest","children"), Output("fc-upper","children"),
     Output("fc-lower","children"), Output("fc-model","children"),
     Output("fc-horiz","children")],
    [Input("fc-ticker","value"), Input("fc-horizon","value")],
)
def update_forecast(ticker, horizon):
    empty = go.Figure()
    empty.update_layout(**PLOT_BASE)
    defaults = (empty, html.Div("No data"), "—","—","—","—","—")

    try:
        # Fetch forecasts from endpoint: GET /forecasts/{ticker}?horizon=30
        r = requests.get(f"{API_BASE}/forecasts/{ticker}",
                         params={"horizon": horizon}, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return defaults
        payload = r.json()
    except Exception as e:
        return defaults

    # payload should be list[ForecastResponse]
    if not isinstance(payload, list) or not payload:
        return defaults

    fc = pd.DataFrame(payload)
    
    # Ensure forecast_date is datetime
    fc["forecast_date"] = pd.to_datetime(fc["forecast_date"])
    fc = fc.sort_values("forecast_date").reset_index(drop=True)

    # Fetch historical prices for context
    try:
        rh = requests.get(f"{API_BASE}/prices/{ticker}/history",
                          params={"limit": 90}, headers=HEADERS, timeout=6)
        if rh.status_code == 200:
            hist = pd.DataFrame(rh.json())
            hist["date"] = pd.to_datetime(hist["date"])
            hist = hist.sort_values("date")
        else:
            hist = pd.DataFrame()
    except Exception:
        hist = pd.DataFrame()
    # Build main chart
    fig = go.Figure()
    
    # Add historical prices
    if not hist.empty and "close" in hist.columns:
        fig.add_trace(go.Scatter(
            x=hist["date"], y=hist["close"], name="Historical",
            line=dict(color=COLORS["blue"], width=2), mode="lines",
        ))
    
    # Add confidence band
    if "yhat_upper" in fc.columns and "yhat_lower" in fc.columns:
        fig.add_trace(go.Scatter(
            x=list(fc["forecast_date"]) + list(fc["forecast_date"])[::-1],
            y=list(fc["yhat_upper"]) + list(fc["yhat_lower"])[::-1],
            fill="toself", fillcolor=COLORS["green"]+"18",
            line=dict(color="rgba(0,0,0,0)"), name="95% Confidence Band", 
            showlegend=True, hoverinfo="skip",
        ))
    
    # Add forecast line
    if "yhat" in fc.columns:
        fig.add_trace(go.Scatter(
            x=fc["forecast_date"], y=fc["yhat"], name="Forecast",
            line=dict(color=COLORS["green"], width=2, dash="dash"), mode="lines+markers",
        ))
    
    fig.update_layout(**PLOT_BASE, height=400,
                       title=dict(text=f"<b>{ticker}</b>  ·  {horizon}-Day Forecast",
                                  font=dict(size=12, color=COLORS["text"])))

    # Build forecast table
    rows = []
    for _, row in fc.head(10).iterrows():
        date_str = str(row["forecast_date"])[:10]
        yhat = f"${row.get('yhat', 0):.2f}" if pd.notna(row.get('yhat')) else "—"
        upper = f"${row.get('yhat_upper', 0):.2f}" if pd.notna(row.get('yhat_upper')) else "—"
        lower = f"${row.get('yhat_lower', 0):.2f}" if pd.notna(row.get('yhat_lower')) else "—"
        
        rows.append(html.Tr([
            html.Td(date_str, style=_td(COLORS["muted"])),
            html.Td(yhat, style=_td(COLORS["green"])),
            html.Td(lower, style=_td(COLORS["dim"])),
            html.Td(upper, style=_td(COLORS["dim"])),
        ]))
    
    table = html.Table(
        [html.Thead(html.Tr([
            html.Th("DATE", style=_th()), html.Th("FORECAST", style=_th()),
            html.Th("LOWER BOUND", style=_th()),  html.Th("UPPER BOUND", style=_th()),
        ]))] + [html.Tbody(rows)],
        style={"width":"100%","borderCollapse":"collapse","fontFamily":"'IBM Plex Mono',monospace"},
    )

    # Extract latest forecast values for metric cards
    latest = fc.iloc[-1] if not fc.empty else {}
    yhat_val = f"${latest.get('yhat', 0):.2f}" if pd.notna(latest.get('yhat')) else "—"
    upper_val = f"${latest.get('yhat_upper', 0):.2f}" if pd.notna(latest.get('yhat_upper')) else "—"
    lower_val = f"${latest.get('yhat_lower', 0):.2f}" if pd.notna(latest.get('yhat_lower')) else "—"
    model = latest.get("model_used", "Prophet")[:15] if pd.notna(latest.get("model_used")) else "—"

    return fig, table, yhat_val, upper_val, lower_val, model, f"{horizon}D"


@callback(
    Output("fc-compare-chart", "figure"),
    [Input("fc-compare-btn", "n_clicks"), Input("fc-horizon", "value")],
    State("fc-compare-tickers", "value"),
    prevent_initial_call=True,
)
def update_compare(n_clicks, horizon, tickers_str):
    if not tickers_str or not tickers_str.strip():
        empty = go.Figure()
        empty.update_layout(**PLOT_BASE)
        return empty

    try:
        # Use compare endpoint: GET /forecasts/compare?tickers=AAPL,MSFT&horizon=30
        tickers = ",".join([t.strip().upper() for t in tickers_str.split(",")])
        r = requests.get(f"{API_BASE}/forecasts/compare",
                         params={"tickers": tickers, "horizon": horizon}, 
                         headers=HEADERS, timeout=10)
        if r.status_code != 200:
            empty = go.Figure()
            empty.update_layout(**PLOT_BASE)
            return empty
        
        payload = r.json()
    except Exception:
        empty = go.Figure()
        empty.update_layout(**PLOT_BASE)
        return empty

    fig = go.Figure()
    
    # payload should be dict with ticker keys
    if not isinstance(payload, dict):
        empty = go.Figure()
        empty.update_layout(**PLOT_BASE)
        return empty

    colors_list = [COLORS["blue"], COLORS["green"], COLORS["amber"], COLORS["red"], COLORS["purple"]]
    
    for idx, (ticker, data) in enumerate(payload.items()):
        if not isinstance(data, list):
            data = [data]
        
        df = pd.DataFrame(data)
        if "forecast_date" in df.columns and "yhat" in df.columns:
            df["forecast_date"] = pd.to_datetime(df["forecast_date"])
            df = df.sort_values("forecast_date")
            
            color = colors_list[idx % len(colors_list)]
            fig.add_trace(go.Scatter(
                x=df["forecast_date"], y=df["yhat"], name=ticker,
                line=dict(color=color, width=2), mode="lines+markers",
            ))

    fig.update_layout(**PLOT_BASE, height=350, hovermode="x unified",
                       title=dict(text="FORECAST COMPARISON", 
                                  font=dict(size=11, color=COLORS["muted"])))
    
    return fig

def _th():
    return {"fontSize":"9px","color":COLORS["dim"],"letterSpacing":"1.5px",
            "padding":"5px 6px","textAlign":"left","borderBottom":f"1px solid {COLORS['border']}"}

def _td(color):
    return {"fontFamily":"'IBM Plex Mono',monospace","fontSize":"11px","color":color,
            "padding":"6px 6px","borderBottom":f"1px solid {COLORS['border']}22"}
