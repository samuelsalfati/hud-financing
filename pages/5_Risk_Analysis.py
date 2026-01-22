"""
Risk Analysis Page - Default scenarios and loss waterfall modeling
Redesigned with preset scenarios and number inputs (no sliders)
"""
import streamlit as st
import pandas as pd
import math
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


# Helper functions
def safe_pct(val, decimals=1):
    """Format percentage, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.{decimals}%}"


def safe_currency(val):
    """Format currency, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"${val:,.0f}"


# Check if deal is configured
if 'deal_params' not in st.session_state:
    st.warning("⚠️ No deal configured. Please set up your deal in Executive Summary first.")
    st.page_link("pages/1_Executive_Summary.py", label="→ Go to Executive Summary")
    st.stop()

# Get deal params
p = st.session_state['deal_params']
deal = st.session_state.get('deal')
results = st.session_state.get('results')
aggregator_summary = st.session_state.get('aggregator_summary')

# Header
st.markdown(page_header(
    "Risk Analysis",
    "Default scenarios and loss waterfall modeling"
), unsafe_allow_html=True)

# Deal Summary Bar
coinvest_pct = p.get('agg_coinvest', 0)
st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
<span style="color:#b0bec5;">Property: <strong style="color:#4cc9f0;">${p['property_value']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">Loan: <strong style="color:#4cc9f0;">${p['loan_amount']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">LTV: <strong style="color:#4cc9f0;">{p['ltv']:.0%}</strong></span>
<span style="color:#b0bec5;">A/B/C: <strong style="color:#4cc9f0;">{p['a_pct']:.0%}/{p['b_pct']:.0%}/{p['c_pct']:.0%}</strong></span>
<span style="color:#b0bec5;">Co-Invest: <strong style="color:#06ffa5;">{coinvest_pct:.0%}</strong></span>
</div>""", unsafe_allow_html=True)

# =============================================================================
# SECTION 1: PROTECTION ANALYSIS
# =============================================================================
st.markdown("### Capital Stack Protection")

# Calculate protection levels
c_amt = p['loan_amount'] * p['c_pct']
b_amt = p['loan_amount'] * p['b_pct']
a_amt = p['loan_amount'] * p['a_pct']
agg_exposure = c_amt * coinvest_pct

# What property value decline wipes each tranche?
# Loss = Property Value * (1 - Recovery) - but we need to think about it differently
# If property sells for X, loan balance is L, loss = max(0, L - X)
# C is wiped when X < A + B amounts
# B is impaired when X < A amount

protect_c_value = a_amt + b_amt  # Property must sell for this to protect C fully
protect_b_value = a_amt  # Property must sell for this to protect B fully

protect_c_decline = 1 - (protect_c_value / p['property_value'])  # Max decline before C loss
protect_b_decline = 1 - (protect_b_value / p['property_value'])  # Max decline before B loss

st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:1rem; margin-bottom:1rem;">
<strong style="color:#4cc9f0;">How to Read This</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
Each tranche has a "cushion" of junior capital below it. The A-Piece is protected until losses exceed B+C combined.
Property value must decline significantly before senior tranches take losses.
</div>
</div>""", unsafe_allow_html=True)

# Protection table
prot_col1, prot_col2, prot_col3, prot_col4 = st.columns(4)

with prot_col1:
    st.markdown(f"""<div style="background:rgba(76,201,240,0.15); border-radius:8px; padding:1rem; text-align:center; height:140px;">
<div style="color:#4cc9f0; font-weight:600; font-size:0.9rem;">A-Piece (Bank)</div>
<div style="color:#e0e0e0; font-size:1.6rem; font-weight:700; margin:0.5rem 0;">${a_amt/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.75rem;">Cushion: ${(b_amt+c_amt)/1e6:.1f}M ({p['b_pct']+p['c_pct']:.0%})</div>
<div style="color:#06ffa5; font-size:0.8rem; margin-top:0.3rem;">Protected up to {protect_b_decline:.0%} decline</div>
</div>""", unsafe_allow_html=True)

with prot_col2:
    st.markdown(f"""<div style="background:rgba(255,161,90,0.15); border-radius:8px; padding:1rem; text-align:center; height:140px;">
<div style="color:#ffa15a; font-weight:600; font-size:0.9rem;">B-Fund (Mezz)</div>
<div style="color:#e0e0e0; font-size:1.6rem; font-weight:700; margin:0.5rem 0;">${b_amt/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.75rem;">Cushion: ${c_amt/1e6:.1f}M ({p['c_pct']:.0%})</div>
<div style="color:#ffa15a; font-size:0.8rem; margin-top:0.3rem;">Protected up to {protect_c_decline:.0%} decline</div>
</div>""", unsafe_allow_html=True)

with prot_col3:
    st.markdown(f"""<div style="background:rgba(239,85,59,0.15); border-radius:8px; padding:1rem; text-align:center; height:140px;">
<div style="color:#ef553b; font-weight:600; font-size:0.9rem;">C-Fund (First Loss)</div>
<div style="color:#e0e0e0; font-size:1.6rem; font-weight:700; margin:0.5rem 0;">${c_amt/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.75rem;">Cushion: None (equity)</div>
<div style="color:#ef553b; font-size:0.8rem; margin-top:0.3rem;">First loss position</div>
</div>""", unsafe_allow_html=True)

with prot_col4:
    st.markdown(f"""<div style="background:rgba(6,255,165,0.15); border-radius:8px; padding:1rem; text-align:center; height:140px;">
<div style="color:#06ffa5; font-weight:600; font-size:0.9rem;">Aggregator Co-Invest</div>
<div style="color:#e0e0e0; font-size:1.6rem; font-weight:700; margin:0.5rem 0;">${agg_exposure/1e6:.2f}M</div>
<div style="color:#78909c; font-size:0.75rem;">{coinvest_pct:.0%} of C-Piece</div>
<div style="color:#ef553b; font-size:0.8rem; margin-top:0.3rem;">Pro-rata with C-Fund LPs</div>
</div>""", unsafe_allow_html=True)

st.divider()

# =============================================================================
# SECTION 2: PRESET DEFAULT SCENARIOS
# =============================================================================
st.markdown("### Default Scenario Comparison")

st.markdown("""<div style="background:rgba(239,85,59,0.1); border:1px solid rgba(239,85,59,0.2); border-radius:8px; padding:1rem; margin-bottom:1rem;">
<strong style="color:#ef553b;">What Happens in Default?</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
When a borrower defaults, the property is sold (or taken back) at a <strong>recovery rate</strong> — the sale price as % of original property value.
Losses flow through the capital stack from C → B → A (junior to senior). Below are standard stress scenarios.
</div>
</div>""", unsafe_allow_html=True)

# Define preset scenarios with clear descriptions
preset_scenarios = [
    {
        "name": "No Default",
        "description": "Loan performs as expected",
        "recovery": 1.00,
        "default_month": 0,
        "legal_costs": 0.00,
        "color": "#06ffa5",
    },
    {
        "name": "Mild Stress",
        "description": "Early workout, good recovery",
        "recovery": 0.90,
        "default_month": 12,
        "legal_costs": 0.03,
        "color": "#4cc9f0",
    },
    {
        "name": "Moderate Stress",
        "description": "Typical default scenario",
        "recovery": 0.75,
        "default_month": 18,
        "legal_costs": 0.05,
        "color": "#ffa15a",
    },
    {
        "name": "Severe Stress",
        "description": "Difficult market conditions",
        "recovery": 0.60,
        "default_month": 24,
        "legal_costs": 0.08,
        "color": "#ef553b",
    },
    {
        "name": "Catastrophic",
        "description": "Fire sale / distressed market",
        "recovery": 0.45,
        "default_month": 12,
        "legal_costs": 0.10,
        "color": "#9c27b0",
    },
]

# Run all preset scenarios
scenario_results = []
for ps in preset_scenarios:
    if ps["default_month"] == 0:
        # No default scenario
        scenario_results.append({
            "scenario": ps,
            "total_loss": 0,
            "a_loss": 0,
            "b_loss": 0,
            "c_loss": 0,
            "agg_loss": 0,
            "a_loss_pct": 0,
            "b_loss_pct": 0,
            "c_loss_pct": 0,
        })
    else:
        scenario = DefaultScenario(
            name=ps["name"],
            default_month=ps["default_month"],
            recovery_rate=ps["recovery"],
            months_to_recovery=12,
            legal_costs_pct=ps["legal_costs"],
        )
        result = run_loss_waterfall(
            p['loan_amount'],
            p['property_value'],
            p['a_pct'],
            p['b_pct'],
            p['c_pct'],
            scenario,
            p['current_sofr'],
            p['borrower_spread'],
            accrued_months=ps["default_month"],
        )

        # Extract losses by tranche
        a_loss = 0
        b_loss = 0
        c_loss = 0
        for alloc in result.allocations:
            if "A" in alloc.tranche_name:
                a_loss = alloc.loss_amount
            elif "B" in alloc.tranche_name:
                b_loss = alloc.loss_amount
            elif "C" in alloc.tranche_name:
                c_loss = alloc.loss_amount

        scenario_results.append({
            "scenario": ps,
            "total_loss": result.total_loss,
            "a_loss": a_loss,
            "b_loss": b_loss,
            "c_loss": c_loss,
            "agg_loss": c_loss * coinvest_pct,
            "a_loss_pct": a_loss / a_amt if a_amt > 0 else 0,
            "b_loss_pct": b_loss / b_amt if b_amt > 0 else 0,
            "c_loss_pct": c_loss / c_amt if c_amt > 0 else 0,
        })

# Display scenario cards
st.markdown("##### Scenario Overview")
scen_cols = st.columns(5)

for i, sr in enumerate(scenario_results):
    ps = sr["scenario"]
    with scen_cols[i]:
        c_loss_display = f"{sr['c_loss_pct']:.0%}" if sr['c_loss_pct'] < 1 else "100%"
        st.markdown(f"""<div style="background:rgba({int(ps['color'][1:3], 16)}, {int(ps['color'][3:5], 16)}, {int(ps['color'][5:7], 16)}, 0.15); border:1px solid {ps['color']}; border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:{ps['color']}; font-weight:600; font-size:0.85rem;">{ps['name']}</div>
<div style="color:#78909c; font-size:0.7rem; margin:0.3rem 0;">{ps['description']}</div>
<div style="color:#e0e0e0; font-size:1.2rem; font-weight:700;">{safe_currency(sr['total_loss'])}</div>
<div style="color:#78909c; font-size:0.7rem;">Total Loss</div>
<div style="border-top:1px solid rgba(255,255,255,0.1); margin-top:0.5rem; padding-top:0.5rem;">
<div style="color:#ef553b; font-size:0.75rem;">C-Fund: {c_loss_display}</div>
</div>
</div>""", unsafe_allow_html=True)

# Detailed comparison table
st.markdown("##### Detailed Comparison")

comparison_data = []
for sr in scenario_results:
    ps = sr["scenario"]
    comparison_data.append({
        "Scenario": ps["name"],
        "Recovery Rate": f"{ps['recovery']:.0%}",
        "Default Month": ps["default_month"] if ps["default_month"] > 0 else "N/A",
        "Legal Costs": f"{ps['legal_costs']:.0%}",
        "Total Loss": safe_currency(sr['total_loss']),
        "A-Piece Loss": safe_currency(sr['a_loss']),
        "B-Fund Loss": safe_currency(sr['b_loss']),
        "C-Fund Loss": safe_currency(sr['c_loss']),
        "Agg Co-Invest Loss": safe_currency(sr['agg_loss']),
    })

st.dataframe(comparison_data, use_container_width=True, hide_index=True)

# Bar chart comparison
default_scenarios_only = [sr for sr in scenario_results if sr["scenario"]["default_month"] > 0]
if default_scenarios_only:
    fig = create_grouped_bar_chart(
        categories=[sr["scenario"]["name"] for sr in default_scenarios_only],
        groups={
            "A-Piece": [sr["a_loss"] / 1e6 for sr in default_scenarios_only],
            "B-Fund": [sr["b_loss"] / 1e6 for sr in default_scenarios_only],
            "C-Fund": [sr["c_loss"] / 1e6 for sr in default_scenarios_only],
        },
        title="Loss by Tranche Across Scenarios ($M)",
        y_title="Loss ($M)",
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# =============================================================================
# SECTION 3: CUSTOM SCENARIO BUILDER
# =============================================================================
st.markdown("### Custom Scenario Builder")

st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:1rem; margin-bottom:1rem;">
<strong style="color:#4cc9f0;">Build Your Own Scenario</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
Enter specific assumptions to model a custom default scenario. Useful for stress testing specific situations.
</div>
</div>""", unsafe_allow_html=True)

custom_col1, custom_col2, custom_col3, custom_col4 = st.columns(4)

with custom_col1:
    custom_recovery = st.number_input(
        "Recovery Rate (%)",
        min_value=20,
        max_value=100,
        value=70,
        step=5,
        help="Property sale price as % of original value"
    ) / 100

with custom_col2:
    custom_month = st.number_input(
        "Default Month",
        min_value=1,
        max_value=p['term_months'],
        value=12,
        step=3,
        help="When default occurs"
    )

with custom_col3:
    custom_legal = st.number_input(
        "Legal/Workout Costs (%)",
        min_value=0,
        max_value=20,
        value=5,
        step=1,
        help="Foreclosure and legal costs"
    ) / 100

with custom_col4:
    custom_recovery_months = st.number_input(
        "Months to Recover",
        min_value=3,
        max_value=24,
        value=12,
        step=3,
        help="Time to sell property"
    )

# Run custom scenario
custom_scenario = DefaultScenario(
    name="Custom",
    default_month=custom_month,
    recovery_rate=custom_recovery,
    months_to_recovery=custom_recovery_months,
    legal_costs_pct=custom_legal,
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
    accrued_months=custom_month,
)

# Display results
st.markdown("##### Custom Scenario Results")

res_col1, res_col2 = st.columns([1, 2])

with res_col1:
    # Summary metrics
    st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:8px; padding:1rem;">
<div style="color:#ef553b; font-weight:600; margin-bottom:0.8rem;">Loss Summary</div>
<div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
<span style="color:#b0bec5;">Property Value:</span>
<span style="color:#e0e0e0;">${p['property_value']/1e6:.1f}M</span>
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
<span style="color:#b0bec5;">Recovery Value:</span>
<span style="color:#e0e0e0;">${p['property_value']*custom_recovery/1e6:.1f}M</span>
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
<span style="color:#b0bec5;">Loan Balance:</span>
<span style="color:#e0e0e0;">${p['loan_amount']/1e6:.1f}M</span>
</div>
<div style="display:flex; justify-content:space-between; padding-top:0.5rem; border-top:1px solid rgba(239,85,59,0.3);">
<span style="color:#ef553b; font-weight:600;">Total Loss:</span>
<span style="color:#ef553b; font-weight:600;">${custom_result.total_loss/1e6:.2f}M</span>
</div>
</div>""", unsafe_allow_html=True)

with res_col2:
    # Loss allocation table
    alloc_data = []
    for a in custom_result.allocations:
        status = "Wiped Out" if a.is_wiped_out else "Impaired" if a.loss_amount > 0 else "Protected"
        status_color = "#ef553b" if a.is_wiped_out else "#ffa15a" if a.loss_amount > 0 else "#06ffa5"
        alloc_data.append({
            "Tranche": a.tranche_name,
            "Principal": f"${a.tranche_amount:,.0f}",
            "Loss": f"${a.loss_amount:,.0f}",
            "Loss %": f"{a.loss_percentage:.0%}",
            "Recovery": f"${a.recovery_amount:,.0f}",
            "Status": status,
        })

    st.dataframe(alloc_data, use_container_width=True, hide_index=True)

# Loss waterfall visualization
st.markdown("##### Loss Waterfall")

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
    title=f"Loss Allocation: {custom_recovery:.0%} Recovery at Month {custom_month}",
)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# =============================================================================
# SECTION 4: PROBABILITY & EXPECTED LOSS
# =============================================================================
st.markdown("### Probability Analysis")

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

prob_col1, prob_col2, prob_col3 = st.columns(3)

with prob_col1:
    st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border-radius:8px; padding:1.2rem; text-align:center;">
<div style="color:#4cc9f0; font-weight:600; font-size:0.9rem;">Annual PD</div>
<div style="color:#78909c; font-size:0.75rem;">Probability of Default per Year</div>
<div style="color:#e0e0e0; font-size:2rem; font-weight:700; margin:0.5rem 0;">{annual_pd:.2%}</div>
<div style="color:#78909c; font-size:0.75rem;">Based on {ltv:.0%} LTV</div>
</div>""", unsafe_allow_html=True)

with prob_col2:
    st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-radius:8px; padding:1.2rem; text-align:center;">
<div style="color:#ffa15a; font-weight:600; font-size:0.9rem;">Cumulative PD</div>
<div style="color:#78909c; font-size:0.75rem;">Over {p['hud_month']} Month Hold</div>
<div style="color:#e0e0e0; font-size:2rem; font-weight:700; margin:0.5rem 0;">{expected_loss['cumulative_pd']:.2%}</div>
<div style="color:#78909c; font-size:0.75rem;">Assuming {term_years:.1f} year term</div>
</div>""", unsafe_allow_html=True)

with prob_col3:
    st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:8px; padding:1.2rem; text-align:center;">
<div style="color:#ef553b; font-weight:600; font-size:0.9rem;">Expected Loss</div>
<div style="color:#78909c; font-size:0.75rem;">PD × LGD × Exposure</div>
<div style="color:#e0e0e0; font-size:2rem; font-weight:700; margin:0.5rem 0;">{safe_currency(expected_loss['expected_loss'])}</div>
<div style="color:#78909c; font-size:0.75rem;">{expected_loss['expected_loss_pct']:.3%} of loan</div>
</div>""", unsafe_allow_html=True)

st.divider()

# =============================================================================
# SECTION 5: RISK SUMMARY
# =============================================================================
st.markdown("### Risk Summary & Recommendations")

# Determine risk level
if ltv <= 0.75 and annual_pd <= 0.02:
    risk_status = "LOW"
    risk_color = "#06ffa5"
    risk_desc = "Conservative structure with strong protection for all tranches."
elif ltv <= 0.85 and annual_pd <= 0.04:
    risk_status = "MODERATE"
    risk_color = "#ffa15a"
    risk_desc = "Standard market terms. C-Fund provides adequate cushion for senior tranches."
else:
    risk_status = "ELEVATED"
    risk_color = "#ef553b"
    risk_desc = "Higher leverage increases loss exposure. Consider additional credit enhancements."

sum_col1, sum_col2 = st.columns([1, 2])

with sum_col1:
    st.markdown(f"""<div style="
        background: linear-gradient(135deg, rgba({int(risk_color[1:3], 16)}, {int(risk_color[3:5], 16)}, {int(risk_color[5:7], 16)}, 0.2), rgba(26,35,50,0.9));
        border: 2px solid {risk_color};
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    ">
        <div style="font-size: 0.85rem; color: #b0bec5;">Overall Risk Level</div>
        <div style="font-size: 2.5rem; font-weight: 700; color: {risk_color};">{risk_status}</div>
        <div style="font-size: 0.8rem; color: #78909c; margin-top:0.5rem;">{risk_desc}</div>
    </div>""", unsafe_allow_html=True)

with sum_col2:
    st.markdown("##### Key Risk Factors")

    # Build risk factor list
    risk_factors = []

    if ltv > 0.85:
        risk_factors.append(("High LTV", f"{ltv:.0%} LTV increases loss severity in default", "#ef553b"))
    elif ltv > 0.75:
        risk_factors.append(("Moderate LTV", f"{ltv:.0%} LTV is market standard", "#ffa15a"))
    else:
        risk_factors.append(("Conservative LTV", f"{ltv:.0%} LTV provides strong cushion", "#06ffa5"))

    if p['c_pct'] >= 0.15:
        risk_factors.append(("Strong C-Cushion", f"{p['c_pct']:.0%} first loss protects seniors", "#06ffa5"))
    elif p['c_pct'] >= 0.10:
        risk_factors.append(("Adequate C-Cushion", f"{p['c_pct']:.0%} first loss is market standard", "#ffa15a"))
    else:
        risk_factors.append(("Thin C-Cushion", f"{p['c_pct']:.0%} first loss may be insufficient", "#ef553b"))

    if coinvest_pct > 0:
        risk_factors.append(("Aligned Interests", f"Aggregator has {coinvest_pct:.0%} co-invest ({safe_currency(agg_exposure)})", "#06ffa5"))
    else:
        risk_factors.append(("No Co-Invest", "Aggregator has no capital at risk", "#ffa15a"))

    for factor_name, factor_desc, factor_color in risk_factors:
        st.markdown(f"""<div style="display:flex; align-items:center; margin-bottom:0.5rem; padding:0.5rem; background:rgba(255,255,255,0.02); border-radius:6px;">
<div style="width:12px; height:12px; background:{factor_color}; border-radius:50%; margin-right:0.8rem;"></div>
<div>
<div style="color:#e0e0e0; font-size:0.9rem; font-weight:500;">{factor_name}</div>
<div style="color:#78909c; font-size:0.8rem;">{factor_desc}</div>
</div>
</div>""", unsafe_allow_html=True)

st.divider()
st.caption("HUD Financing Platform | Risk Analysis")
