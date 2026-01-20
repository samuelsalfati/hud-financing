"""
Ascendra-styled CSS and color constants for HUD Financing Platform
"""

# =============================================================================
# COLOR PALETTE - Ascendra Theme
# =============================================================================

# Primary Colors
DARK_BG = "#0a1929"  # Deep navy background
DARK_BG_SECONDARY = "#1a2332"  # Lighter navy for cards
DARK_BG_GRADIENT_START = "#0a1929"
DARK_BG_GRADIENT_END = "#1a2332"

# Accent Colors
CYAN_PRIMARY = "#4cc9f0"  # Primary cyan
CYAN_LIGHT = "#7dd8f5"
CYAN_DARK = "#3ab8df"

MINT_ACCENT = "#06ffa5"  # Mint green accent
MINT_LIGHT = "#38ffb8"
MINT_DARK = "#00e090"

# Status Colors
SUCCESS_GREEN = "#06ffa5"
WARNING_ORANGE = "#ffa15a"
ERROR_RED = "#ef553b"
INFO_BLUE = "#4cc9f0"

# Chart Colors (Plotly-compatible)
CHART_COLORS = [
    "#4cc9f0",  # Cyan
    "#06ffa5",  # Mint
    "#ffa15a",  # Orange
    "#ef553b",  # Red
    "#ab63fa",  # Purple
    "#636efa",  # Blue
    "#00cc96",  # Teal
    "#fecb52",  # Yellow
]

# Tranche Colors
TRANCHE_COLORS = {
    "A": "#00cc96",  # Green - safest
    "B": "#ffa15a",  # Orange - middle
    "C": "#ef553b",  # Red - highest risk
    "sponsor": "#4cc9f0",  # Cyan - sponsor
}

# Text Colors
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#b0bec5"
TEXT_MUTED = "#78909c"

# =============================================================================
# CSS STYLES
# =============================================================================

def get_page_css() -> str:
    """Returns the main CSS for Ascendra-styled pages"""
    return f"""
    <style>
    /* ===== Global Styles ===== */
    .stApp {{
        background: linear-gradient(135deg, {DARK_BG_GRADIENT_START} 0%, {DARK_BG_GRADIENT_END} 100%);
    }}

    /* ===== Header Styles ===== */
    .main-header {{
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, {CYAN_PRIMARY}, {MINT_ACCENT});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }}

    .sub-header {{
        color: {TEXT_SECONDARY};
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }}

    /* ===== Card Styles ===== */
    .metric-card {{
        background: linear-gradient(145deg, {DARK_BG_SECONDARY}, rgba(26, 35, 50, 0.8));
        border: 1px solid rgba(76, 201, 240, 0.2);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }}

    .metric-card:hover {{
        border-color: rgba(76, 201, 240, 0.4);
        box-shadow: 0 6px 25px rgba(76, 201, 240, 0.1);
    }}

    .metric-value {{
        font-size: 2.2rem;
        font-weight: 700;
        color: {CYAN_PRIMARY};
        margin: 0;
    }}

    .metric-label {{
        font-size: 0.85rem;
        color: {TEXT_SECONDARY};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.3rem;
    }}

    .metric-delta {{
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }}

    .metric-delta.positive {{
        color: {SUCCESS_GREEN};
    }}

    .metric-delta.negative {{
        color: {ERROR_RED};
    }}

    /* ===== Status Indicators ===== */
    .status-badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
    }}

    .status-success {{
        background: rgba(6, 255, 165, 0.15);
        color: {SUCCESS_GREEN};
        border: 1px solid rgba(6, 255, 165, 0.3);
    }}

    .status-warning {{
        background: rgba(255, 161, 90, 0.15);
        color: {WARNING_ORANGE};
        border: 1px solid rgba(255, 161, 90, 0.3);
    }}

    .status-error {{
        background: rgba(239, 85, 59, 0.15);
        color: {ERROR_RED};
        border: 1px solid rgba(239, 85, 59, 0.3);
    }}

    /* ===== SOFR Indicator ===== */
    .sofr-indicator {{
        background: linear-gradient(145deg, {DARK_BG_SECONDARY}, rgba(26, 35, 50, 0.9));
        border: 1px solid rgba(76, 201, 240, 0.3);
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
    }}

    .sofr-value {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {CYAN_PRIMARY};
    }}

    .sofr-label {{
        font-size: 0.7rem;
        color: {TEXT_SECONDARY};
        text-transform: uppercase;
    }}

    .sofr-timestamp {{
        font-size: 0.65rem;
        color: {TEXT_MUTED};
    }}

    .live-dot {{
        display: inline-block;
        width: 8px;
        height: 8px;
        background: {SUCCESS_GREEN};
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 2s infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.5; }}
    }}

    /* ===== Section Dividers ===== */
    .section-divider {{
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(76, 201, 240, 0.3), transparent);
        margin: 2rem 0;
    }}

    /* ===== Table Styles ===== */
    .styled-table {{
        background: {DARK_BG_SECONDARY};
        border-radius: 8px;
        overflow: hidden;
    }}

    .styled-table th {{
        background: rgba(76, 201, 240, 0.1);
        color: {CYAN_PRIMARY};
        font-weight: 600;
        text-transform: uppercase;
        font-size: 0.75rem;
        letter-spacing: 0.05em;
    }}

    .styled-table td {{
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }}

    /* ===== Button Styles ===== */
    .stButton > button {{
        background: linear-gradient(135deg, {CYAN_PRIMARY}, {CYAN_DARK}) !important;
        color: {DARK_BG} !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.5rem !important;
        transition: all 0.3s ease !important;
    }}

    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(76, 201, 240, 0.4) !important;
    }}

    /* ===== Sidebar Styles ===== */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {DARK_BG} 0%, {DARK_BG_SECONDARY} 100%) !important;
        border-right: 1px solid rgba(76, 201, 240, 0.1);
    }}

    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stSlider label,
    section[data-testid="stSidebar"] .stNumberInput label {{
        color: {TEXT_SECONDARY} !important;
    }}

    /* ===== Tab Styles ===== */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background: transparent;
    }}

    .stTabs [data-baseweb="tab"] {{
        background: rgba(76, 201, 240, 0.1);
        border-radius: 8px 8px 0 0;
        border: 1px solid rgba(76, 201, 240, 0.2);
        border-bottom: none;
        color: {TEXT_SECONDARY};
    }}

    .stTabs [aria-selected="true"] {{
        background: rgba(76, 201, 240, 0.2) !important;
        color: {CYAN_PRIMARY} !important;
        border-color: rgba(76, 201, 240, 0.4) !important;
    }}

    /* ===== Expander Styles ===== */
    .streamlit-expanderHeader {{
        background: {DARK_BG_SECONDARY} !important;
        border: 1px solid rgba(76, 201, 240, 0.2) !important;
        border-radius: 8px !important;
    }}

    /* ===== Alert/Info Box Styles ===== */
    .stAlert {{
        background: rgba(76, 201, 240, 0.1) !important;
        border: 1px solid rgba(76, 201, 240, 0.3) !important;
        border-radius: 8px !important;
    }}

    /* ===== Logo Container ===== */
    .logo-container {{
        text-align: center;
        padding: 1rem 0;
        margin-bottom: 1rem;
    }}

    .logo-container img {{
        max-width: 180px;
        filter: drop-shadow(0 0 10px rgba(76, 201, 240, 0.3));
    }}

    /* ===== Gauge Container ===== */
    .gauge-container {{
        display: flex;
        justify-content: center;
        align-items: center;
    }}

    /* ===== Tooltip ===== */
    .tooltip {{
        position: relative;
        cursor: help;
    }}

    .tooltip::after {{
        content: attr(data-tooltip);
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background: {DARK_BG};
        color: {TEXT_PRIMARY};
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        font-size: 0.75rem;
        white-space: nowrap;
        opacity: 0;
        pointer-events: none;
        transition: opacity 0.2s;
        border: 1px solid rgba(76, 201, 240, 0.3);
    }}

    .tooltip:hover::after {{
        opacity: 1;
    }}

    /* ===== Hide Streamlit Branding ===== */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    </style>
    """


def get_plotly_theme() -> dict:
    """Returns Plotly layout defaults for Ascendra theme"""
    return {
        "template": "plotly_dark",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
            "color": TEXT_SECONDARY,
        },
        "title": {
            "font": {
                "color": TEXT_PRIMARY,
                "size": 16,
            }
        },
        "xaxis": {
            "gridcolor": "rgba(76, 201, 240, 0.1)",
            "linecolor": "rgba(76, 201, 240, 0.2)",
            "tickcolor": TEXT_MUTED,
        },
        "yaxis": {
            "gridcolor": "rgba(76, 201, 240, 0.1)",
            "linecolor": "rgba(76, 201, 240, 0.2)",
            "tickcolor": TEXT_MUTED,
        },
        "colorway": CHART_COLORS,
    }


def apply_plotly_theme(fig):
    """Apply Ascendra theme to a Plotly figure"""
    theme = get_plotly_theme()
    fig.update_layout(**theme)
    return fig


def metric_card(label: str, value: str, delta: str = None, delta_positive: bool = True) -> str:
    """Generate HTML for a metric card"""
    delta_html = ""
    if delta:
        delta_class = "positive" if delta_positive else "negative"
        delta_symbol = "+" if delta_positive else ""
        delta_html = f'<div class="metric-delta {delta_class}">{delta_symbol}{delta}</div>'

    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value">{value}</div>
        {delta_html}
    </div>
    """


def status_badge(text: str, status: str = "success") -> str:
    """Generate HTML for a status badge"""
    return f'<span class="status-badge status-{status}">{text}</span>'


def section_divider() -> str:
    """Generate HTML for a section divider"""
    return '<div class="section-divider"></div>'


# =============================================================================
# PAGE HEADER COMPONENT
# =============================================================================

def page_header(title: str, subtitle: str = None) -> str:
    """Generate HTML for a page header"""
    subtitle_html = f'<p class="sub-header">{subtitle}</p>' if subtitle else ""
    return f"""
    <h1 class="main-header">{title}</h1>
    {subtitle_html}
    """
