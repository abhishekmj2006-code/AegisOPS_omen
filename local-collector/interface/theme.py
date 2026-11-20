"""Theme constants for AegisOPS Desktop UI — Grafana Observability Design System.
Provides signature Grafana dark styling, modular panel palettes, and high-contrast alert states.
"""

# Base Surfaces & Backgrounds (Grafana Charcoal & Slate Atmosphere)
BG_DEEP = "#111217"          # Primary dark canvas background
BG_SIDEBAR = "#141619"       # Nav sidebar background
BG_SURFACE = "#181b1f"       # Grafana panel surface
BG_CARD = "#22252b"          # Elevated panel / metric card surface
BG_INPUT = "#111217"         # Textbox, input fields, code viewers
BG_HOVER = "#2c3235"         # Element hover state

# Borders & Separators (Grafana clean 1px panel borders)
BORDER_SUBTLE = "#2c3235"    # Standard 1px panel border
BORDER_ACTIVE = "#3274D9"    # Grafana blue active border
BORDER_ACCENT = "#FF780A"    # Grafana orange accent border

# Text & Typography Hierarchy
TEXT_PRIMARY = "#F4F5F5"     # Crisp white for headings and values
TEXT_SECONDARY = "#D8D9DA"   # Body text & major labels
TEXT_MUTED = "#8E8E8E"       # Secondary descriptions & metadata
TEXT_FAINT = "#606266"       # Footers, timestamps, deactivated labels

# Status & Semantic Accents (Grafana Signature Palette)
ACCENT_PRIMARY = "#FF780A"   # Signature Grafana Orange
ACCENT_PRIMARY_HOVER = "#E06800"
ACCENT_BLUE = "#3274D9"      # Grafana Blue

STATUS_ONLINE_BG = "#18321d"
STATUS_ONLINE_FG = "#73BF69"  # Grafana Vibrant Green

STATUS_OFFLINE_BG = "#38171a"
STATUS_OFFLINE_FG = "#F2495C" # Grafana Alert Red

STATUS_WARN_BG = "#383115"
STATUS_WARN_FG = "#FADE2A"   # Grafana Alert Yellow

STATUS_INFO_BG = "#142847"
STATUS_INFO_FG = "#5794F2"   # Grafana Light Blue

# Metric Category Accents
METRIC_CPU = "#FF780A"       # Grafana Orange
METRIC_RAM = "#B877D9"       # Grafana Purple
METRIC_DISK = "#5794F2"      # Grafana Blue
METRIC_NET = "#73BF69"       # Grafana Green
