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
    """Format percentage, handling inf/nan/None"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.1%}"


def fmt_moic(val):
    """Format MOIC, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.2f}x"


def safe_irr_spread(val1, val2):
    """Calculate IRR spread in bps, handling inf/nan"""
    if val1 is None or val2 is None:
        return "N/A"
    if math.isinf(val1) or math.isnan(val1) or math.isinf(val2) or math.isnan(val2):
        return "N/A"
    return f"{(val1 - val2)*100:.0f}"


def safe_bps(val):
    """Format bps value, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.0f}"

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from components.charts import create_grouped_bar_chart, create_line_chart, create_heatmap
from engine.deal import Deal, Tranche, TrancheType, RateType, FeeStructure, FundTerms
from engine.scenarios import get_standard_scenarios, get_rate_scenarios, run_scenarios, run_scenario, Scenario
import plotly.graph_objects as go

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
coinvest_pct = p.get('agg_coinvest', 0)
role_label = f"Co-Invest ({coinvest_pct:.0%} of C)" if coinvest_pct > 0 else "Aggregator (Fee-only)"
role_color = "#ef553b" if coinvest_pct > 0 else "#06ffa5"
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
<strong style="color:#06ffa5;">📊 Aggregator Mode (Fee-Only)</strong>
<span style="color:#b0bec5; font-size:0.85rem;"> — Income from AUM fees, promote, and fee allocation. No capital at risk.</span>
</div>""", unsafe_allow_html=True)
else:
    st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border:1px solid rgba(239,85,59,0.3); border-radius:8px; padding:0.6rem 1rem; margin-bottom:1rem;">
<strong style="color:#ef553b;">📊 Co-Invest Mode ({coinvest_pct:.0%} of C-Piece)</strong>
<span style="color:#b0bec5; font-size:0.85rem;"> — Returns include co-invest returns (fee-free) + AUM fees + promote.</span>
</div>""", unsafe_allow_html=True)

# Scenario type selector
scenario_type = st.radio(
    "Scenario Type",
    ["HUD Timing", "Rate Shocks", "Combined Stress", "Fee Sensitivity", "Breakeven", "Custom"],
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

    # Results table - Gross Returns
    st.markdown("##### Gross Tranche Returns")
    results_data = []
    for r in results_scenarios:
        row = {
            "Scenario": r.scenario.name,
            "Exit Month": r.scenario.exit_month,
            "Extension": "Yes" if r.scenario.has_extension else "No",
            "A IRR": fmt_pct(r.a_irr),
            "B IRR (Gross)": fmt_pct(r.b_irr),
            "C IRR (Gross)": fmt_pct(r.c_irr),
        }
        results_data.append(row)

    st.dataframe(results_data, use_container_width=True, hide_index=True)

    # LP Net Returns table
    st.markdown("##### LP Net Returns (After AUM & Promote)")
    lp_data = []
    for r in results_scenarios:
        row = {
            "Scenario": r.scenario.name,
            "B-Fund LP IRR": fmt_pct(r.b_lp_irr),
            "B-Fund LP MOIC": fmt_moic(r.b_lp_moic),
            "C-Fund LP IRR": fmt_pct(r.c_lp_irr),
            "C-Fund LP MOIC": fmt_moic(r.c_lp_moic),
        }
        lp_data.append(row)

    st.dataframe(lp_data, use_container_width=True, hide_index=True)

    # Aggregator Economics table
    st.markdown("##### Aggregator Economics by Scenario")
    agg_data = []
    for r in results_scenarios:
        if r.aggregator:
            row = {
                "Scenario": r.scenario.name,
                "Fee Allocation": f"${r.aggregator.fee_allocation:,.0f}",
                "AUM Fees": f"${r.aggregator.total_aum:,.0f}",
                "Promote": f"${r.aggregator.total_promote:,.0f}",
                "Co-Invest": f"${r.aggregator.coinvest_returns:,.0f}",
                "Total": f"${r.aggregator.grand_total:,.0f}",
            }
            agg_data.append(row)

    if agg_data:
        st.dataframe(agg_data, use_container_width=True, hide_index=True)

    # IRR comparison chart - now includes LP returns
    fig = create_grouped_bar_chart(
        categories=[r.scenario.name for r in results_scenarios],
        groups={
            "A-Piece (Bank)": [r.a_irr * 100 for r in results_scenarios],
            "B-Fund Gross": [r.b_irr * 100 for r in results_scenarios],
            "B-Fund LP Net": [r.b_lp_irr * 100 for r in results_scenarios],
            "C-Fund Gross": [r.c_irr * 100 for r in results_scenarios],
            "C-Fund LP Net": [r.c_lp_irr * 100 for r in results_scenarios],
        },
        title="IRR by Timing Scenario (Gross vs LP Net)",
        y_title="IRR (%)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Key insight
    base_case = next((r for r in results_scenarios if "Base" in r.scenario.name), results_scenarios[0])
    worst_case = min(results_scenarios, key=lambda r: r.c_lp_irr)
    best_case = max(results_scenarios, key=lambda r: r.c_lp_irr)

    st.info(f"""
    **Timing Analysis (C-Fund LP Perspective):**
    - **Best Case:** {best_case.scenario.name} with {fmt_pct(best_case.c_lp_irr)} LP IRR
    - **Base Case:** {base_case.scenario.name} with {fmt_pct(base_case.c_lp_irr)} LP IRR
    - **Worst Case:** {worst_case.scenario.name} with {fmt_pct(worst_case.c_lp_irr)} LP IRR
    - LP IRR spread: {safe_irr_spread(best_case.c_lp_irr, worst_case.c_lp_irr)} bps
    """)

elif scenario_type == "Rate Shocks":
    st.subheader("Interest Rate Shock Scenarios")

    try:
        scenarios = get_rate_scenarios(p['current_sofr'])
        results_scenarios = run_scenarios(deal, scenarios, sofr_curve, is_principal)
    except Exception as e:
        st.error(f"Error running rate scenarios: {e}")
        st.stop()

    # Gross Returns table
    st.markdown("##### Gross Tranche Returns")
    results_data = []
    for r in results_scenarios:
        new_sofr = p['current_sofr'] + r.scenario.sofr_shift
        row = {
            "Scenario": r.scenario.name,
            "SOFR Shift": f"{r.scenario.sofr_shift*10000:+.0f} bps",
            "New SOFR": f"{new_sofr:.2%}",
            "A IRR": fmt_pct(r.a_irr),
            "B IRR (Gross)": fmt_pct(r.b_irr),
            "C IRR (Gross)": fmt_pct(r.c_irr),
            "Borrower Cost": fmt_pct(r.borrower_all_in_cost),
        }
        results_data.append(row)

    st.dataframe(results_data, use_container_width=True, hide_index=True)

    # LP Net Returns table
    st.markdown("##### LP Net Returns (After AUM & Promote)")
    lp_data = []
    for r in results_scenarios:
        row = {
            "Scenario": r.scenario.name,
            "B-Fund LP IRR": fmt_pct(r.b_lp_irr),
            "B-Fund LP MOIC": fmt_moic(r.b_lp_moic),
            "C-Fund LP IRR": fmt_pct(r.c_lp_irr),
            "C-Fund LP MOIC": fmt_moic(r.c_lp_moic),
        }
        lp_data.append(row)

    st.dataframe(lp_data, use_container_width=True, hide_index=True)

    # Aggregator Economics table
    st.markdown("##### Aggregator Economics by Scenario")
    agg_data = []
    for r in results_scenarios:
        if r.aggregator:
            row = {
                "Scenario": r.scenario.name,
                "Fee Allocation": f"${r.aggregator.fee_allocation:,.0f}",
                "AUM Fees": f"${r.aggregator.total_aum:,.0f}",
                "Promote": f"${r.aggregator.total_promote:,.0f}",
                "Co-Invest": f"${r.aggregator.coinvest_returns:,.0f}",
                "Total": f"${r.aggregator.grand_total:,.0f}",
            }
            agg_data.append(row)

    if agg_data:
        st.dataframe(agg_data, use_container_width=True, hide_index=True)

    # Rate impact chart - now shows LP returns too
    fig = create_grouped_bar_chart(
        categories=[r.scenario.name for r in results_scenarios],
        groups={
            "B-Fund Gross": [r.b_irr * 100 for r in results_scenarios],
            "B-Fund LP Net": [r.b_lp_irr * 100 for r in results_scenarios],
            "C-Fund Gross": [r.c_irr * 100 for r in results_scenarios],
            "C-Fund LP Net": [r.c_lp_irr * 100 for r in results_scenarios],
        },
        title="IRR by Rate Scenario (Gross vs LP Net)",
        y_title="IRR (%)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Rate sensitivity - now shows LP impact
    base_c_lp = next((r.c_lp_irr for r in results_scenarios if r.scenario.sofr_shift == 0), results_scenarios[0].c_lp_irr)
    plus_100_c_lp = next((r.c_lp_irr for r in results_scenarios if r.scenario.sofr_shift == 0.01), base_c_lp)

    # Calculate rate impact safely
    rate_impact_bps = "N/A"
    exposure_level = "unknown"
    if not (math.isinf(base_c_lp) or math.isnan(base_c_lp) or math.isinf(plus_100_c_lp) or math.isnan(plus_100_c_lp)):
        rate_diff = abs(plus_100_c_lp - base_c_lp)
        rate_impact_bps = f"{(plus_100_c_lp - base_c_lp)*100:+.0f}"
        exposure_level = 'well protected' if rate_diff < 0.02 else 'moderately exposed' if rate_diff < 0.05 else 'significantly exposed'

    st.info(f"""
    **Rate Sensitivity (C-Fund LP Perspective):**
    - Base LP IRR at current SOFR ({p['current_sofr']:.2%}): **{fmt_pct(base_c_lp)}**
    - +100 bps shock impact: **{rate_impact_bps} bps** LP IRR change
    - LP is {exposure_level} to rate changes
    """)

elif scenario_type == "Combined Stress":
    st.subheader("Combined Stress Testing")

    st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:1rem; margin-bottom:1.5rem;">
<strong style="color:#4cc9f0;">How to Read This Matrix</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
<strong>Rows (↓)</strong> = HUD Exit Timing (when the permanent HUD loan closes)<br>
<strong>Columns (→)</strong> = SOFR Rate Change from today<br>
<strong>Cell Value</strong> = IRR under that scenario<br><br>
<span style="color:#06ffa5;">Green = Higher IRR (better)</span> | <span style="color:#ef553b;">Red = Lower IRR (worse)</span>
</div>
</div>""", unsafe_allow_html=True)

    # Select which IRR to show
    irr_view = st.radio(
        "View IRR for:",
        ["C-Fund LP Net", "B-Fund LP Net", "C-Fund Gross", "B-Fund Gross"],
        horizontal=True,
    )

    # Generate combined scenarios
    timing_options = [18, 24, 30, 36, 42]
    rate_options = [-0.01, 0, 0.01, 0.02]

    try:
        # Create heatmap data and store full results
        irr_matrix = []
        all_results = []
        for timing in timing_options:
            row = []
            row_results = []
            for rate_shift in rate_options:
                scenario = Scenario(
                    name=f"{timing}mo / {rate_shift*100:+.0f}bps",
                    exit_month=timing,
                    has_extension=timing > deal.term_months,
                    sofr_shift=rate_shift,
                )
                result = run_scenarios(deal, [scenario], sofr_curve, is_principal)[0]
                row_results.append(result)
                # Select which IRR to display
                if irr_view == "C-Fund LP Net":
                    row.append(result.c_lp_irr)
                elif irr_view == "B-Fund LP Net":
                    row.append(result.b_lp_irr)
                elif irr_view == "C-Fund Gross":
                    row.append(result.c_irr)
                else:  # B-Fund Gross
                    row.append(result.b_irr)
            irr_matrix.append(row)
            all_results.append(row_results)
    except Exception as e:
        st.error(f"Error running stress scenarios: {e}")
        st.stop()

    # Create heatmap
    fig = create_heatmap(
        z=irr_matrix,
        x_labels=[f"{r*100:+.0f} bps" for r in rate_options],
        y_labels=[f"{t} months" for t in timing_options],
        title=f"{irr_view} IRR: Timing x Rate Stress Matrix",
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

    # Aggregator economics comparison for base vs worst
    st.markdown("#### Aggregator Economics: Base vs Worst Case")
    base_result = all_results[1][1]  # 24mo, 0 bps
    worst_result = all_results[worst_timing_idx][worst_rate_idx]

    if base_result.aggregator and worst_result.aggregator:
        agg_compare = [
            {
                "Scenario": "Base Case (24mo)",
                "Fee Allocation": f"${base_result.aggregator.fee_allocation:,.0f}",
                "AUM Fees": f"${base_result.aggregator.total_aum:,.0f}",
                "Promote": f"${base_result.aggregator.total_promote:,.0f}",
                "Co-Invest": f"${base_result.aggregator.coinvest_returns:,.0f}",
                "Total": f"${base_result.aggregator.grand_total:,.0f}",
            },
            {
                "Scenario": f"Worst ({timing_options[worst_timing_idx]}mo, {rate_options[worst_rate_idx]*100:+.0f}bps)",
                "Fee Allocation": f"${worst_result.aggregator.fee_allocation:,.0f}",
                "AUM Fees": f"${worst_result.aggregator.total_aum:,.0f}",
                "Promote": f"${worst_result.aggregator.total_promote:,.0f}",
                "Co-Invest": f"${worst_result.aggregator.coinvest_returns:,.0f}",
                "Total": f"${worst_result.aggregator.grand_total:,.0f}",
            },
        ]
        st.dataframe(agg_compare, use_container_width=True, hide_index=True)

        # Delta
        delta_total = worst_result.aggregator.grand_total - base_result.aggregator.grand_total
        delta_color = "#06ffa5" if delta_total >= 0 else "#ef553b"
        st.markdown(f"""<div style="text-align:center; padding:0.5rem;">
<span style="color:#78909c;">Aggregator Total Change:</span>
<span style="color:{delta_color}; font-weight:600; font-size:1.1rem;"> ${delta_total:+,.0f}</span>
</div>""", unsafe_allow_html=True)

    # Key insights
    st.markdown("#### Key Insights")

    # Calculate sensitivities safely
    def safe_range(v1, v2):
        if math.isinf(v1) or math.isnan(v1) or math.isinf(v2) or math.isnan(v2):
            return None
        return abs(v1 - v2) * 100

    irr_range = safe_range(max_irr, min_irr)
    timing_sensitivity = safe_range(irr_matrix[0][1], irr_matrix[-1][1])  # Same rate, different timing
    rate_sensitivity = safe_range(irr_matrix[1][0], irr_matrix[1][-1])  # Same timing, different rate

    if timing_sensitivity is not None and rate_sensitivity is not None:
        if timing_sensitivity > rate_sensitivity:
            main_risk = "**HUD Timing**"
            risk_desc = "Exit delays hurt more than rate changes"
        else:
            main_risk = "**Interest Rates**"
            risk_desc = "Rate increases hurt more than exit delays"
    else:
        main_risk = "**Undetermined**"
        risk_desc = "Unable to calculate sensitivity"

    st.markdown(f"""
- **IRR Range:** {safe_bps(irr_range)} bps between best and worst case
- **Primary Risk Driver:** {main_risk} — {risk_desc}
- **Timing Impact:** {safe_bps(timing_sensitivity)} bps IRR change from early to late exit
- **Rate Impact:** {safe_bps(rate_sensitivity)} bps IRR change from rates down to rates up
    """)

elif scenario_type == "Fee Sensitivity":
    st.subheader("Fee Sensitivity Analysis")

    st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:1rem; margin-bottom:1.5rem;">
<strong style="color:#4cc9f0;">How Fees Impact Returns</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
<strong>Deal Fees</strong> (Origination/Exit): Paid by borrower, allocated to tranches<br>
<strong>AUM Fees</strong>: Deducted from LP capital, paid to Aggregator monthly<br>
<strong>Promote</strong>: Share of profits above hurdle, paid to Aggregator at exit
</div>
</div>""", unsafe_allow_html=True)

    # Current fee structure
    st.markdown("##### Current Fee Structure")
    curr1, curr2, curr3, curr4, curr5, curr6 = st.columns(6)
    with curr1:
        st.metric("Origination", f"{p['orig_fee']*10000:.0f} bps")
    with curr2:
        st.metric("Exit Fee", f"{p['exit_fee']*10000:.0f} bps")
    with curr3:
        st.metric("B-Fund AUM", f"{p.get('b_aum_fee', 0.015)*100:.1f}%/yr")
    with curr4:
        st.metric("C-Fund AUM", f"{p.get('c_aum_fee', 0.02)*100:.1f}%/yr")
    with curr5:
        st.metric("B-Fund Promote", f"{p.get('b_promote', 0.20)*100:.0f}%")
    with curr6:
        st.metric("C-Fund Promote", f"{p.get('c_promote', 0.20)*100:.0f}%")

    st.divider()

    # Fee sensitivity selector
    fee_type = st.selectbox(
        "Analyze Sensitivity For:",
        ["AUM Fee (B & C)", "Promote Rate", "Origination Fee", "Exit Fee"],
    )

    # Generate scenarios based on fee type
    fee_scenarios = []
    base_exit = p['hud_month']

    if fee_type == "AUM Fee (B & C)":
        aum_rates = [0.005, 0.01, 0.015, 0.02, 0.025, 0.03]
        for aum in aum_rates:
            # Create modified deal with different AUM
            modified_deal = Deal(
                property_value=deal.property_value,
                loan_amount=deal.loan_amount,
                term_months=deal.term_months,
                expected_hud_month=deal.expected_hud_month,
                tranches=deal.tranches,
                fees=deal.fees,
                borrower_spread=deal.borrower_spread,
                b_fund_terms=FundTerms(aum_fee_pct=aum, promote_pct=p.get('b_promote', 0.20), hurdle_rate=p.get('b_hurdle', 0.08)),
                c_fund_terms=FundTerms(aum_fee_pct=aum, promote_pct=p.get('c_promote', 0.20), hurdle_rate=p.get('c_hurdle', 0.10)),
                aggregator_coinvest_pct=deal.aggregator_coinvest_pct,
            )
            scenario = Scenario(name=f"AUM {aum*100:.1f}%", exit_month=base_exit, has_extension=False)
            result = run_scenario(modified_deal, scenario, sofr_curve, is_principal)
            fee_scenarios.append({"rate": aum, "label": f"{aum*100:.1f}%", "result": result})

    elif fee_type == "Promote Rate":
        promote_rates = [0.10, 0.15, 0.20, 0.25, 0.30]
        for prom in promote_rates:
            modified_deal = Deal(
                property_value=deal.property_value,
                loan_amount=deal.loan_amount,
                term_months=deal.term_months,
                expected_hud_month=deal.expected_hud_month,
                tranches=deal.tranches,
                fees=deal.fees,
                borrower_spread=deal.borrower_spread,
                b_fund_terms=FundTerms(aum_fee_pct=p.get('b_aum_fee', 0.015), promote_pct=prom, hurdle_rate=p.get('b_hurdle', 0.08)),
                c_fund_terms=FundTerms(aum_fee_pct=p.get('c_aum_fee', 0.02), promote_pct=prom, hurdle_rate=p.get('c_hurdle', 0.10)),
                aggregator_coinvest_pct=deal.aggregator_coinvest_pct,
            )
            scenario = Scenario(name=f"Promote {prom*100:.0f}%", exit_month=base_exit, has_extension=False)
            result = run_scenario(modified_deal, scenario, sofr_curve, is_principal)
            fee_scenarios.append({"rate": prom, "label": f"{prom*100:.0f}%", "result": result})

    elif fee_type == "Origination Fee":
        orig_rates = [0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02]
        for orig in orig_rates:
            modified_fees = FeeStructure(origination_fee=orig, exit_fee=p['exit_fee'], extension_fee=p['ext_fee'])
            modified_deal = Deal(
                property_value=deal.property_value,
                loan_amount=deal.loan_amount,
                term_months=deal.term_months,
                expected_hud_month=deal.expected_hud_month,
                tranches=deal.tranches,
                fees=modified_fees,
                borrower_spread=deal.borrower_spread,
                b_fund_terms=deal.b_fund_terms,
                c_fund_terms=deal.c_fund_terms,
                aggregator_coinvest_pct=deal.aggregator_coinvest_pct,
            )
            scenario = Scenario(name=f"Orig {orig*10000:.0f}bps", exit_month=base_exit, has_extension=False)
            result = run_scenario(modified_deal, scenario, sofr_curve, is_principal)
            fee_scenarios.append({"rate": orig, "label": f"{orig*10000:.0f} bps", "result": result})

    else:  # Exit Fee
        exit_rates = [0, 0.0025, 0.005, 0.0075, 0.01, 0.015]
        for ex in exit_rates:
            modified_fees = FeeStructure(origination_fee=p['orig_fee'], exit_fee=ex, extension_fee=p['ext_fee'])
            modified_deal = Deal(
                property_value=deal.property_value,
                loan_amount=deal.loan_amount,
                term_months=deal.term_months,
                expected_hud_month=deal.expected_hud_month,
                tranches=deal.tranches,
                fees=modified_fees,
                borrower_spread=deal.borrower_spread,
                b_fund_terms=deal.b_fund_terms,
                c_fund_terms=deal.c_fund_terms,
                aggregator_coinvest_pct=deal.aggregator_coinvest_pct,
            )
            scenario = Scenario(name=f"Exit {ex*10000:.0f}bps", exit_month=base_exit, has_extension=False)
            result = run_scenario(modified_deal, scenario, sofr_curve, is_principal)
            fee_scenarios.append({"rate": ex, "label": f"{ex*10000:.0f} bps", "result": result})

    # Display results table
    st.markdown(f"##### {fee_type} Impact on Returns")
    fee_data = []
    for s in fee_scenarios:
        r = s["result"]
        row = {
            fee_type: s["label"],
            "B-Fund LP IRR": fmt_pct(r.b_lp_irr),
            "C-Fund LP IRR": fmt_pct(r.c_lp_irr),
            "Agg Total": f"${r.aggregator.grand_total:,.0f}" if r.aggregator else "N/A",
        }
        fee_data.append(row)

    st.dataframe(fee_data, use_container_width=True, hide_index=True)

    # Chart
    fig = create_grouped_bar_chart(
        categories=[s["label"] for s in fee_scenarios],
        groups={
            "B-Fund LP IRR": [s["result"].b_lp_irr * 100 for s in fee_scenarios],
            "C-Fund LP IRR": [s["result"].c_lp_irr * 100 for s in fee_scenarios],
        },
        title=f"LP Returns vs {fee_type}",
        y_title="IRR (%)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Aggregator impact
    st.markdown("##### Aggregator Economics by Fee Level")
    agg_fee_data = []
    for s in fee_scenarios:
        r = s["result"]
        if r.aggregator:
            row = {
                fee_type: s["label"],
                "AUM Fees": f"${r.aggregator.total_aum:,.0f}",
                "Promote": f"${r.aggregator.total_promote:,.0f}",
                "Fee Alloc": f"${r.aggregator.fee_allocation:,.0f}",
                "Co-Invest": f"${r.aggregator.coinvest_returns:,.0f}",
                "Total": f"${r.aggregator.grand_total:,.0f}",
            }
            agg_fee_data.append(row)

    st.dataframe(agg_fee_data, use_container_width=True, hide_index=True)

    # Key insight
    if fee_scenarios:
        first = fee_scenarios[0]["result"]
        last = fee_scenarios[-1]["result"]

        # Safe calculation for IRR change
        c_lp_change = None
        if not (math.isinf(first.c_lp_irr) or math.isnan(first.c_lp_irr) or
                math.isinf(last.c_lp_irr) or math.isnan(last.c_lp_irr)):
            c_lp_change = (last.c_lp_irr - first.c_lp_irr) * 100

        agg_change = (last.aggregator.grand_total - first.aggregator.grand_total) if (first.aggregator and last.aggregator) else 0

        c_lp_text = f"{c_lp_change:+.0f}" if c_lp_change is not None else "N/A"
        insight_text = 'Higher fees benefit Aggregator but reduce LP returns' if (agg_change > 0 and c_lp_change is not None and c_lp_change < 0) else 'Fee structure impacts both parties'

        st.info(f"""
        **Fee Sensitivity Summary:**
        - C-Fund LP IRR change across range: **{c_lp_text} bps**
        - Aggregator income change: **${agg_change:+,.0f}**
        - {insight_text}
        """)

elif scenario_type == "Breakeven":
    st.subheader("Breakeven Analysis")

    st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:1rem; margin-bottom:1.5rem;">
<strong style="color:#4cc9f0;">Breakeven Points</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
Find the threshold where each stakeholder's returns hit critical levels (0% IRR, hurdle rate, etc.)
</div>
</div>""", unsafe_allow_html=True)

    # Run scenarios across timing range to find breakeven
    timing_range = list(range(12, 61, 3))

    # Calculate for each timing
    breakeven_data = []
    b_hurdle = p.get('b_hurdle', 0.08)
    c_hurdle = p.get('c_hurdle', 0.10)

    for month in timing_range:
        scenario = Scenario(
            name=f"{month}mo",
            exit_month=month,
            has_extension=month > deal.term_months,
            sofr_shift=0,
        )
        result = run_scenario(deal, scenario, sofr_curve, is_principal)

        breakeven_data.append({
            "month": month,
            "b_lp_irr": result.b_lp_irr,
            "c_lp_irr": result.c_lp_irr,
            "b_gross_irr": result.b_irr,
            "c_gross_irr": result.c_irr,
            "agg_total": result.aggregator.grand_total if result.aggregator else 0,
        })

    # Find breakeven months
    def find_breakeven(data, key, target):
        for i, d in enumerate(data):
            if d[key] <= target:
                if i == 0:
                    return data[0]["month"]
                # Interpolate
                prev = data[i-1]
                curr = d
                if prev[key] != curr[key]:
                    ratio = (prev[key] - target) / (prev[key] - curr[key])
                    return prev["month"] + ratio * (curr["month"] - prev["month"])
                return curr["month"]
        return None

    b_lp_breakeven_0 = find_breakeven(breakeven_data, "b_lp_irr", 0)
    c_lp_breakeven_0 = find_breakeven(breakeven_data, "c_lp_irr", 0)
    b_lp_breakeven_hurdle = find_breakeven(breakeven_data, "b_lp_irr", b_hurdle)
    c_lp_breakeven_hurdle = find_breakeven(breakeven_data, "c_lp_irr", c_hurdle)

    # Display breakeven summary
    st.markdown("##### Breakeven Points by Exit Month")

    be1, be2, be3, be4 = st.columns(4)

    with be1:
        val = f"{b_lp_breakeven_hurdle:.0f}mo" if b_lp_breakeven_hurdle else ">60mo"
        st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#ffa15a; font-weight:600; font-size:0.85rem;">B-Fund LP Hurdle</div>
<div style="color:#78909c; font-size:0.7rem;">Below {b_hurdle*100:.0f}% IRR at</div>
<div style="color:#ffa15a; font-size:1.5rem; font-weight:700;">{val}</div>
</div>""", unsafe_allow_html=True)

    with be2:
        val = f"{b_lp_breakeven_0:.0f}mo" if b_lp_breakeven_0 else ">60mo"
        st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#ffa15a; font-weight:600; font-size:0.85rem;">B-Fund LP Zero</div>
<div style="color:#78909c; font-size:0.7rem;">0% IRR at</div>
<div style="color:#ffa15a; font-size:1.5rem; font-weight:700;">{val}</div>
</div>""", unsafe_allow_html=True)

    with be3:
        val = f"{c_lp_breakeven_hurdle:.0f}mo" if c_lp_breakeven_hurdle else ">60mo"
        st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#ef553b; font-weight:600; font-size:0.85rem;">C-Fund LP Hurdle</div>
<div style="color:#78909c; font-size:0.7rem;">Below {c_hurdle*100:.0f}% IRR at</div>
<div style="color:#ef553b; font-size:1.5rem; font-weight:700;">{val}</div>
</div>""", unsafe_allow_html=True)

    with be4:
        val = f"{c_lp_breakeven_0:.0f}mo" if c_lp_breakeven_0 else ">60mo"
        st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#ef553b; font-weight:600; font-size:0.85rem;">C-Fund LP Zero</div>
<div style="color:#78909c; font-size:0.7rem;">0% IRR at</div>
<div style="color:#ef553b; font-size:1.5rem; font-weight:700;">{val}</div>
</div>""", unsafe_allow_html=True)

    st.divider()

    # IRR curve chart
    st.markdown("##### LP IRR by Exit Month")

    fig = go.Figure()

    # B-Fund LP
    fig.add_trace(go.Scatter(
        x=[d["month"] for d in breakeven_data],
        y=[d["b_lp_irr"] * 100 for d in breakeven_data],
        mode='lines+markers',
        name='B-Fund LP',
        line=dict(color='#ffa15a', width=2),
    ))

    # C-Fund LP
    fig.add_trace(go.Scatter(
        x=[d["month"] for d in breakeven_data],
        y=[d["c_lp_irr"] * 100 for d in breakeven_data],
        mode='lines+markers',
        name='C-Fund LP',
        line=dict(color='#ef553b', width=2),
    ))

    # Hurdle lines
    fig.add_hline(y=b_hurdle * 100, line_dash="dash", line_color="#ffa15a", opacity=0.5,
                  annotation_text=f"B Hurdle ({b_hurdle*100:.0f}%)")
    fig.add_hline(y=c_hurdle * 100, line_dash="dash", line_color="#ef553b", opacity=0.5,
                  annotation_text=f"C Hurdle ({c_hurdle*100:.0f}%)")
    fig.add_hline(y=0, line_dash="dot", line_color="#78909c", opacity=0.5,
                  annotation_text="Breakeven (0%)")

    fig.update_layout(
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#b0bec5'},
        xaxis={'title': 'Exit Month', 'gridcolor': 'rgba(76,201,240,0.1)'},
        yaxis={'title': 'IRR (%)', 'gridcolor': 'rgba(76,201,240,0.1)'},
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Aggregator income curve
    st.markdown("##### Aggregator Income by Exit Month")

    fig2 = go.Figure()

    fig2.add_trace(go.Scatter(
        x=[d["month"] for d in breakeven_data],
        y=[d["agg_total"] for d in breakeven_data],
        mode='lines+markers',
        name='Aggregator Total',
        line=dict(color='#06ffa5', width=2),
        fill='tozeroy',
        fillcolor='rgba(6,255,165,0.1)',
    ))

    fig2.update_layout(
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#b0bec5'},
        xaxis={'title': 'Exit Month', 'gridcolor': 'rgba(76,201,240,0.1)'},
        yaxis={'title': 'Total Income ($)', 'gridcolor': 'rgba(76,201,240,0.1)', 'tickformat': '$,.0f'},
        showlegend=False,
    )

    st.plotly_chart(fig2, use_container_width=True)

    # Key insight
    c_be_text = f"{c_lp_breakeven_hurdle:.0f}mo" if c_lp_breakeven_hurdle else ">60mo"
    b_be_text = f"{b_lp_breakeven_hurdle:.0f}mo" if b_lp_breakeven_hurdle else ">60mo"
    st.info(f"""
    **Breakeven Summary:**
    - C-Fund LP hits hurdle ({c_hurdle*100:.0f}%) at **{c_be_text}** — delays beyond this trigger promote
    - B-Fund LP hits hurdle ({b_hurdle*100:.0f}%) at **{b_be_text}** — delays beyond this trigger promote
    - Longer holds benefit Aggregator (more AUM fees) but hurt LPs
    """)

elif scenario_type == "Custom":
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

    # Gross Tranche Returns
    st.markdown("##### Gross Tranche Returns")
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.metric("A-Piece (Bank)", fmt_pct(custom_results.a_irr))
    with g2:
        st.metric("B-Fund Gross", fmt_pct(custom_results.b_irr))
    with g3:
        st.metric("C-Fund Gross", fmt_pct(custom_results.c_irr))
    with g4:
        st.metric("Borrower Cost", fmt_pct(custom_results.borrower_all_in_cost))

    # LP Net Returns
    st.markdown("##### LP Net Returns (After AUM & Promote)")
    lp1, lp2, lp3, lp4 = st.columns(4)
    with lp1:
        st.metric("B-Fund LP IRR", fmt_pct(custom_results.b_lp_irr))
    with lp2:
        st.metric("B-Fund LP MOIC", fmt_moic(custom_results.b_lp_moic))
    with lp3:
        st.metric("C-Fund LP IRR", fmt_pct(custom_results.c_lp_irr))
    with lp4:
        st.metric("C-Fund LP MOIC", fmt_moic(custom_results.c_lp_moic))

    # Aggregator Economics
    if custom_results.aggregator:
        st.markdown("##### Aggregator Economics")
        agg1, agg2, agg3, agg4, agg5 = st.columns(5)
        with agg1:
            st.metric("Fee Allocation", f"${custom_results.aggregator.fee_allocation:,.0f}")
        with agg2:
            st.metric("AUM Fees", f"${custom_results.aggregator.total_aum:,.0f}")
        with agg3:
            st.metric("Promote", f"${custom_results.aggregator.total_promote:,.0f}")
        with agg4:
            st.metric("Co-Invest", f"${custom_results.aggregator.coinvest_returns:,.0f}")
        with agg5:
            st.metric("Total", f"${custom_results.aggregator.grand_total:,.0f}")

        # Detailed breakdown
        with st.expander("Aggregator Breakdown"):
            agg_detail = [
                {"Source": "Fee Allocation", "Amount": f"${custom_results.aggregator.fee_allocation:,.0f}", "Timing": "Day 1 + Exit"},
                {"Source": "B-Fund AUM Fee", "Amount": f"${custom_results.aggregator.b_fund_aum:,.0f}", "Timing": f"Monthly ({custom_exit} months)"},
                {"Source": "C-Fund AUM Fee", "Amount": f"${custom_results.aggregator.c_fund_aum:,.0f}", "Timing": f"Monthly ({custom_exit} months)"},
                {"Source": "B-Fund Promote", "Amount": f"${custom_results.aggregator.b_fund_promote:,.0f}", "Timing": "At Exit"},
                {"Source": "C-Fund Promote", "Amount": f"${custom_results.aggregator.c_fund_promote:,.0f}", "Timing": "At Exit"},
                {"Source": "Co-Invest Returns", "Amount": f"${custom_results.aggregator.coinvest_returns:,.0f}", "Timing": "At Exit"},
            ]
            st.dataframe(agg_detail, use_container_width=True, hide_index=True)

    # Comparison with base case
    if results:
        st.markdown("##### Comparison to Base Case")
        base_c_lp_irr = st.session_state.get('fund_results', {}).get('C_fund')
        base_c_lp_irr = base_c_lp_irr.lp_cashflows.irr if base_c_lp_irr else 0

        irr_delta = custom_results.c_lp_irr - base_c_lp_irr
        if not math.isinf(irr_delta) and not math.isnan(irr_delta):
            delta_color = "#06ffa5" if irr_delta >= 0 else "#ef553b"
            st.markdown(f"""
            **C-Fund LP IRR Change vs Base ({p['hud_month']}mo exit):**
            <span style="color:{delta_color}; font-weight:600;">{irr_delta*100:+.0f} bps</span>
            (Base: {fmt_pct(base_c_lp_irr)} → Custom: {fmt_pct(custom_results.c_lp_irr)})
            """, unsafe_allow_html=True)

st.divider()
st.caption("HUD Financing Platform | Scenario Analysis")
