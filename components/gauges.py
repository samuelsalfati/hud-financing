"""
Gauge chart components for HUD Financing Platform
"""
import plotly.graph_objects as go
from typing import Optional, Tuple
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from components.styles import (
    CYAN_PRIMARY, MINT_ACCENT, WARNING_ORANGE, ERROR_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, DARK_BG_SECONDARY,
    SUCCESS_GREEN,
)


def create_irr_gauge(
    irr: float,
    title: str = "Sponsor IRR",
    min_val: float = -0.10,
    max_val: float = 0.40,
    thresholds: Tuple[float, float, float] = (0.10, 0.15, 0.20),
) -> go.Figure:
    """
    Create IRR gauge chart

    Args:
        irr: IRR value (as decimal)
        title: Chart title
        min_val: Minimum gauge value
        max_val: Maximum gauge value
        thresholds: (warning, good, excellent) thresholds

    Returns:
        Plotly Figure
    """
    # Determine color based on IRR
    if irr >= thresholds[2]:
        bar_color = MINT_ACCENT
    elif irr >= thresholds[1]:
        bar_color = SUCCESS_GREEN
    elif irr >= thresholds[0]:
        bar_color = CYAN_PRIMARY
    elif irr >= 0:
        bar_color = WARNING_ORANGE
    else:
        bar_color = ERROR_RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=irr * 100,  # Convert to percentage
        number={
            "suffix": "%",
            "font": {"size": 36, "color": TEXT_PRIMARY},
            "valueformat": ".1f",
        },
        title={
            "text": title,
            "font": {"size": 16, "color": TEXT_SECONDARY}
        },
        gauge={
            "axis": {
                "range": [min_val * 100, max_val * 100],
                "tickwidth": 1,
                "tickcolor": TEXT_SECONDARY,
                "tickfont": {"color": TEXT_SECONDARY},
            },
            "bar": {"color": bar_color, "thickness": 0.75},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [min_val * 100, 0], "color": "rgba(239, 85, 59, 0.1)"},
                {"range": [0, thresholds[0] * 100], "color": "rgba(255, 161, 90, 0.1)"},
                {"range": [thresholds[0] * 100, thresholds[1] * 100], "color": "rgba(76, 201, 240, 0.1)"},
                {"range": [thresholds[1] * 100, thresholds[2] * 100], "color": "rgba(0, 204, 150, 0.1)"},
                {"range": [thresholds[2] * 100, max_val * 100], "color": "rgba(6, 255, 165, 0.1)"},
            ],
            "threshold": {
                "line": {"color": TEXT_PRIMARY, "width": 2},
                "thickness": 0.8,
                "value": irr * 100,
            },
        },
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT_SECONDARY},
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_dscr_gauge(
    dscr: float,
    title: str = "DSCR",
    min_val: float = 0.5,
    max_val: float = 2.0,
) -> go.Figure:
    """
    Create DSCR gauge chart

    Args:
        dscr: DSCR value
        title: Chart title
        min_val: Minimum gauge value
        max_val: Maximum gauge value

    Returns:
        Plotly Figure
    """
    # Determine color based on DSCR
    if dscr >= 1.40:
        bar_color = MINT_ACCENT
    elif dscr >= 1.25:
        bar_color = SUCCESS_GREEN
    elif dscr >= 1.10:
        bar_color = CYAN_PRIMARY
    elif dscr >= 1.0:
        bar_color = WARNING_ORANGE
    else:
        bar_color = ERROR_RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=dscr,
        number={
            "suffix": "x",
            "font": {"size": 36, "color": TEXT_PRIMARY},
            "valueformat": ".2f",
        },
        title={
            "text": title,
            "font": {"size": 16, "color": TEXT_SECONDARY}
        },
        gauge={
            "axis": {
                "range": [min_val, max_val],
                "tickwidth": 1,
                "tickcolor": TEXT_SECONDARY,
                "tickfont": {"color": TEXT_SECONDARY},
            },
            "bar": {"color": bar_color, "thickness": 0.75},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [min_val, 1.0], "color": "rgba(239, 85, 59, 0.15)"},
                {"range": [1.0, 1.10], "color": "rgba(255, 161, 90, 0.15)"},
                {"range": [1.10, 1.25], "color": "rgba(76, 201, 240, 0.15)"},
                {"range": [1.25, 1.40], "color": "rgba(0, 204, 150, 0.15)"},
                {"range": [1.40, max_val], "color": "rgba(6, 255, 165, 0.15)"},
            ],
            "threshold": {
                "line": {"color": WARNING_ORANGE, "width": 2},
                "thickness": 0.8,
                "value": 1.0,  # Breakeven threshold
            },
        },
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT_SECONDARY},
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_ltv_gauge(
    ltv: float,
    title: str = "Loan-to-Value",
    max_ltv: float = 0.90,
) -> go.Figure:
    """
    Create LTV gauge chart (lower is better)

    Args:
        ltv: LTV ratio (as decimal)
        title: Chart title
        max_ltv: Maximum LTV threshold

    Returns:
        Plotly Figure
    """
    # For LTV, lower is better
    if ltv <= 0.65:
        bar_color = MINT_ACCENT
    elif ltv <= 0.75:
        bar_color = SUCCESS_GREEN
    elif ltv <= 0.80:
        bar_color = CYAN_PRIMARY
    elif ltv <= 0.85:
        bar_color = WARNING_ORANGE
    else:
        bar_color = ERROR_RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=ltv * 100,
        number={
            "suffix": "%",
            "font": {"size": 36, "color": TEXT_PRIMARY},
            "valueformat": ".0f",
        },
        title={
            "text": title,
            "font": {"size": 16, "color": TEXT_SECONDARY}
        },
        gauge={
            "axis": {
                "range": [50, 95],
                "tickwidth": 1,
                "tickcolor": TEXT_SECONDARY,
                "tickfont": {"color": TEXT_SECONDARY},
            },
            "bar": {"color": bar_color, "thickness": 0.75},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [50, 65], "color": "rgba(6, 255, 165, 0.15)"},
                {"range": [65, 75], "color": "rgba(0, 204, 150, 0.15)"},
                {"range": [75, 80], "color": "rgba(76, 201, 240, 0.15)"},
                {"range": [80, 85], "color": "rgba(255, 161, 90, 0.15)"},
                {"range": [85, 95], "color": "rgba(239, 85, 59, 0.15)"},
            ],
        },
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT_SECONDARY},
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_probability_gauge(
    probability: float,
    title: str = "Loss Probability",
    invert_colors: bool = True,  # For loss prob, lower is better
) -> go.Figure:
    """
    Create probability gauge (0-100%)

    Args:
        probability: Probability value (0-1)
        title: Chart title
        invert_colors: If True, lower values are green

    Returns:
        Plotly Figure
    """
    pct = probability * 100

    if invert_colors:
        # Lower is better (e.g., loss probability)
        if pct <= 2:
            bar_color = MINT_ACCENT
        elif pct <= 5:
            bar_color = SUCCESS_GREEN
        elif pct <= 10:
            bar_color = CYAN_PRIMARY
        elif pct <= 20:
            bar_color = WARNING_ORANGE
        else:
            bar_color = ERROR_RED
    else:
        # Higher is better (e.g., success probability)
        if pct >= 95:
            bar_color = MINT_ACCENT
        elif pct >= 80:
            bar_color = SUCCESS_GREEN
        elif pct >= 60:
            bar_color = CYAN_PRIMARY
        elif pct >= 40:
            bar_color = WARNING_ORANGE
        else:
            bar_color = ERROR_RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pct,
        number={
            "suffix": "%",
            "font": {"size": 36, "color": TEXT_PRIMARY},
            "valueformat": ".1f",
        },
        title={
            "text": title,
            "font": {"size": 16, "color": TEXT_SECONDARY}
        },
        gauge={
            "axis": {
                "range": [0, 100],
                "tickwidth": 1,
                "tickcolor": TEXT_SECONDARY,
                "tickfont": {"color": TEXT_SECONDARY},
            },
            "bar": {"color": bar_color, "thickness": 0.75},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
        },
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT_SECONDARY},
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_moic_gauge(
    moic: float,
    title: str = "MOIC",
    min_val: float = 0.5,
    max_val: float = 2.5,
) -> go.Figure:
    """
    Create MOIC (Multiple on Invested Capital) gauge

    Args:
        moic: MOIC value
        title: Chart title
        min_val: Minimum gauge value
        max_val: Maximum gauge value

    Returns:
        Plotly Figure
    """
    if moic >= 1.5:
        bar_color = MINT_ACCENT
    elif moic >= 1.3:
        bar_color = SUCCESS_GREEN
    elif moic >= 1.1:
        bar_color = CYAN_PRIMARY
    elif moic >= 1.0:
        bar_color = WARNING_ORANGE
    else:
        bar_color = ERROR_RED

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=moic,
        number={
            "suffix": "x",
            "font": {"size": 36, "color": TEXT_PRIMARY},
            "valueformat": ".2f",
        },
        title={
            "text": title,
            "font": {"size": 16, "color": TEXT_SECONDARY}
        },
        gauge={
            "axis": {
                "range": [min_val, max_val],
                "tickwidth": 1,
                "tickcolor": TEXT_SECONDARY,
                "tickfont": {"color": TEXT_SECONDARY},
            },
            "bar": {"color": bar_color, "thickness": 0.75},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [min_val, 1.0], "color": "rgba(239, 85, 59, 0.1)"},
                {"range": [1.0, 1.1], "color": "rgba(255, 161, 90, 0.1)"},
                {"range": [1.1, 1.3], "color": "rgba(76, 201, 240, 0.1)"},
                {"range": [1.3, 1.5], "color": "rgba(0, 204, 150, 0.1)"},
                {"range": [1.5, max_val], "color": "rgba(6, 255, 165, 0.1)"},
            ],
            "threshold": {
                "line": {"color": WARNING_ORANGE, "width": 2},
                "thickness": 0.8,
                "value": 1.0,  # Breakeven
            },
        },
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT_SECONDARY},
        height=250,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_mini_gauge(
    value: float,
    label: str,
    format_str: str = "{:.1%}",
    color: str = None,
) -> go.Figure:
    """
    Create a compact mini gauge for dashboards

    Args:
        value: Value to display
        label: Label text
        format_str: Format string for value
        color: Override color

    Returns:
        Plotly Figure
    """
    if color is None:
        color = CYAN_PRIMARY

    fig = go.Figure(go.Indicator(
        mode="number",
        value=value * 100 if "%" in format_str else value,
        number={
            "suffix": "%" if "%" in format_str else "x" if "x" in format_str else "",
            "font": {"size": 28, "color": color},
            "valueformat": ".1f",
        },
        title={
            "text": label,
            "font": {"size": 12, "color": TEXT_SECONDARY}
        },
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=100,
        margin=dict(l=10, r=10, t=40, b=10),
    )

    return fig
