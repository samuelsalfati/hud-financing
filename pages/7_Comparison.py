"""
Comparison Page - Side-by-side deal analysis
"""
import streamlit as st
import pandas as pd
import math
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from components.charts import create_grouped_bar_chart, create_comparison_bar
from engine.deal import Deal, Tranche, TrancheType, RateType, FeeStructure
from engine.cashflows import generate_cashflows

# Page config
st.set_page_config(
    page_title="Comparison | HUD Financing",
    page_icon="⚖️",
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
is_principal = p.get('is_principal', True)


def fmt_pct(val):
    """Format percentage, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.1%}"


def fmt_moic(val):
    """Format MOIC, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.2f}x"


# Header
st.markdown(page_header(
    "Deal Comparison",
    "Compare different deal structures side-by-side"
), unsafe_allow_html=True)

# Deal Summary Bar
role_label = "Principal" if is_principal else "Aggregator"
role_color = "#ef553b" if is_principal else "#06ffa5"
st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
<span style="color:#b0bec5;">Current Deal: <strong style="color:#4cc9f0;">${p['property_value']/1e6:.0f}M @ {p['ltv']:.0%} LTV</strong></span>
<span style="color:#b0bec5;">SOFR: <strong style="color:#06ffa5;">{p['current_sofr']:.2%}</strong></span>
<span style="color:#b0bec5;">Role: <strong style="color:{role_color};">{role_label}</strong></span>
</div>""", unsafe_allow_html=True)

# Purpose explanation
st.markdown("""<div style="background:rgba(6,255,165,0.08); border:1px solid rgba(6,255,165,0.2); border-radius:8px; padding:1rem; margin-bottom:1.5rem;">
<strong style="color:#06ffa5;">📊 Deal Comparison Tool</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
Compare multiple deal structures to find the optimal configuration. Useful for:
<ul style="margin:0.5rem 0 0 1rem; padding:0;">
<li>Testing different <strong>LTV levels</strong> (higher LTV = more leverage but lower IRR)</li>
<li>Comparing <strong>tranche structures</strong> (A/B/C splits)</li>
<li>Evaluating <strong>different properties</strong> or deal sizes</li>
<li>Sensitivity to <strong>SOFR assumptions</strong></li>
</ul>
</div>
</div>""", unsafe_allow_html=True)

# Initialize session state for deals
if "comparison_deals" not in st.session_state:
    st.session_state.comparison_deals = {}

# Auto-add current deal if comparison is empty and deal exists
if len(st.session_state.comparison_deals) == 0 and deal and results:
    deal_name = f"Current Deal (${p['property_value']/1e6:.0f}M)"
    st.session_state.comparison_deals[deal_name] = {
        "deal": deal,
        "sofr": p['current_sofr'],
        "results": results,
        "is_principal": is_principal,
    }

st.divider()

# Template deals
DEAL_TEMPLATES = {
    "Conservative": {
        "description": "Lower leverage, safer structure",
        "ltv": 0.75,
        "a_pct": 0.75,
        "b_pct": 0.15,
        "borrower_spread": 0.045,
        "origination_fee": 0.0125,
        "hud_month": 24,
    },
    "Market Standard": {
        "description": "Typical market terms",
        "ltv": 0.80,
        "a_pct": 0.70,
        "b_pct": 0.20,
        "borrower_spread": 0.04,
        "origination_fee": 0.01,
        "hud_month": 24,
    },
    "Aggressive": {
        "description": "Higher leverage, max returns",
        "ltv": 0.85,
        "a_pct": 0.65,
        "b_pct": 0.25,
        "borrower_spread": 0.035,
        "origination_fee": 0.0075,
        "hud_month": 18,
    },
    "Large SNF Portfolio": {
        "description": "$200M+ portfolio deal",
        "ltv": 0.80,
        "a_pct": 0.72,
        "b_pct": 0.18,
        "borrower_spread": 0.0375,
        "origination_fee": 0.0075,
        "hud_month": 30,
        "property_value": 250_000_000,
    },
}

# Quick add templates
st.subheader("⚡ Quick Add Template")

template_cols = st.columns(len(DEAL_TEMPLATES))
for i, (template_name, template) in enumerate(DEAL_TEMPLATES.items()):
    with template_cols[i]:
        c_pct_display = 1 - template['a_pct'] - template['b_pct']

        st.markdown(f"""<div style="background:rgba(76,201,240,0.08); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem; margin-bottom:0.5rem;">
        <strong style="color:#4cc9f0; font-size:0.95rem;">{template_name}</strong>
        <div style="color:#b0bec5; font-size:0.8rem; margin:0.3rem 0;">{template["description"]}</div>
        <div style="color:#e0e0e0; font-size:0.75rem; line-height:1.4;">
        <strong>LTV:</strong> {template['ltv']:.0%}<br>
        <strong>Stack:</strong> {template['a_pct']:.0%}/{template['b_pct']:.0%}/{c_pct_display:.0%}<br>
        <strong>Spread:</strong> {template['borrower_spread']*100:.2f}%<br>
        <strong>Fee:</strong> {template['origination_fee']*100:.2f}%
        </div>
        </div>""", unsafe_allow_html=True)

        if st.button(f"➕ Add", key=f"template_{template_name}", use_container_width=True):
            prop_val = template.get("property_value", p['property_value'])
            ltv_val = template["ltv"]
            loan_amt = prop_val * ltv_val
            c_pct = 1 - template["a_pct"] - template["b_pct"]

            template_deal = Deal(
                deal_name=template_name,
                property_value=prop_val,
                loan_amount=loan_amt,
                term_months=36,
                expected_hud_month=template["hud_month"],
                tranches=[
                    Tranche(TrancheType.A, template["a_pct"], RateType.FLOATING, 0.02),
                    Tranche(TrancheType.B, template["b_pct"], RateType.FLOATING, 0.06),
                    Tranche(TrancheType.C, c_pct, RateType.FIXED, 0.12),
                ],
                fees=FeeStructure(origination_fee=template["origination_fee"]),
                borrower_spread=template["borrower_spread"],
            )

            sofr_curve = [p['current_sofr']] * 60
            try:
                template_results = generate_cashflows(template_deal, sofr_curve, template["hud_month"], sponsor_is_principal=is_principal)
                st.session_state.comparison_deals[template_name] = {
                    "deal": template_deal,
                    "sofr": p['current_sofr'],
                    "results": template_results,
                    "is_principal": is_principal,
                }
                st.rerun()
            except Exception as e:
                st.error(f"Error: {str(e)}")

st.divider()

# Deal input section
st.subheader("➕ Custom Deal Variant")

with st.expander("Create Custom Deal", expanded=len(st.session_state.comparison_deals) < 2):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Deal Basics**")
        deal_name = st.text_input("Deal Name", value=f"Variant {len(st.session_state.comparison_deals) + 1}")
        property_value = st.number_input("Property Value ($)", value=int(p['property_value']), step=5_000_000)
        ltv = st.number_input(
            "LTV (%)", min_value=60.0, max_value=90.0, value=p['ltv']*100, step=5.0, format="%.0f", key="comp_ltv"
        ) / 100
        term_months = st.number_input("Term (months)", min_value=12, max_value=120, value=36, step=6, key="comp_term")
        expected_hud = st.number_input(
            "Expected HUD (month)", min_value=12, max_value=120, value=p['hud_month'], step=1, key="comp_hud"
        )

    with col2:
        st.markdown("**Rates & Fees**")
        comp_sofr = st.number_input(
            "SOFR (%)", min_value=1.0, max_value=10.0, value=p['current_sofr']*100, step=0.25, format="%.2f", key="comp_sofr"
        ) / 100
        borrower_spread = st.number_input(
            "Borrower Spread (%)", min_value=1.0, max_value=10.0, value=4.00, step=0.25, format="%.2f", key="comp_bspread"
        ) / 100
        origination_fee = st.number_input(
            "Origination Fee (%)", min_value=0.5, max_value=3.0, value=1.0, step=0.25, format="%.2f", key="comp_orig"
        ) / 100
        comp_is_principal = st.radio(
            "Role", ["Principal", "Aggregator"], horizontal=True, key="comp_role"
        ) == "Principal"

    with col3:
        st.markdown("**Capital Stack**")
        a_pct = st.number_input(
            "A-Piece %", min_value=50.0, max_value=85.0, value=70.0, step=5.0, format="%.0f", key="comp_a"
        ) / 100
        b_pct = st.number_input(
            "B-Piece %", min_value=5.0, max_value=40.0, value=20.0, step=5.0, format="%.0f", key="comp_b"
        ) / 100
        c_pct = 1 - a_pct - b_pct
        st.markdown(f"**C-Piece: {c_pct:.0%}** (calculated)")

        if c_pct < 0.05:
            st.warning("C-Piece too small!")
        elif c_pct > 0.30:
            st.warning("C-Piece unusually large")

    add_col1, add_col2 = st.columns([1, 3])
    with add_col1:
        add_button = st.button("➕ Add to Comparison", type="primary", use_container_width=True)

    if add_button:
        if c_pct < 0.01:
            st.error("Invalid capital stack - C-Piece must be positive")
        else:
            loan_amount = property_value * ltv

            new_deal = Deal(
                deal_name=deal_name,
                property_value=property_value,
                loan_amount=loan_amount,
                term_months=term_months,
                expected_hud_month=expected_hud,
                tranches=[
                    Tranche(TrancheType.A, a_pct, RateType.FLOATING, 0.02),
                    Tranche(TrancheType.B, b_pct, RateType.FLOATING, 0.06),
                    Tranche(TrancheType.C, c_pct, RateType.FIXED, 0.12),
                ],
                fees=FeeStructure(origination_fee=origination_fee),
                borrower_spread=borrower_spread,
            )

            sofr_curve = [comp_sofr] * 60
            try:
                new_results = generate_cashflows(new_deal, sofr_curve, expected_hud, sponsor_is_principal=comp_is_principal)

                st.session_state.comparison_deals[deal_name] = {
                    "deal": new_deal,
                    "sofr": comp_sofr,
                    "results": new_results,
                    "is_principal": comp_is_principal,
                }
                st.success(f"Added {deal_name} to comparison")
                st.rerun()
            except Exception as e:
                st.error(f"Error creating deal: {str(e)}")

st.divider()

# Display comparison
if st.session_state.comparison_deals:
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.subheader(f"📊 Comparing {len(st.session_state.comparison_deals)} Deal{'s' if len(st.session_state.comparison_deals) > 1 else ''}")
    with header_col2:
        if st.button("🗑️ Clear All", use_container_width=True):
            st.session_state.comparison_deals = {}
            st.rerun()

    # Build comparison data
    comparison_data = []
    deal_names = list(st.session_state.comparison_deals.keys())

    for name, data in st.session_state.comparison_deals.items():
        comp_deal = data["deal"]
        comp_results = data["results"]
        sponsor = comp_results.get("sponsor")
        deal_is_principal = data.get("is_principal", True)
        role = "Principal" if deal_is_principal else "Aggregator"

        row = {
            "Deal": name,
            "Role": role,
            "Property": f"${comp_deal.property_value/1e6:.0f}M",
            "LTV": f"{comp_deal.ltv:.0%}",
            "HUD Mo": comp_deal.expected_hud_month,
            "SOFR": f"{data['sofr']:.2%}",
        }

        if sponsor:
            row["Sponsor IRR"] = fmt_pct(sponsor.irr)
            if deal_is_principal:
                row["MOIC"] = fmt_moic(sponsor.moic)
            row["Profit"] = f"${sponsor.total_profit:,.0f}"
        else:
            row["Sponsor IRR"] = "N/A"
            if deal_is_principal:
                row["MOIC"] = "N/A"
            row["Profit"] = "N/A"

        comparison_data.append(row)

    # Comparison table
    st.dataframe(comparison_data, use_container_width=True, hide_index=True)

    # Individual deal removal
    if len(st.session_state.comparison_deals) > 1:
        remove_deal = st.selectbox(
            "Remove a deal:",
            options=[""] + deal_names,
            key="remove_deal_select"
        )
        if remove_deal and st.button(f"Remove '{remove_deal}'"):
            del st.session_state.comparison_deals[remove_deal]
            st.rerun()

    st.divider()

    # Visual comparisons - only show if more than 1 deal
    if len(st.session_state.comparison_deals) >= 2:
        col1, col2 = st.columns(2)

        with col1:
            # IRR comparison
            irrs = []
            for name, data in st.session_state.comparison_deals.items():
                sponsor = data["results"].get("sponsor")
                irr_val = sponsor.irr if sponsor else 0
                # Handle inf/nan for chart
                if math.isinf(irr_val) or math.isnan(irr_val):
                    irr_val = 0
                irrs.append(irr_val)

            fig = create_comparison_bar(
                items=deal_names,
                values=irrs,
                title="Sponsor IRR Comparison",
                value_format="{:.1%}",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Profit comparison
            profits = []
            for name, data in st.session_state.comparison_deals.items():
                sponsor = data["results"].get("sponsor")
                profit_val = sponsor.total_profit if sponsor else 0
                if math.isinf(profit_val) or math.isnan(profit_val):
                    profit_val = 0
                profits.append(profit_val)

            fig = create_comparison_bar(
                items=deal_names,
                values=profits,
                title="Total Profit Comparison",
                value_format="${:,.0f}",
                color_by_value=False,
            )
            st.plotly_chart(fig, use_container_width=True)

        # Tranche comparison
        st.subheader("Tranche Returns Comparison")

        tranche_irrs = {"A-Piece": [], "B-Piece": [], "C-Piece": []}
        for name, data in st.session_state.comparison_deals.items():
            for tranche, label in [("A", "A-Piece"), ("B", "B-Piece"), ("C", "C-Piece")]:
                t_result = data["results"].get(tranche)
                irr_val = t_result.irr * 100 if t_result else 0
                if math.isinf(irr_val) or math.isnan(irr_val):
                    irr_val = 0
                tranche_irrs[label].append(irr_val)

        fig = create_grouped_bar_chart(
            categories=deal_names,
            groups=tranche_irrs,
            title="Tranche IRR Comparison (%)",
            y_title="IRR (%)",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Winner analysis
        st.subheader("📈 Analysis")

        # Find best by IRR (only considering valid IRRs)
        valid_deals = [
            (name, data) for name, data in st.session_state.comparison_deals.items()
            if data["results"].get("sponsor") and not math.isinf(data["results"]["sponsor"].irr) and not math.isnan(data["results"]["sponsor"].irr)
        ]

        if valid_deals:
            # Sort by IRR
            sorted_by_irr = sorted(valid_deals, key=lambda x: x[1]["results"]["sponsor"].irr, reverse=True)
            # Sort by profit
            sorted_by_profit = sorted(valid_deals, key=lambda x: x[1]["results"]["sponsor"].total_profit, reverse=True)

            best_irr_name, best_irr_data = sorted_by_irr[0]
            best_profit_name, best_profit_data = sorted_by_profit[0]

            # Rankings table
            st.markdown("**Deal Rankings**")
            ranking_data = []
            for rank, (name, data) in enumerate(sorted_by_irr, 1):
                sponsor = data["results"]["sponsor"]
                deal_obj = data["deal"]
                profit_rank = next(i for i, (n, _) in enumerate(sorted_by_profit, 1) if n == name)

                ranking_data.append({
                    "Rank": f"#{rank}",
                    "Deal": name,
                    "IRR": fmt_pct(sponsor.irr),
                    "Profit": f"${sponsor.total_profit:,.0f}",
                    "Profit Rank": f"#{profit_rank}",
                    "LTV": f"{deal_obj.ltv:.0%}",
                    "C-Piece": f"{deal_obj.tranches[2].percentage:.0%}",
                })

            st.dataframe(ranking_data, use_container_width=True, hide_index=True)

            st.markdown("")

            # Key insights
            analysis_col1, analysis_col2 = st.columns(2)

            with analysis_col1:
                st.markdown(f"""<div style="background:rgba(6,255,165,0.1); border-left:4px solid #06ffa5; padding:1rem; border-radius:0 8px 8px 0; margin-bottom:1rem;">
                <strong style="color:#06ffa5;">🏆 Highest IRR: {best_irr_name}</strong>
                <div style="color:#e0e0e0; font-size:0.9rem; margin-top:0.5rem;">
                {fmt_pct(best_irr_data['results']['sponsor'].irr)} IRR
                </div>
                </div>""", unsafe_allow_html=True)

            with analysis_col2:
                st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border-left:4px solid #4cc9f0; padding:1rem; border-radius:0 8px 8px 0; margin-bottom:1rem;">
                <strong style="color:#4cc9f0;">💰 Highest Profit: {best_profit_name}</strong>
                <div style="color:#e0e0e0; font-size:0.9rem; margin-top:0.5rem;">
                ${best_profit_data['results']['sponsor'].total_profit:,.0f}
                </div>
                </div>""", unsafe_allow_html=True)

            # Trade-off analysis
            if len(valid_deals) >= 2:
                st.markdown("**Trade-off Analysis**")

                # Find extremes for analysis
                lowest_ltv = min(valid_deals, key=lambda x: x[1]["deal"].ltv)
                highest_ltv = max(valid_deals, key=lambda x: x[1]["deal"].ltv)

                insights = []

                # IRR vs Profit trade-off
                if best_irr_name != best_profit_name:
                    irr_diff = best_irr_data['results']['sponsor'].irr - best_profit_data['results']['sponsor'].irr
                    profit_diff = best_profit_data['results']['sponsor'].total_profit - best_irr_data['results']['sponsor'].total_profit
                    insights.append(f"**IRR vs Profit trade-off:** {best_irr_name} has higher IRR (+{irr_diff*100:.0f} bps) but {best_profit_name} generates more profit (+${profit_diff:,.0f})")

                # LTV analysis
                if lowest_ltv[0] != highest_ltv[0]:
                    low_name, low_data = lowest_ltv
                    high_name, high_data = highest_ltv
                    ltv_diff = high_data["deal"].ltv - low_data["deal"].ltv
                    irr_impact = high_data["results"]["sponsor"].irr - low_data["results"]["sponsor"].irr

                    if irr_impact > 0:
                        insights.append(f"**Leverage effect:** {high_name} ({high_data['deal'].ltv:.0%} LTV) outperforms {low_name} ({low_data['deal'].ltv:.0%} LTV) by {irr_impact*100:.0f} bps — higher leverage is paying off")
                    else:
                        insights.append(f"**Leverage penalty:** {low_name} ({low_data['deal'].ltv:.0%} LTV) outperforms {high_name} ({high_data['deal'].ltv:.0%} LTV) by {abs(irr_impact)*100:.0f} bps — lower leverage is more efficient")

                # C-piece analysis
                largest_c = max(valid_deals, key=lambda x: x[1]["deal"].tranches[2].percentage)
                smallest_c = min(valid_deals, key=lambda x: x[1]["deal"].tranches[2].percentage)
                if largest_c[0] != smallest_c[0]:
                    c_diff = largest_c[1]["deal"].tranches[2].percentage - smallest_c[1]["deal"].tranches[2].percentage
                    if c_diff > 0.03:  # Only mention if meaningful difference
                        insights.append(f"**Equity exposure:** {largest_c[0]} has {largest_c[1]['deal'].tranches[2].percentage:.0%} C-piece vs {smallest_c[0]} at {smallest_c[1]['deal'].tranches[2].percentage:.0%} — larger C-piece means more skin in the game but higher risk")

                for insight in insights:
                    st.markdown(f"- {insight}")

                # Recommendation
                st.markdown("")
                st.markdown("**Recommendation**")

                if best_irr_name == best_profit_name:
                    st.markdown(f"""<div style="background:rgba(6,255,165,0.15); border:1px solid rgba(6,255,165,0.3); border-radius:8px; padding:1rem;">
                    <strong style="color:#06ffa5;">✅ Clear winner: {best_irr_name}</strong>
                    <div style="color:#e0e0e0; font-size:0.9rem; margin-top:0.5rem;">
                    This deal has both the highest IRR and highest absolute profit. No trade-offs required.
                    </div>
                    </div>""", unsafe_allow_html=True)
                else:
                    st.markdown(f"""<div style="background:rgba(255,171,0,0.15); border:1px solid rgba(255,171,0,0.3); border-radius:8px; padding:1rem;">
                    <strong style="color:#ffab00;">⚖️ Depends on your priority:</strong>
                    <div style="color:#e0e0e0; font-size:0.9rem; margin-top:0.5rem;">
                    • <strong>Maximize returns on capital:</strong> Choose <strong>{best_irr_name}</strong> ({fmt_pct(best_irr_data['results']['sponsor'].irr)} IRR)<br>
                    • <strong>Maximize absolute dollars:</strong> Choose <strong>{best_profit_name}</strong> (${best_profit_data['results']['sponsor'].total_profit:,.0f} profit)
                    </div>
                    </div>""", unsafe_allow_html=True)

    else:
        st.info("➕ Add at least one more deal variant above to see comparison charts")

else:
    st.info("Your current deal has been added. Create deal variants above to compare different structures.")

st.divider()
st.caption("HUD Financing Platform | Deal Comparison")
