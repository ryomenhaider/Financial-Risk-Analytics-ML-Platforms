"""
Phase 6 Dashboard — app.py
Entry point. Creates Dash app, dark theme, registers pages, configures routing.
Run: python dashboard/app.py  →  http://localhost:8050
"""

import dash
from dash import Dash, html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc
import datetime

app = Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.CYBORG,
        dbc.icons.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;700;800&display=swap",
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
app.title = "FinDash · Phase 6"
server = app.server  # expose for gunicorn

# ── Navigation items ──────────────────────────────────────────────────────────
NAV_ITEMS = [
    {"label": "Market Overview",     "href": "/overview",  "icon": "bi-grid-3x3-gap-fill"},
    {"label": "Anomaly Detector",    "href": "/anomalies", "icon": "bi-exclamation-triangle-fill"},
    {"label": "Price Forecasts",     "href": "/forecasts", "icon": "bi-graph-up-arrow"},
    {"label": "Portfolio Optimiser", "href": "/portfolio", "icon": "bi-pie-chart-fill"},
    {"label": "Sentiment Analysis",  "href": "/sentiment", "icon": "bi-chat-quote-fill"},
]

sidebar = html.Aside([
    html.Div([html.Span("FIN", className="logo-accent"), html.Span("DASH")], className="sidebar-logo"),
    html.P("Phase 6 · Analytics", className="sidebar-subtitle"),
    html.Hr(className="sidebar-divider"),
    html.Nav([
        dcc.Link(
            html.Div([html.I(className=f"{i['icon']} me-2"), i["label"]], className="sidebar-link"),
            href=i["href"], className="nav-item-link",
        )
        for i in NAV_ITEMS
    ], className="sidebar-nav"),
    html.Div(className="sidebar-spacer"),
    html.Div([
        html.Div("● LIVE", className="live-badge"),
        html.P("API endpoints active", className="sidebar-footer-text"),
    ], className="sidebar-footer"),
], className="sidebar")

topbar = html.Header([
    html.Div(id="page-title", className="topbar-title"),
    html.Div([
        dcc.Interval(id="clock-interval", interval=1000, n_intervals=0),
        html.Span(id="live-clock", className="topbar-clock"),
        html.Span(" UTC", className="topbar-tz"),
    ], className="topbar-right"),
], className="topbar")

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    sidebar,
    html.Div([topbar, html.Main(dash.page_container, className="page-content")], className="main-wrapper"),
], className="app-shell")

@callback(Output("live-clock", "children"), Input("clock-interval", "n_intervals"))
def update_clock(_):
    return datetime.datetime.utcnow().strftime("%H:%M:%S")

@callback(Output("page-title", "children"), Input("url", "pathname"))
def update_title(path):
    return {
        "/overview": "Market Overview", "/anomalies": "Anomaly Detector",
        "/forecasts": "Price Forecasts", "/portfolio": "Portfolio Optimiser",
        "/sentiment": "Sentiment Analysis",
    }.get(path, "Dashboard")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8050)