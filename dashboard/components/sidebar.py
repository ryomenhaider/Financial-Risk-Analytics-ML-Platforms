import dash
import dash_bootstrap_components as dbc
from dash import html

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "background-color": "#1a1a2e",  # dark navy
    "overflow-y": "auto"
}

CONTENT_STYLE = {
    "margin-left": "17rem",
    "padding": "2rem 1rem"
}

sidebar = html.Div(
    [
        html.H4("FIP", className="text-white mb-4"),
        html.Hr(style={"border-color": "#444"}),
        dbc.Nav(
            [
                dbc.NavLink("Overview",   href="/",          active="exact"),
                dbc.NavLink("Prices",     href="/prices",    active="exact"),
                dbc.NavLink("Forecasts",  href="/forecasts", active="exact"),
                dbc.NavLink("Anomalies",  href="/anomalies", active="exact"),
                dbc.NavLink("Sentiment",  href="/sentiment", active="exact"),
            ],
            vertical=True,
            pills=True,
        ),
    ],
    style=SIDEBAR_STYLE
)