"""
Plotly chart wrappers with Ascendra styling for HUD Financing Platform
"""
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import List, Dict, Optional, Any
import numpy as np
import pandas as pd
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from components.styles import (
    CYAN_PRIMARY, MINT_ACCENT, WARNING_ORANGE, ERROR_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    CHART_COLORS, TRANCHE_COLORS, get_plotly_theme,
)


def apply_ascendra_theme(fig: go.Figure) -> go.Figure:
    """Apply Ascendra theme to any Plotly figure"""
    fig.update_layout(**get_plotly_theme())
    return fig


def create_line_chart(
    x: List,
    y: List,
    name: str = "",
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    color: str = None,
    fill: bool = False,
) -> go.Figure:
    """Create styled line chart"""
    if color is None:
        color = CYAN_PRIMARY

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x,
        y=y,
        name=name,
        mode="lines",
        line={"color": color, "width": 2},
        fill="tozeroy" if fill else None,
        fillcolor=f"rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)" if fill else None,
    ))

    fig.update_layout(
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        xaxis_title=x_title,
        yaxis_title=y_title,
        margin=dict(b=100),
    )

    return apply_ascendra_theme(fig)


def create_multi_line_chart(
    data: Dict[str, Dict],  # {series_name: {"x": [], "y": [], "color": str}}
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    height: int = 400,
) -> go.Figure:
    """Create multi-line chart with multiple series"""
    fig = go.Figure()

    for i, (name, series) in enumerate(data.items()):
        color = series.get("color", CHART_COLORS[i % len(CHART_COLORS)])
        fig.add_trace(go.Scatter(
            x=series["x"],
            y=series["y"],
            name=name,
            mode="lines+markers",
            line={"color": color, "width": 2},
            marker={"size": 4},
        ))

    fig.update_layout(
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=height,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
        },
        margin=dict(b=100),
    )

    return apply_ascendra_theme(fig)


def create_bar_chart(
    x: List,
    y: List,
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    color: str = None,
    horizontal: bool = False,
) -> go.Figure:
    """Create styled bar chart"""
    if color is None:
        color = CYAN_PRIMARY

    if horizontal:
        fig = go.Figure(go.Bar(y=x, x=y, orientation='h', marker_color=color))
    else:
        fig = go.Figure(go.Bar(x=x, y=y, marker_color=color))

    fig.update_layout(
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        xaxis_title=x_title,
        yaxis_title=y_title,
    )

    return apply_ascendra_theme(fig)


def create_grouped_bar_chart(
    categories: List[str],
    groups: Dict[str, List[float]],
    title: str = "",
    y_title: str = "",
    colors: List[str] = None,
    height: int = 400,
) -> go.Figure:
    """Create grouped bar chart"""
    if colors is None:
        colors = CHART_COLORS

    fig = go.Figure()

    for i, (group_name, values) in enumerate(groups.items()):
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            name=group_name,
            marker_color=colors[i % len(colors)],
        ))

    fig.update_layout(
        barmode='group',
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        yaxis_title=y_title,
        height=height,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
        },
        margin=dict(b=100),
    )

    return apply_ascendra_theme(fig)


def create_stacked_bar_chart(
    categories: List[str],
    stacks: Dict[str, List[float]],
    title: str = "",
    y_title: str = "",
    colors: List[str] = None,
    height: int = 400,
) -> go.Figure:
    """Create stacked bar chart"""
    if colors is None:
        colors = CHART_COLORS

    fig = go.Figure()

    for i, (stack_name, values) in enumerate(stacks.items()):
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            name=stack_name,
            marker_color=colors[i % len(colors)],
        ))

    fig.update_layout(
        barmode='stack',
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        yaxis_title=y_title,
        height=height,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
        },
        margin=dict(b=100),
    )

    return apply_ascendra_theme(fig)


def create_area_chart(
    x: List,
    y_dict: Dict[str, List[float]],
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    stacked: bool = True,
    height: int = 400,
) -> go.Figure:
    """Create stacked or overlapping area chart"""
    fig = go.Figure()

    for i, (name, y) in enumerate(y_dict.items()):
        color = CHART_COLORS[i % len(CHART_COLORS)]
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            name=name,
            mode="lines",
            line={"color": color, "width": 1},
            fill="tonexty" if stacked and i > 0 else "tozeroy",
            stackgroup="one" if stacked else None,
        ))

    fig.update_layout(
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=height,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.25,
            "xanchor": "center",
            "x": 0.5,
        },
        margin=dict(b=120),
    )

    return apply_ascendra_theme(fig)


def create_histogram(
    values: List[float],
    title: str = "",
    x_title: str = "",
    bins: int = 50,
    show_mean: bool = True,
    show_percentiles: bool = True,
    height: int = 400,
) -> go.Figure:
    """Create histogram with optional statistics overlays"""
    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=values,
        nbinsx=bins,
        marker_color=CYAN_PRIMARY,
        opacity=0.7,
    ))

    # Add mean line
    if show_mean:
        mean_val = np.mean(values)
        fig.add_vline(
            x=mean_val,
            line_dash="dash",
            line_color=MINT_ACCENT,
            annotation_text=f"Mean: {mean_val:.2%}",
            annotation_position="top",
        )

    # Add percentile lines
    if show_percentiles:
        p5 = np.percentile(values, 5)
        p95 = np.percentile(values, 95)
        fig.add_vline(x=p5, line_dash="dot", line_color=WARNING_ORANGE)
        fig.add_vline(x=p95, line_dash="dot", line_color=WARNING_ORANGE)

    fig.update_layout(
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        xaxis_title=x_title,
        yaxis_title="Frequency",
        height=height,
        bargap=0.05,
    )

    return apply_ascendra_theme(fig)


def create_heatmap(
    z: List[List[float]],
    x_labels: List[str],
    y_labels: List[str],
    title: str = "",
    color_scale: str = "RdYlGn",
    height: int = 400,
    format_func: callable = None,
) -> go.Figure:
    """Create heatmap for sensitivity tables"""
    if format_func is None:
        format_func = lambda x: f"{x:.1%}"

    # Create text annotations
    text = [[format_func(val) for val in row] for row in z]

    # Calculate min/max for proper color scaling
    flat_z = [val for row in z for val in row]
    z_min = min(flat_z) if flat_z else 0
    z_max = max(flat_z) if flat_z else 1

    # Add some padding if values are very close
    if z_max - z_min < 0.01:  # Less than 1% spread
        z_min = z_min - 0.05
        z_max = z_max + 0.05

    fig = go.Figure(go.Heatmap(
        z=z,
        x=x_labels,
        y=y_labels,
        text=text,
        texttemplate="%{text}",
        textfont={"size": 12, "color": "#ffffff"},
        colorscale=color_scale,
        showscale=True,
        zmin=z_min,
        zmax=z_max,
        colorbar={
            "tickfont": {"color": TEXT_SECONDARY},
            "tickformat": ".0%",
        },
    ))

    fig.update_layout(
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        height=height,
        xaxis={"side": "top"},
    )

    return apply_ascendra_theme(fig)


def create_fan_chart(
    x: List,
    percentile_data: Dict[str, List[float]],
    title: str = "",
    x_title: str = "",
    y_title: str = "",
    height: int = 400,
) -> go.Figure:
    """Create fan chart for uncertainty visualization"""
    fig = go.Figure()

    # Add bands from outer to inner
    if "p5" in percentile_data and "p95" in percentile_data:
        fig.add_trace(go.Scatter(
            x=x + x[::-1],
            y=percentile_data["p95"] + percentile_data["p5"][::-1],
            fill="toself",
            fillcolor=f"rgba(76, 201, 240, 0.1)",
            line={"width": 0},
            name="90% CI",
            showlegend=True,
        ))

    if "p25" in percentile_data and "p75" in percentile_data:
        fig.add_trace(go.Scatter(
            x=x + x[::-1],
            y=percentile_data["p75"] + percentile_data["p25"][::-1],
            fill="toself",
            fillcolor=f"rgba(76, 201, 240, 0.2)",
            line={"width": 0},
            name="50% CI",
            showlegend=True,
        ))

    # Add median line
    if "p50" in percentile_data:
        fig.add_trace(go.Scatter(
            x=x,
            y=percentile_data["p50"],
            mode="lines",
            line={"color": CYAN_PRIMARY, "width": 2},
            name="Median",
        ))

    fig.update_layout(
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        xaxis_title=x_title,
        yaxis_title=y_title,
        height=height,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.2,
            "xanchor": "center",
            "x": 0.5,
        },
        margin=dict(b=100),
    )

    return apply_ascendra_theme(fig)


def create_tornado_chart(
    parameters: List[str],
    low_impacts: List[float],
    high_impacts: List[float],
    base_value: float,
    title: str = "Sensitivity Analysis",
    height: int = 400,
) -> go.Figure:
    """Create tornado chart for sensitivity analysis"""
    # Sort by total impact
    total_impacts = [abs(h - l) for l, h in zip(low_impacts, high_impacts)]
    sorted_indices = np.argsort(total_impacts)[::-1]

    sorted_params = [parameters[i] for i in sorted_indices]
    sorted_low = [low_impacts[i] - base_value for i in sorted_indices]
    sorted_high = [high_impacts[i] - base_value for i in sorted_indices]

    fig = go.Figure()

    # Low side (negative impact)
    fig.add_trace(go.Bar(
        y=sorted_params,
        x=sorted_low,
        orientation='h',
        name='Low Scenario',
        marker_color=ERROR_RED,
    ))

    # High side (positive impact)
    fig.add_trace(go.Bar(
        y=sorted_params,
        x=sorted_high,
        orientation='h',
        name='High Scenario',
        marker_color=SUCCESS_GREEN,
    ))

    fig.update_layout(
        barmode='overlay',
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        xaxis_title="IRR Impact",
        height=height,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.15,
            "xanchor": "center",
            "x": 0.5,
        },
        margin=dict(b=80),
    )

    # Add base line
    fig.add_vline(x=0, line_color=TEXT_SECONDARY, line_width=1)

    return apply_ascendra_theme(fig)


def create_cashflow_chart(
    months: List[int],
    principal: List[float],
    interest: List[float],
    fees: List[float],
    title: str = "Monthly Cashflows",
    height: int = 400,
) -> go.Figure:
    """Create cashflow bar chart with net line"""
    fig = go.Figure()

    # Stacked bars
    fig.add_trace(go.Bar(
        x=months, y=principal, name="Principal", marker_color=CYAN_PRIMARY
    ))
    fig.add_trace(go.Bar(
        x=months, y=interest, name="Interest", marker_color=MINT_ACCENT
    ))
    fig.add_trace(go.Bar(
        x=months, y=fees, name="Fees", marker_color=WARNING_ORANGE
    ))

    # Net line
    net = [p + i + f for p, i, f in zip(principal, interest, fees)]
    fig.add_trace(go.Scatter(
        x=months, y=net, name="Net CF",
        mode="lines+markers",
        line={"color": TEXT_PRIMARY, "width": 2},
        marker={"size": 4},
    ))

    fig.update_layout(
        barmode='relative',
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        xaxis_title="Month",
        yaxis_title="Cashflow ($)",
        yaxis_tickformat="$,.0f",
        height=height,
        legend={
            "orientation": "h",
            "yanchor": "top",
            "y": -0.25,
            "xanchor": "center",
            "x": 0.5,
        },
        margin=dict(b=120),
    )

    return apply_ascendra_theme(fig)


def create_comparison_bar(
    items: List[str],
    values: List[float],
    title: str = "",
    value_format: str = "{:.1%}",
    color_by_value: bool = True,
    height: int = 300,
) -> go.Figure:
    """Create horizontal comparison bar chart"""
    # Determine colors
    if color_by_value:
        colors = []
        for v in values:
            if v >= 0.20:
                colors.append(MINT_ACCENT)
            elif v >= 0.15:
                colors.append(SUCCESS_GREEN)
            elif v >= 0.10:
                colors.append(CYAN_PRIMARY)
            elif v >= 0:
                colors.append(WARNING_ORANGE)
            else:
                colors.append(ERROR_RED)
    else:
        colors = [CYAN_PRIMARY] * len(values)

    fig = go.Figure(go.Bar(
        y=items,
        x=values,
        orientation='h',
        marker_color=colors,
        text=[value_format.format(v) for v in values],
        textposition="outside",
        textfont={"color": TEXT_PRIMARY},
    ))

    fig.update_layout(
        title={"text": title, "font": {"color": TEXT_PRIMARY}},
        height=height,
        margin=dict(l=150, r=60),
    )

    return apply_ascendra_theme(fig)
