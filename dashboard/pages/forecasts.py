
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import dash, requests
from dash import dcc, html, Input, Output, callback
import plotly.graph_objects as go
import pandas as pd
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
        _metric_card("MAE",         "fc-mae",  COLORS["blue"]),
        _metric_card("MAPE",        "fc-mape", COLORS["amber"]),
        _metric_card("RMSE",        "fc-rmse", COLORS["purple"]),
        _metric_card("MODEL",       "fc-model", COLORS["green"]),
        _metric_card("HORIZON",     "fc-horiz", COLORS["muted"]),
    ], style={"display":"flex","gap":"12px","marginBottom":"20px","flexWrap":"wrap"}),

    # Main forecast chart
    dcc.Loading(type="circle", color=COLORS["blue"], children=[
        dcc.Graph(id="fc-main-chart", config={"displayModeBar":False},
                  style={"borderRadius":"6px","border":f"1px solid {COLORS['border']}",
                         "marginBottom":"20px"}),
    ]),

    # Feature importance + model comparison
    html.Div([
        html.Div([
            html.Div("XGBOOST FEATURE IMPORTANCE",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                dcc.Graph(id="fc-feat-chart", config={"displayModeBar":False},
                          style={"height":"320px"}),
            ]),
        ], style={"flex":"1","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),

        html.Div([
            html.Div("FORECAST TABLE (NEXT 10 DAYS)",
                     style={"fontFamily":"'IBM Plex Mono',monospace","fontSize":"10px",
                             "letterSpacing":"2px","color":COLORS["muted"],"marginBottom":"12px"}),
            dcc.Loading(type="dot", color=COLORS["blue"], children=[
                html.Div(id="fc-table"),
            ]),
        ], style={"width":"340px","background":COLORS["card"],"border":f"1px solid {COLORS['border']}",
                   "borderRadius":"6px","padding":"16px"}),
    ], style={"display":"flex","gap":"16px"}),
])



@callback(
    [Output("fc-main-chart","figure"), Output("fc-feat-chart","figure"),
     Output("fc-table","children"),
     Output("fc-mae","children"), Output("fc-mape","children"),
     Output("fc-rmse","children"), Output("fc-model","children"),
     Output("fc-horiz","children")],
    [Input("fc-ticker","value"), Input("fc-horizon","value")],
)
def update_forecast(ticker, horizon):
    empty = go.Figure()
    empty.update_layout(**PLOT_BASE)
    defaults = (empty, empty, html.Div("No data"), "—","—","—","—","—")

    try:
        r = requests.get(f"{API_BASE}/forecast/{ticker}",
                         params={"horizon": horizon}, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return defaults
        payload = r.json()
    except Exception:
        return defaults

    # Support both flat list and dict with 'forecast' + 'metrics' keys
    if isinstance(payload, list):
        fc_rows = payload
        metrics = {}
    else:
        fc_rows  = payload.get("forecast", payload.get("predictions", []))
        metrics  = payload.get("metrics", {})

    if not fc_rows:
        return defaults

    fc  = pd.DataFrame(fc_rows)
    fc["forecast_date"] = pd.to_datetime(fc.get("forecast_date", fc.get("ds", fc.get("date"))))
    yhat = fc.get("predicted_close", fc.get("yhat", fc.get("predicted_price")))

    # Historical prices for context
    try:
        rh = requests.get(f"{API_BASE}/prices/{ticker}/history",
                          params={"days": 60}, headers=HEADERS, timeout=6)
        hist = pd.DataFrame(rh.json())
        hist["timestamp"] = pd.to_datetime(hist["timestamp"])
        hist = hist.sort_values("timestamp")
    except Exception:
        hist = pd.DataFrame()

    # Main chart
    fig = go.Figure()
    if not hist.empty:
        fig.add_trace(go.Scatter(
            x=hist["timestamp"], y=hist["close"], name="Actual",
            line=dict(color=COLORS["blue"], width=2), mode="lines",
        ))
    # Confidence band
    if "yhat_upper" in fc.columns and "yhat_lower" in fc.columns:
        fig.add_trace(go.Scatter(
            x=list(fc["forecast_date"]) + list(fc["forecast_date"])[::-1],
            y=list(fc["yhat_upper"]) + list(fc["yhat_lower"])[::-1],
            fill="toself", fillcolor=COLORS["green"]+"18",
            line=dict(color="rgba(0,0,0,0)"), name="Confidence Band", showlegend=True,
        ))
    # Forecast line
    y_col = "predicted_close" if "predicted_close" in fc.columns else \
            "yhat" if "yhat" in fc.columns else "predicted_price"
    if y_col in fc.columns:
        fig.add_trace(go.Scatter(
            x=fc["forecast_date"], y=fc[y_col], name="Forecast",
            line=dict(color=COLORS["green"], width=2, dash="dash"), mode="lines",
        ))
    fig.update_layout(**PLOT_BASE, height=400,
                       title=dict(text=f"<b>{ticker}</b>  ·  {horizon}-Day Price Forecast",
                                  font=dict(size=12, color=COLORS["text"])))

    # Feature importance
    fi_fig = go.Figure()
    feat_imp = metrics.get("feature_importance") or payload.get("feature_importance")
    if feat_imp and isinstance(feat_imp, dict):
        sorted_f = sorted(feat_imp.items(), key=lambda x: x[1], reverse=True)[:15]
        names = [f[0] for f in sorted_f]
        vals  = [f[1] for f in sorted_f]
        fi_fig.add_trace(go.Bar(x=vals, y=names, orientation="h",
                                 marker_color=COLORS["blue"], opacity=0.85))
    else:
        fi_fig.add_annotation(text="Feature importance not available",
                               x=0.5, y=0.5, showarrow=False,
                               font=dict(color=COLORS["muted"], size=12))
    fi_fig.update_layout(**PLOT_BASE, height=280,
                          xaxis_title="Importance Score",
                          title=dict(text="TOP FEATURES", font=dict(size=11, color=COLORS["muted"])))

    # Forecast table
    y_vals = fc[y_col] if y_col in fc.columns else pd.Series([])
    rows = []
    for _, row in fc.head(10).iterrows():
        pred = row.get(y_col, 0)
        lo   = row.get("yhat_lower", row.get("lower", "—"))
        hi   = row.get("yhat_upper", row.get("upper", "—"))
        rows.append(html.Tr([
            html.Td(str(row["forecast_date"])[:10], style=_td(COLORS["muted"])),
            html.Td(f"${pred:.2f}",                style=_td(COLORS["green"])),
            html.Td(f"${lo:.2f}" if isinstance(lo,(int,float)) else str(lo), style=_td(COLORS["dim"])),
            html.Td(f"${hi:.2f}" if isinstance(hi,(int,float)) else str(hi), style=_td(COLORS["dim"])),
        ]))
    table = html.Table(
        [html.Thead(html.Tr([
            html.Th("DATE", style=_th()), html.Th("FORECAST", style=_th()),
            html.Th("LOW CI", style=_th()),  html.Th("HIGH CI", style=_th()),
        ]))] + [html.Tbody(rows)],
        style={"width":"100%","borderCollapse":"collapse","fontFamily":"'IBM Plex Mono',monospace"},
    )

    mae   = f"{metrics.get('test_mae', metrics.get('mae','—')):.4f}" if isinstance(metrics.get('test_mae',metrics.get('mae')), (int,float)) else "—"
    mape  = f"{metrics.get('test_mape', metrics.get('mape','—')):.2f}%" if isinstance(metrics.get('test_mape',metrics.get('mape')), (int,float)) else "—"
    rmse  = f"{metrics.get('rmse','—'):.4f}" if isinstance(metrics.get('rmse'), (int,float)) else "—"
    model = (payload.get("model_version") or payload.get("model","XGBoost+Prophet"))[:12]

    return fig, fi_fig, table, mae, mape, rmse, model, f"{horizon}D"

def _th():
    return {"fontSize":"9px","color":COLORS["dim"],"letterSpacing":"1.5px",
            "padding":"5px 6px","textAlign":"left","borderBottom":f"1px solid {COLORS['border']}"}
def _td(color):
    return {"fontFamily":"'IBM Plex Mono',monospace","fontSize":"11px","color":color,
            "padding":"6px 6px","borderBottom":f"1px solid {COLORS['border']}22"}