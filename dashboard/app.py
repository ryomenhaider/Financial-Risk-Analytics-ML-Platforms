# dashboard/app.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os
import requests
import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output

# FIX: import everything from theme — do NOT redefine COLORS or PLOT_BASE here
from dashboard.theme import COLORS, PLOT_BASE, API_HEALTH, HEADERS

# /dashboard/ must match the FastAPI mount point
DASH_URL_BASE = os.getenv("DASH_URL_BASE_PATHNAME", "/dashboard/")

app = dash.Dash(
    __name__,
    use_pages=True,
    # FIX: cannot supply url_base_pathname AND requests_pathname_prefix together —
    # Dash raises InvalidConfig. Use routes_pathname_prefix + requests_pathname_prefix
    # explicitly instead. Both must match the FastAPI mount point /dashboard/
    routes_pathname_prefix=DASH_URL_BASE,
    requests_pathname_prefix=DASH_URL_BASE,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600"
        "&family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
app.title = "FIP — Financial Intelligence Platform"

# Exposed to FastAPI WSGIMiddleware
server = app.server

_NAV = [
    ("📈", "MARKET",    "/dashboard/"),
    ("🔍", "ANOMALY",   "/dashboard/anomalies"),
    ("🧠", "FORECAST",  "/dashboard/forecasts"),
    ("⚖️", "PORTFOLIO", "/dashboard/portfolio"),
    ("💬", "SENTIMENT", "/dashboard/sentiment"),
]

def _nl(icon, label, href):
    return dcc.Link(
        html.Div([
            html.Span(icon, style={"marginRight": "6px", "fontSize": "13px"}),
            html.Span(label, style={
                "fontFamily": "'IBM Plex Mono',monospace",
                "fontWeight": "500", "fontSize": "10px", "letterSpacing": "2px",
            }),
        ], style={
            "display": "flex", "alignItems": "center",
            "padding": "6px 14px", "borderRadius": "4px", "color": COLORS["muted"],
        }),
        href=href, style={"textDecoration": "none"},
    )

navbar = html.Div([
    html.Div([
        html.Span("FIP", style={
            "fontFamily": "'IBM Plex Mono',monospace", "fontWeight": "600",
            "fontSize": "17px", "color": COLORS["blue"], "letterSpacing": "5px",
        }),
        html.Div("FINANCIAL INTELLIGENCE PLATFORM", style={
            "fontFamily": "'IBM Plex Mono',monospace", "fontSize": "8px",
            "color": COLORS["dim"], "letterSpacing": "2.5px", "marginTop": "2px",
        }),
    ], style={"padding": "0 28px"}),
    html.Div(
        [_nl(i, l, h) for i, l, h in _NAV],
        style={"display": "flex", "gap": "2px", "alignItems": "center"},
    ),
    html.Div([
        html.Div(id="nav-status"),
        dcc.Interval(id="status-tick", interval=30_000, n_intervals=0),
    ], style={"padding": "0 28px", "display": "flex", "alignItems": "center"}),
], style={
    "display": "flex", "justifyContent": "space-between", "alignItems": "center",
    "height": "58px", "background": COLORS["card"],
    "borderBottom": f"1px solid {COLORS['border']}",
    "position": "sticky", "top": "0", "zIndex": "1000",
})

app.layout = html.Div([
    navbar,
    html.Div(
        dash.page_container,
        style={"minHeight": "calc(100vh - 58px)", "background": COLORS["bg"], "padding": "28px"},
    ),
], style={"background": COLORS["bg"], "minHeight": "100vh", "fontFamily": "'IBM Plex Sans',sans-serif"})


@app.callback(Output("nav-status", "children"), Input("status-tick", "n_intervals"))
def _ping(_):
    dot, label, color = "●", "LIVE", COLORS["green"]
    try:
        # FIX: API_HEALTH is now correctly set to /api/health in theme.py
        r = requests.get(API_HEALTH, timeout=2, headers=HEADERS)
        if r.status_code != 200:
            dot, label, color = "●", "DEGRADED", COLORS["amber"]
    except Exception:
        dot, label, color = "●", "OFFLINE", COLORS["red"]
    return html.Span([
        html.Span(dot, style={"color": color, "marginRight": "6px", "fontSize": "9px"}),
        html.Span(label, style={
            "fontFamily": "'IBM Plex Mono',monospace", "fontSize": "10px",
            "color": color, "letterSpacing": "2px",
        }),
    ], style={"display": "flex", "alignItems": "center"})

