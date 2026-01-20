"""
Waterfall chart components for HUD Financing Platform
"""
import plotly.graph_objects as go
from typing import List, Dict, Optional
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from components.styles import (
    CYAN_PRIMARY, MINT_ACCENT, WARNING_ORANGE, ERROR_RED,
    TEXT_PRIMARY, TEXT_SECONDARY, TRANCHE_COLORS,
    SUCCESS_GREEN,
)


def create_capital_stack_waterfall(
    property_value: float,
    loan_amount: float,
    a_amount: float,
    b_amount: float,
    c_amount: float,
    title: str = "Capital Stack Waterfall",
) -> go.Figure:
    """
    Create capital stack waterfall chart

    Args:
        property_value: Total property value
        loan_amount: Total loan amount
        a_amount: A-piece amount
        b_amount: B-piece amount
        c_amount: C-piece amount
        title: Chart title

    Returns:
        Plotly Figure
    """
    equity_cushion = property_value - loan_amount

    fig = go.Figure(go.Waterfall(
        name="Capital Stack",
        orientation="v",
        x=["Property Value", "Equity Cushion", "Loan Amount", "A-Piece", "B-Piece", "C-Piece"],
        y=[
            property_value,
            -equity_cushion,
            0,  # Total
            -a_amount,
            -b_amount,
            -c_amount,
        ],
        measure=["absolute", "relative", "total", "relative", "relative", "relative"],
        text=[
            f"${property_value/1e6:.1f}M",
            f"-${equity_cushion/1e6:.1f}M",
            f"${loan_amount/1e6:.1f}M",
            f"${a_amount/1e6:.1f}M",
            f"${b_amount/1e6:.1f}M",
            f"${c_amount/1e6:.1f}M",
        ],
        textposition="outside",
        textfont={"color": TEXT_PRIMARY, "size": 11},
        connector={"line": {"color": "rgba(76, 201, 240, 0.3)", "width": 1}},
        decreasing={"marker": {"color": ERROR_RED}},
        increasing={"marker": {"color": SUCCESS_GREEN}},
        totals={"marker": {"color": CYAN_PRIMARY}},
    ))

    fig.update_layout(
        title={
            "text": title,
            "font": {"color": TEXT_PRIMARY, "size": 16},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT_SECONDARY},
        height=400,
        showlegend=False,
        yaxis={
            "tickformat": "$,.0f",
            "gridcolor": "rgba(76, 201, 240, 0.1)",
            "zerolinecolor": "rgba(76, 201, 240, 0.3)",
        },
        xaxis={
            "tickfont": {"size": 10},
        },
        margin=dict(l=60, r=20, t=50, b=40),
    )

    return fig


def create_stacked_capital_bar(
    a_amount: float,
    b_amount: float,
    c_amount: float,
    title: str = "Tranche Structure",
) -> go.Figure:
    """
    Create stacked horizontal bar for capital stack

    Args:
        a_amount: A-piece amount
        b_amount: B-piece amount
        c_amount: C-piece amount
        title: Chart title

    Returns:
        Plotly Figure
    """
    total = a_amount + b_amount + c_amount

    fig = go.Figure()

    # C-Piece (bottom - highest risk)
    fig.add_trace(go.Bar(
        x=[c_amount],
        y=["Capital Stack"],
        orientation='h',
        name=f"C-Piece (Sponsor) - ${c_amount/1e6:.1f}M ({c_amount/total:.0%})",
        marker_color=TRANCHE_COLORS["C"],
        text=[f"C: {c_amount/total:.0%}"],
        textposition="inside",
        textfont={"color": "white", "size": 11},
    ))

    # B-Piece (middle)
    fig.add_trace(go.Bar(
        x=[b_amount],
        y=["Capital Stack"],
        orientation='h',
        name=f"B-Piece (Mezz) - ${b_amount/1e6:.1f}M ({b_amount/total:.0%})",
        marker_color=TRANCHE_COLORS["B"],
        text=[f"B: {b_amount/total:.0%}"],
        textposition="inside",
        textfont={"color": "white", "size": 11},
    ))

    # A-Piece (top - safest)
    fig.add_trace(go.Bar(
        x=[a_amount],
        y=["Capital Stack"],
        orientation='h',
        name=f"A-Piece (Senior) - ${a_amount/1e6:.1f}M ({a_amount/total:.0%})",
        marker_color=TRANCHE_COLORS["A"],
        text=[f"A: {a_amount/total:.0%}"],
        textposition="inside",
        textfont={"color": "white", "size": 11},
    ))

    fig.update_layout(
        barmode='stack',
        title={
            "text": title,
            "font": {"color": TEXT_PRIMARY, "size": 16},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT_SECONDARY},
        height=200,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.4,
            "xanchor": "center",
            "x": 0.5,
        },
        xaxis={
            "tickformat": "$,.0f",
            "gridcolor": "rgba(76, 201, 240, 0.1)",
        },
        yaxis={"visible": False},
        margin=dict(l=20, r=20, t=50, b=80),
    )

    return fig


def create_loss_waterfall(
    allocations: List[Dict],
    total_loss: float,
    total_recovery: float,
    title: str = "Loss Waterfall",
) -> go.Figure:
    """
    Create loss allocation waterfall chart

    Args:
        allocations: List of {"name": str, "amount": float, "loss": float, "recovery": float}
        total_loss: Total loss amount
        total_recovery: Total recovery amount
        title: Chart title

    Returns:
        Plotly Figure
    """
    x_labels = ["Total Claim"]
    y_values = [total_loss + total_recovery]
    measures = ["absolute"]
    colors = [CYAN_PRIMARY]

    # Add recovery
    x_labels.append("Recovery")
    y_values.append(total_recovery)
    measures.append("relative")
    colors.append(SUCCESS_GREEN)

    # Add losses by tranche (from junior to senior)
    for alloc in allocations:
        x_labels.append(f"{alloc['name']} Loss")
        y_values.append(-alloc['loss'])
        measures.append("relative")
        colors.append(ERROR_RED if alloc['loss'] > 0 else "rgba(128,128,128,0.3)")

    # Final
    x_labels.append("Remaining")
    y_values.append(0)
    measures.append("total")
    colors.append(TEXT_MUTED if total_recovery <= 0 else MINT_ACCENT)

    fig = go.Figure(go.Waterfall(
        name="Loss Allocation",
        orientation="v",
        x=x_labels,
        y=y_values,
        measure=measures,
        connector={"line": {"color": "rgba(76, 201, 240, 0.3)", "width": 1}},
        decreasing={"marker": {"color": ERROR_RED}},
        increasing={"marker": {"color": SUCCESS_GREEN}},
        totals={"marker": {"color": CYAN_PRIMARY}},
        textposition="outside",
        textfont={"color": TEXT_PRIMARY, "size": 10},
    ))

    fig.update_layout(
        title={
            "text": title,
            "font": {"color": TEXT_PRIMARY, "size": 16},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT_SECONDARY},
        height=400,
        showlegend=False,
        yaxis={
            "tickformat": "$,.0f",
            "gridcolor": "rgba(76, 201, 240, 0.1)",
        },
        xaxis={
            "tickangle": -45,
            "tickfont": {"size": 9},
        },
        margin=dict(l=60, r=20, t=50, b=80),
    )

    return fig


def create_tranche_loss_bar(
    allocations: List[Dict],
    title: str = "Tranche Impact",
) -> go.Figure:
    """
    Create horizontal bar showing loss impact by tranche

    Args:
        allocations: List of {"name": str, "amount": float, "loss": float, "loss_pct": float}
        title: Chart title

    Returns:
        Plotly Figure
    """
    names = [a["name"] for a in allocations]
    loss_pcts = [a["loss_pct"] * 100 for a in allocations]
    recovery_pcts = [100 - (a["loss_pct"] * 100) for a in allocations]

    # Colors based on loss severity
    loss_colors = []
    for a in allocations:
        if a["loss_pct"] >= 0.99:
            loss_colors.append(ERROR_RED)
        elif a["loss_pct"] > 0:
            loss_colors.append(WARNING_ORANGE)
        else:
            loss_colors.append("rgba(128,128,128,0.2)")

    fig = go.Figure()

    # Recovery portion
    fig.add_trace(go.Bar(
        y=names,
        x=recovery_pcts,
        orientation='h',
        name='Recovery',
        marker_color=SUCCESS_GREEN,
        text=[f"{r:.0f}%" for r in recovery_pcts],
        textposition="inside",
    ))

    # Loss portion
    fig.add_trace(go.Bar(
        y=names,
        x=loss_pcts,
        orientation='h',
        name='Loss',
        marker_color=loss_colors,
        text=[f"{l:.0f}%" if l > 5 else "" for l in loss_pcts],
        textposition="inside",
    ))

    fig.update_layout(
        barmode='stack',
        title={
            "text": title,
            "font": {"color": TEXT_PRIMARY, "size": 16},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT_SECONDARY},
        height=250,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": -0.3,
            "xanchor": "center",
            "x": 0.5,
        },
        xaxis={
            "title": "Percentage",
            "range": [0, 100],
            "gridcolor": "rgba(76, 201, 240, 0.1)",
        },
        margin=dict(l=120, r=20, t=50, b=60),
    )

    return fig


def create_fee_breakdown_waterfall(
    origination_fee: float,
    exit_fee: float,
    extension_fees: float = 0,
    spread_income: float = 0,
    c_interest: float = 0,
    title: str = "Sponsor Returns Breakdown",
) -> go.Figure:
    """
    Create waterfall showing sponsor return components

    Args:
        origination_fee: Origination fee income
        exit_fee: Exit fee income
        extension_fees: Extension fee income
        spread_income: Total spread income
        c_interest: C-piece interest income
        title: Chart title

    Returns:
        Plotly Figure
    """
    x_labels = []
    y_values = []
    measures = []

    # Build waterfall
    if origination_fee > 0:
        x_labels.append("Origination Fee")
        y_values.append(origination_fee)
        measures.append("relative")

    if spread_income > 0:
        x_labels.append("Spread Income")
        y_values.append(spread_income)
        measures.append("relative")

    if c_interest > 0:
        x_labels.append("C-Piece Interest")
        y_values.append(c_interest)
        measures.append("relative")

    if exit_fee > 0:
        x_labels.append("Exit Fee")
        y_values.append(exit_fee)
        measures.append("relative")

    if extension_fees > 0:
        x_labels.append("Extension Fees")
        y_values.append(extension_fees)
        measures.append("relative")

    # Total
    x_labels.append("Total Returns")
    y_values.append(0)
    measures.append("total")

    fig = go.Figure(go.Waterfall(
        name="Returns",
        orientation="v",
        x=x_labels,
        y=y_values,
        measure=measures,
        connector={"line": {"color": "rgba(6, 255, 165, 0.3)", "width": 1}},
        increasing={"marker": {"color": MINT_ACCENT}},
        totals={"marker": {"color": CYAN_PRIMARY}},
        textposition="outside",
        text=[f"${v:,.0f}" for v in y_values[:-1]] + [f"${sum(y_values[:-1]):,.0f}"],
        textfont={"color": TEXT_PRIMARY, "size": 10},
    ))

    fig.update_layout(
        title={
            "text": title,
            "font": {"color": TEXT_PRIMARY, "size": 16},
        },
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT_SECONDARY},
        height=350,
        showlegend=False,
        yaxis={
            "tickformat": "$,.0f",
            "gridcolor": "rgba(76, 201, 240, 0.1)",
        },
        xaxis={
            "tickangle": -30,
            "tickfont": {"size": 10},
        },
        margin=dict(l=60, r=20, t=50, b=60),
    )

    return fig


# Need to import TEXT_MUTED
TEXT_MUTED = "#78909c"
