"""
Risk Analysis Page - Default scenarios and loss waterfall visualization
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from components.waterfalls import create_loss_waterfall, create_tranche_loss_bar
from components.gauges import create_probability_gauge, create_ltv_gauge
from components.charts import create_bar_chart, create_grouped_bar_chart
from engine.defaults import (
    get_standard_default_scenarios,
    run_loss_waterfall,
    analyze_multiple_scenarios,
    calculate_expected_loss,
    calculate_loss_probability_by_ltv,
    DefaultScenario,
)

# Page config
st.set_page_config(
    page_title="Risk Analysis | HUD Financing",
    page_icon="⚠️",
    layout="wide",
)

if not check_password():
    st.stop()

st.markdown(get_page_css(), unsafe_allow_html=True)

# Sidebar
sofr_data = render_sofr_indicator()
render_logo()

# Check if deal is configured
if 'deal_params' not in st.session_state:
    st.warning("⚠️ No deal configured. Please set up your deal in Executive Summary first.")
    st.page_link("pages/1_Executive_Summary.py", label="→ Go to Executive Summary")
    st.stop()

# Get deal params
p = st.session_state['deal_params']
deal = st.session_state.get('deal')
results = st.session_state.get('results')

# Header
st.markdown(page_header(
    "Risk Analysis",
    "Default scenarios and loss waterfall modeling"
), unsafe_allow_html=True)

# Deal Summary Bar
st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
<span style="color:#b0bec5;">Property: <strong style="color:#4cc9f0;">${p['property_value']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">Loan: <strong style="color:#4cc9f0;">${p['loan_amount']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">LTV: <strong style="color:#4cc9f0;">{p['ltv']:.0%}</strong></span>
<span style="color:#b0bec5;">Term: <strong style="color:#4cc9f0;">{p['term_months']}mo</strong></span>
<span style="color:#b0bec5;">SOFR: <strong style="color:#06ffa5;">{p['current_sofr']:.2%}</strong></span>
</div>""", unsafe_allow_html=True)

# Key Risk Metrics
st.subheader("Risk Overview")

col1, col2, col3, col4 = st.columns(4)

# Calculate risk metrics
ltv = p['ltv']
annual_pd = calculate_loss_probability_by_ltv(ltv)
term_years = p['hud_month'] / 12
expected_loss = calculate_expected_loss(
    p['loan_amount'],
    p['property_value'],
    ltv,
    term_years,
)

with col1:
    fig = create_ltv_gauge(ltv, "LTV Ratio")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    fig = create_probability_gauge(annual_pd, "Annual PD", invert_colors=True)
    st.plotly_chart(fig, use_container_width=True)

with col3:
    fig = create_probability_gauge(expected_loss["cumulative_pd"], "Cumulative PD", invert_colors=True)
    st.plotly_chart(fig, use_container_width=True)

with col4:
    fig = create_probability_gauge(expected_loss["expected_loss_pct"], "Expected Loss", invert_colors=True)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# Default Scenario Analysis
st.subheader("Default Scenario Analysis")

# Run all standard scenarios
scenarios = get_standard_default_scenarios(p['term_months'])
waterfall_results = analyze_multiple_scenarios(
    p['loan_amount'],
    p['property_value'],
    p['a_pct'],
    p['b_pct'],
    p['c_pct'],
    scenarios,
)

# Results table
results_data = []
for result in waterfall_results:
    results_data.append({
        "Scenario": result.scenario.name,
        "Default Month": result.scenario.default_month if result.scenario.default_month > 0 else "N/A",
        "Recovery Rate": f"{result.scenario.recovery_rate:.0%}",
        "Total Loss": f"${result.total_loss:,.0f}",
        "Senior Impaired": "Yes" if result.senior_impaired else "No",
        "Mezz Impaired": "Yes" if result.mezz_impaired else "No",
        "Sponsor Loss": f"{result.sponsor_loss_pct:.0%}",
    })

st.dataframe(results_data, use_container_width=True, hide_index=True)

# Loss comparison chart
fig = create_grouped_bar_chart(
    categories=[r.scenario.name for r in waterfall_results if r.scenario.default_month > 0],
    groups={
        "Total Loss": [r.total_loss / 1e6 for r in waterfall_results if r.scenario.default_month > 0],
    },
    title="Total Loss by Scenario ($M)",
    y_title="Loss ($M)",
    height=350,
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# Interactive Loss Waterfall
st.subheader("Interactive Loss Waterfall")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### Scenario Selection")

    selected_recovery = st.slider(
        "Recovery Rate",
        min_value=0.20,
        max_value=1.00,
        value=0.70,
        step=0.05,
        format="%.0f%%",
    )

    selected_month = st.slider(
        "Default Month",
        min_value=1,
        max_value=p['term_months'],
        value=12,
    )

    legal_costs = st.slider(
        "Legal/Workout Costs",
        min_value=0.02,
        max_value=0.15,
        value=0.05,
        step=0.01,
        format="%.0f%%",
    )

with col2:
    # Run custom scenario
    custom_scenario = DefaultScenario(
        name="Custom",
        default_month=selected_month,
        recovery_rate=selected_recovery,
        months_to_recovery=12,
        legal_costs_pct=legal_costs,
    )

    custom_result = run_loss_waterfall(
        p['loan_amount'],
        p['property_value'],
        p['a_pct'],
        p['b_pct'],
        p['c_pct'],
        custom_scenario,
        p['current_sofr'],
        p['borrower_spread'],
        accrued_months=selected_month,
    )

    # Display loss waterfall
    allocations = [
        {
            "name": a.tranche_name,
            "amount": a.tranche_amount,
            "loss": a.loss_amount,
            "loss_pct": a.loss_percentage,
        }
        for a in custom_result.allocations
    ]

    fig = create_loss_waterfall(
        allocations,
        custom_result.total_loss,
        custom_result.total_recovery,
        title="Loss Allocation Waterfall",
    )
    st.plotly_chart(fig, use_container_width=True)

# Tranche impact visualization
st.subheader("Tranche Impact Analysis")

fig = create_tranche_loss_bar(
    allocations,
    title="Recovery vs Loss by Tranche",
)
st.plotly_chart(fig, use_container_width=True)

# Detailed allocation table
st.markdown("### Detailed Loss Allocation")

alloc_data = []
for a in custom_result.allocations:
    alloc_data.append({
        "Tranche": a.tranche_name,
        "Principal": f"${a.tranche_amount:,.0f}",
        "Loss Amount": f"${a.loss_amount:,.0f}",
        "Recovery": f"${a.recovery_amount:,.0f}",
        "Loss %": f"{a.loss_percentage:.0%}",
        "Status": "Wiped Out" if a.is_wiped_out else "Impaired" if a.loss_amount > 0 else "Intact",
    })

st.dataframe(alloc_data, use_container_width=True, hide_index=True)

st.divider()

# Risk Summary
st.subheader("Risk Summary")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Loss Severity Analysis")

    # At what recovery rate does each tranche get impaired?
    c_amt = p['loan_amount'] * p['c_pct']
    b_amt = p['loan_amount'] * p['b_pct']
    a_amt = p['loan_amount'] * p['a_pct']

    # Recovery needed to protect each tranche
    protect_c = (p['loan_amount'] - c_amt) / p['property_value']
    protect_b = (p['loan_amount'] - c_amt - b_amt) / p['property_value']
    protect_a = (p['loan_amount'] - c_amt - b_amt - a_amt) / p['property_value']

    st.markdown(f"""
    | Tranche | Cushion | Protected at Recovery > |
    |---------|---------|-------------------------|
    | A-Piece | ${(c_amt + b_amt)/1e6:.1f}M ({p['b_pct'] + p['c_pct']:.0%}) | {max(0, protect_a):.0%} |
    | B-Piece | ${c_amt/1e6:.1f}M ({p['c_pct']:.0%}) | {max(0, protect_b):.0%} |
    | C-Piece | $0 (First Loss) | {max(0, protect_c):.0%} |
    """)

with col2:
    st.markdown("### Key Risk Indicators")

    # Risk status based on metrics
    if ltv <= 0.75 and annual_pd <= 0.02:
        risk_status = "LOW"
        risk_color = "#06ffa5"
    elif ltv <= 0.85 and annual_pd <= 0.04:
        risk_status = "MODERATE"
        risk_color = "#ffa15a"
    else:
        risk_status = "ELEVATED"
        risk_color = "#ef553b"

    st.markdown(f"""
    <div style="
        background: rgba({int(risk_color[1:3], 16)}, {int(risk_color[3:5], 16)}, {int(risk_color[5:7], 16)}, 0.15);
        border: 2px solid {risk_color};
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    ">
        <div style="font-size: 0.8rem; color: #b0bec5;">Overall Risk Level</div>
        <div style="font-size: 1.8rem; font-weight: 700; color: {risk_color};">{risk_status}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    **Key Metrics:**
    - LTV: **{ltv:.0%}** {'(Conservative)' if ltv <= 0.75 else '(Moderate)' if ltv <= 0.85 else '(Aggressive)'}
    - Annual PD: **{annual_pd:.2%}**
    - Expected Loss: **${expected_loss['expected_loss']:,.0f}**
    - C-Piece Cushion: **{p['c_pct']:.0%}** of loan
    """)

st.divider()
st.caption("HUD Financing Platform | Risk Analysis")
