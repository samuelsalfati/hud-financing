"""
Scenarios Page - HUD timing, rate shocks, and combined stress testing
"""
import streamlit as st
import pandas as pd
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def fmt_pct(val):
    """Format percentage, handling inf/nan"""
    if math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.1%}"


def fmt_moic(val):
    """Format MOIC, handling inf/nan"""
    if math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.2f}x"

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from components.charts import create_grouped_bar_chart, create_line_chart, create_heatmap
from engine.deal import Deal, Tranche, TrancheType, RateType, FeeStructure
from engine.scenarios import get_standard_scenarios, get_rate_scenarios, run_scenarios, Scenario

# Page config
st.set_page_config(
    page_title="Scenarios | HUD Financing",
    page_icon="📈",
    layout="wide",
)

if not check_password():
    st.stop()

st.markdown(get_page_css(), unsafe_allow_html=True)

# Sidebar
sofr_data = render_sofr_indicator()
render_logo()

# Check if deal is configured
if 'deal_params' not in st.session_state or 'deal' not in st.session_state:
    st.warning("⚠️ No deal configured. Please set up your deal in Executive Summary first.")
    st.page_link("pages/1_Executive_Summary.py", label="→ Go to Executive Summary")
    st.stop()

# Get deal params
p = st.session_state['deal_params']
deal = st.session_state.get('deal')
results = st.session_state.get('results')
is_principal = p.get('is_principal', True)

# Safety check
if deal is None:
    st.error("Deal configuration is incomplete. Please reconfigure in Executive Summary.")
    st.page_link("pages/1_Executive_Summary.py", label="→ Go to Executive Summary")
    st.stop()

# Build SOFR curve from session state
sofr_curve = [p['current_sofr']] * 60

# Header
st.markdown(page_header(
    "Scenario Analysis",
    "HUD timing, rate shocks, and stress testing"
), unsafe_allow_html=True)

# Deal Summary Bar
role_label = "Principal (C-Piece)" if is_principal else "Aggregator (Fees)"
role_color = "#ef553b" if is_principal else "#06ffa5"
st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
<span style="color:#b0bec5;">Property: <strong style="color:#4cc9f0;">${p['property_value']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">Loan: <strong style="color:#4cc9f0;">${p['loan_amount']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">LTV: <strong style="color:#4cc9f0;">{p['ltv']:.0%}</strong></span>
<span style="color:#b0bec5;">Term: <strong style="color:#4cc9f0;">{p['term_months']}mo</strong></span>
<span style="color:#b0bec5;">SOFR: <strong style="color:#06ffa5;">{p['current_sofr']:.2%}</strong></span>
<span style="color:#b0bec5;">Role: <strong style="color:{role_color};">{role_label}</strong></span>
</div>""", unsafe_allow_html=True)

# Mode explanation
if not is_principal:
    st.markdown("""<div style="background:rgba(6,255,165,0.1); border:1px solid rgba(6,255,165,0.3); border-radius:8px; padding:0.6rem 1rem; margin-bottom:1rem;">
<strong style="color:#06ffa5;">📊 Aggregator Mode</strong>
<span style="color:#b0bec5; font-size:0.85rem;"> — Returns shown as Profit and Yield on Deal (no MOIC since no capital invested)</span>
</div>""", unsafe_allow_html=True)

# Scenario type selector
scenario_type = st.radio(
    "Scenario Type",
    ["HUD Timing", "Rate Shocks", "Combined Stress", "Custom"],
    horizontal=True,
)

st.divider()

if scenario_type == "HUD Timing":
    st.subheader("HUD Takeout Timing Scenarios")

    try:
        scenarios = get_standard_scenarios(deal)
        results_scenarios = run_scenarios(deal, scenarios, sofr_curve, is_principal)
    except Exception as e:
        st.error(f"Error running scenarios: {e}")
        st.stop()

    # Results table
    results_data = []
    for r in results_scenarios:
        row = {
            "Scenario": r.scenario.name,
            "Exit Month": r.scenario.exit_month,
            "Extension": "Yes" if r.scenario.has_extension else "No",
            "Sponsor IRR": fmt_pct(r.sponsor_irr),
            "Profit": f"${r.sponsor_profit:,.0f}",
            "A IRR": fmt_pct(r.a_irr),
            "B IRR": fmt_pct(r.b_irr),
        }
        # Only show MOIC in Principal mode (meaningful metric)
        if is_principal:
            row["MOIC"] = fmt_moic(r.sponsor_moic)
        results_data.append(row)

    st.dataframe(results_data, use_container_width=True, hide_index=True)

    # IRR comparison chart
    fig = create_grouped_bar_chart(
        categories=[r.scenario.name for r in results_scenarios],
        groups={
            "Sponsor IRR": [r.sponsor_irr * 100 for r in results_scenarios],
            "A-Piece IRR": [r.a_irr * 100 for r in results_scenarios],
            "B-Piece IRR": [r.b_irr * 100 for r in results_scenarios],
        },
        title="IRR by Timing Scenario",
        y_title="IRR (%)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Key insight
    base_case = next((r for r in results_scenarios if "Base" in r.scenario.name), results_scenarios[0])
    worst_case = min(results_scenarios, key=lambda r: r.sponsor_irr)
    best_case = max(results_scenarios, key=lambda r: r.sponsor_irr)

    st.info(f"""
    **Timing Analysis:**
    - **Best Case:** {best_case.scenario.name} with {fmt_pct(best_case.sponsor_irr)} IRR
    - **Base Case:** {base_case.scenario.name} with {fmt_pct(base_case.sponsor_irr)} IRR
    - **Worst Case:** {worst_case.scenario.name} with {fmt_pct(worst_case.sponsor_irr)} IRR
    - IRR spread: {(best_case.sponsor_irr - worst_case.sponsor_irr)*100:.0f} bps
    """)

elif scenario_type == "Rate Shocks":
    st.subheader("Interest Rate Shock Scenarios")

    try:
        scenarios = get_rate_scenarios(p['current_sofr'])
        results_scenarios = run_scenarios(deal, scenarios, sofr_curve, is_principal)
    except Exception as e:
        st.error(f"Error running rate scenarios: {e}")
        st.stop()

    # Results table
    results_data = []
    for r in results_scenarios:
        new_sofr = p['current_sofr'] + r.scenario.sofr_shift
        row = {
            "Scenario": r.scenario.name,
            "SOFR Shift": f"{r.scenario.sofr_shift*10000:+.0f} bps",
            "New SOFR": f"{new_sofr:.2%}",
            "Sponsor IRR": fmt_pct(r.sponsor_irr),
            "Profit": f"${r.sponsor_profit:,.0f}",
            "A IRR": fmt_pct(r.a_irr),
            "B IRR": fmt_pct(r.b_irr),
            "Borrower Cost": fmt_pct(r.borrower_all_in_cost),
        }
        if is_principal:
            row["MOIC"] = fmt_moic(r.sponsor_moic)
        results_data.append(row)

    st.dataframe(results_data, use_container_width=True, hide_index=True)

    # Rate impact chart
    sofr_changes = [r.scenario.sofr_shift * 100 for r in results_scenarios]
    sponsor_irrs = [r.sponsor_irr * 100 for r in results_scenarios]

    fig = create_line_chart(
        x=sofr_changes,
        y=sponsor_irrs,
        name="Sponsor IRR",
        title="Sponsor IRR vs SOFR Change",
        x_title="SOFR Change (bps)",
        y_title="Sponsor IRR (%)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Rate sensitivity
    base_irr = next((r.sponsor_irr for r in results_scenarios if r.scenario.sofr_shift == 0), results_scenarios[0].sponsor_irr)
    plus_100 = next((r.sponsor_irr for r in results_scenarios if r.scenario.sofr_shift == 0.01), base_irr)

    st.info(f"""
    **Rate Sensitivity:**
    - Base IRR at current SOFR ({p['current_sofr']:.2%}): **{fmt_pct(base_irr)}**
    - +100 bps shock impact: **{(plus_100 - base_irr)*100:+.0f} bps** IRR change
    - Sponsor is {'well protected' if abs(plus_100 - base_irr) < 0.02 else 'moderately exposed' if abs(plus_100 - base_irr) < 0.05 else 'significantly exposed'} to rate changes
    """)

elif scenario_type == "Combined Stress":
    st.subheader("Combined Stress Testing")

    st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:1rem; margin-bottom:1.5rem;">
<strong style="color:#4cc9f0;">How to Read This Matrix</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
<strong>Rows (↓)</strong> = HUD Exit Timing (when the permanent HUD loan closes)<br>
<strong>Columns (→)</strong> = SOFR Rate Change from today<br>
<strong>Cell Value</strong> = Your IRR under that scenario<br><br>
<span style="color:#06ffa5;">Green = Higher IRR (better)</span> | <span style="color:#ef553b;">Red = Lower IRR (worse)</span>
</div>
</div>""", unsafe_allow_html=True)

    # Generate combined scenarios
    timing_options = [18, 24, 30, 36, 42]
    rate_options = [-0.01, 0, 0.01, 0.02]

    try:
        # Create heatmap data
        irr_matrix = []
        for timing in timing_options:
            row = []
            for rate_shift in rate_options:
                scenario = Scenario(
                    name=f"{timing}mo / {rate_shift*100:+.0f}bps",
                    exit_month=timing,
                    has_extension=timing > deal.term_months,
                    sofr_shift=rate_shift,
                )
                result = run_scenarios(deal, [scenario], sofr_curve, is_principal)[0]
                row.append(result.sponsor_irr)
            irr_matrix.append(row)
    except Exception as e:
        st.error(f"Error running stress scenarios: {e}")
        st.stop()

    # Create heatmap
    fig = create_heatmap(
        z=irr_matrix,
        x_labels=[f"{r*100:+.0f} bps" for r in rate_options],
        y_labels=[f"{t} months" for t in timing_options],
        title="Sponsor IRR: Timing x Rate Stress Matrix",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Identify best/worst scenarios
    min_irr = min(min(row) for row in irr_matrix)
    max_irr = max(max(row) for row in irr_matrix)
    base_irr = irr_matrix[1][1]  # 24mo, 0 bps = base case

    # Find which cell is best/worst
    best_timing_idx = 0
    best_rate_idx = 0
    worst_timing_idx = 0
    worst_rate_idx = 0
    for i, row in enumerate(irr_matrix):
        for j, val in enumerate(row):
            if val == max_irr:
                best_timing_idx, best_rate_idx = i, j
            if val == min_irr:
                worst_timing_idx, worst_rate_idx = i, j

    st.divider()

    # Summary in columns
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""<div style="background:rgba(6,255,165,0.1); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#06ffa5; font-weight:600;">Best Case</div>
<div style="font-size:1.5rem; color:white;">{fmt_pct(max_irr)}</div>
<div style="color:#78909c; font-size:0.8rem;">{timing_options[best_timing_idx]}mo exit, {rate_options[best_rate_idx]*100:+.0f}bps SOFR</div>
</div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#4cc9f0; font-weight:600;">Base Case</div>
<div style="font-size:1.5rem; color:white;">{fmt_pct(base_irr)}</div>
<div style="color:#78909c; font-size:0.8rem;">24mo exit, current rates</div>
</div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#ef553b; font-weight:600;">Worst Case</div>
<div style="font-size:1.5rem; color:white;">{fmt_pct(min_irr)}</div>
<div style="color:#78909c; font-size:0.8rem;">{timing_options[worst_timing_idx]}mo exit, {rate_options[worst_rate_idx]*100:+.0f}bps SOFR</div>
</div>""", unsafe_allow_html=True)

    # Key insights
    st.markdown("#### Key Insights")

    irr_range = (max_irr - min_irr) * 100
    timing_sensitivity = abs(irr_matrix[0][1] - irr_matrix[-1][1]) * 100  # Same rate, different timing
    rate_sensitivity = abs(irr_matrix[1][0] - irr_matrix[1][-1]) * 100  # Same timing, different rate

    if timing_sensitivity > rate_sensitivity:
        main_risk = "**HUD Timing**"
        risk_desc = "Exit delays hurt more than rate changes"
    else:
        main_risk = "**Interest Rates**"
        risk_desc = "Rate increases hurt more than exit delays"

    st.markdown(f"""
- **IRR Range:** {irr_range:.0f} bps between best and worst case
- **Primary Risk Driver:** {main_risk} — {risk_desc}
- **Timing Impact:** {timing_sensitivity:.0f} bps IRR change from early to late exit
- **Rate Impact:** {rate_sensitivity:.0f} bps IRR change from rates down to rates up
    """)

else:  # Custom
    st.subheader("Custom Scenario Builder")

    st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:1rem; margin-bottom:1.5rem;">
<strong style="color:#4cc9f0;">Build Your Scenario</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
Adjust exit timing and rate assumptions to model different outcomes.
</div>
</div>""", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        custom_exit = st.number_input(
            "Exit Month (mo)",
            min_value=12,
            max_value=60,
            value=p['hud_month'],
            step=1,
        )

    with col2:
        custom_sofr_shift = st.number_input(
            "SOFR Shift (bps)",
            min_value=-200,
            max_value=300,
            value=0,
            step=25,
        )

    with col3:
        custom_extension = st.checkbox(
            "Extension Used",
            value=custom_exit > deal.term_months,
        )

    with col4:
        st.markdown(f"""<div style="padding-top:1.5rem; color:#b0bec5; font-size:0.85rem;">
New SOFR: <strong style="color:#06ffa5;">{(p['current_sofr'] + custom_sofr_shift/10000):.2%}</strong>
</div>""", unsafe_allow_html=True)

    # Run custom scenario
    try:
        custom_scenario = Scenario(
            name=f"Custom ({custom_exit}mo, {custom_sofr_shift:+}bps)",
            exit_month=custom_exit,
            has_extension=custom_extension,
            sofr_shift=custom_sofr_shift / 10000,
        )

        custom_results = run_scenarios(deal, [custom_scenario], sofr_curve, is_principal)[0]
    except Exception as e:
        st.error(f"Error running custom scenario: {e}")
        st.stop()

    st.divider()

    # Display results
    st.markdown("### Scenario Results")

    if is_principal:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sponsor IRR", fmt_pct(custom_results.sponsor_irr))
        with col2:
            st.metric("Sponsor MOIC", fmt_moic(custom_results.sponsor_moic))
        with col3:
            st.metric("Sponsor Profit", f"${custom_results.sponsor_profit:,.0f}")
        with col4:
            st.metric("Borrower Cost", fmt_pct(custom_results.borrower_all_in_cost))
    else:
        # Aggregator mode - no MOIC, show yield metrics instead
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sponsor IRR", fmt_pct(custom_results.sponsor_irr))
        with col2:
            st.metric("Total Profit", f"${custom_results.sponsor_profit:,.0f}")
        with col3:
            # Annualized yield on deal
            annual_profit = custom_results.sponsor_profit * (12 / custom_exit) if custom_exit > 0 else 0
            yield_on_deal = annual_profit / p['loan_amount'] if p['loan_amount'] > 0 else 0
            st.metric("Yield on Deal", f"{yield_on_deal:.2%}")
        with col4:
            st.metric("Borrower Cost", fmt_pct(custom_results.borrower_all_in_cost))

    # Tranche results
    st.markdown("### Tranche Returns")
    tranche_data = [
        {"Tranche": "A-Piece (Senior)", "IRR": fmt_pct(custom_results.a_irr)},
        {"Tranche": "B-Piece (Mezz)", "IRR": fmt_pct(custom_results.b_irr)},
        {"Tranche": "C-Piece (Sponsor)", "IRR": fmt_pct(custom_results.c_irr)},
    ]
    st.dataframe(tranche_data, use_container_width=True, hide_index=True)

    # Comparison with base case
    if results:
        base_sponsor_irr = results['sponsor'].irr
        irr_delta = custom_results.sponsor_irr - base_sponsor_irr
        if not math.isinf(irr_delta) and not math.isnan(irr_delta):
            st.info(f"""
            **Comparison to Base Case ({p['hud_month']}mo exit):**
            - IRR change: **{irr_delta*100:+.0f} bps** vs base case ({fmt_pct(base_sponsor_irr)})
            """)

st.divider()
st.caption("HUD Financing Platform | Scenario Analysis")
