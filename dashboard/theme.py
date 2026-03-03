
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import os

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
API_KEY  = os.getenv("DASHBOARD_API_KEY", "changeme")
HEADERS  = {"X-API-Key": API_KEY}

COLORS = {
    "bg":       "#0A0E17", "card":    "#111827", "elevated": "#1C2333",
    "border":   "#1F2D45", "blue":    "#00D4FF", "green":    "#00FF94",
    "red":      "#FF4D6D", "amber":   "#FFB800", "purple":   "#A855F7",
    "text":     "#E8EDF5", "muted":   "#8B9AB3", "dim":      "#4A5568",
}

PLOT_BASE = dict(
    paper_bgcolor=COLORS["card"], plot_bgcolor=COLORS["bg"],
    font=dict(color=COLORS["text"], family="'IBM Plex Mono',monospace", size=11),
    xaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"],
               tickfont=dict(color=COLORS["muted"], size=10), zerolinecolor=COLORS["border"]),
    yaxis=dict(gridcolor=COLORS["border"], linecolor=COLORS["border"],
               tickfont=dict(color=COLORS["muted"], size=10), zerolinecolor=COLORS["border"]),
    margin=dict(l=55, r=20, t=40, b=45),
    legend=dict(bgcolor=COLORS["elevated"], bordercolor=COLORS["border"],
                font=dict(color=COLORS["muted"])),
    hoverlabel=dict(bgcolor=COLORS["elevated"], bordercolor=COLORS["blue"],
                    font=dict(color=COLORS["text"], family="'IBM Plex Mono',monospace")),
)