"""
Export Center Page - Excel download and deal save/load
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from engine.deal import Deal, Tranche, TrancheType, RateType, FeeStructure
from engine.cashflows import generate_cashflows
from engine.scenarios import get_standard_scenarios, run_scenarios

# Page config
st.set_page_config(
    page_title="Export Center | HUD Financing",
    page_icon="📥",
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

# Build SOFR curve from session state
sofr_curve = [p['current_sofr']] * 60

# Header
st.markdown(page_header(
    "Export Center",
    "Download reports and save deal configurations"
), unsafe_allow_html=True)

# Deal Summary Bar
st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
<span style="color:#b0bec5;">Property: <strong style="color:#4cc9f0;">${p['property_value']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">Loan: <strong style="color:#4cc9f0;">${p['loan_amount']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">LTV: <strong style="color:#4cc9f0;">{p['ltv']:.0%}</strong></span>
<span style="color:#b0bec5;">Term: <strong style="color:#4cc9f0;">{p['term_months']}mo</strong></span>
<span style="color:#b0bec5;">SOFR: <strong style="color:#06ffa5;">{p['current_sofr']:.2%}</strong></span>
</div>""", unsafe_allow_html=True)

# Deal naming
st.subheader("Deal Information")

col1, col2 = st.columns(2)

with col1:
    deal_name = st.text_input(
        "Deal Name",
        value=st.session_state.get("deal_name", "HUD Bridge Deal"),
        key="deal_name_input",
    )
    st.session_state.deal_name = deal_name
    if deal:
        deal.deal_name = deal_name

with col2:
    property_address = st.text_input(
        "Property Address (Optional)",
        value="",
    )
    if deal:
        deal.property_address = property_address

st.divider()

# Export Options
st.subheader("Export Options")

col1, col2, col3 = st.columns(3)

# CSV Export
with col1:
    st.markdown("### Cashflow Export")
    st.markdown("Download monthly cashflows as CSV")

    export_view = st.selectbox(
        "Select View",
        ["Sponsor", "A-Piece", "B-Piece", "C-Piece", "All Tranches"],
    )

    if results:
        if export_view == "All Tranches":
            # Combine all tranches
            sponsor = results.get("sponsor")
            df = pd.DataFrame({
                "Month": sponsor.months if sponsor else [],
            })

            for name, key in [("Sponsor", "sponsor"), ("A", "A"), ("B", "B"), ("C", "C")]:
                cf = results.get(key)
                if cf:
                    df[f"{name}_Principal"] = cf.principal_flows
                    df[f"{name}_Interest"] = cf.interest_flows
                    df[f"{name}_Fees"] = cf.fee_flows
                    df[f"{name}_Net"] = cf.total_flows

            csv = df.to_csv(index=False)
            filename = f"{deal_name.replace(' ', '_')}_all_cashflows.csv"

        else:
            key_map = {"Sponsor": "sponsor", "A-Piece": "A", "B-Piece": "B", "C-Piece": "C"}
            key = key_map[export_view]
            cf = results.get(key)

            if cf:
                df = pd.DataFrame({
                    "Month": cf.months,
                    "Principal": cf.principal_flows,
                    "Interest": cf.interest_flows,
                    "Fees": cf.fee_flows,
                    "Net_Cashflow": cf.total_flows,
                })
                csv = df.to_csv(index=False)
                filename = f"{deal_name.replace(' ', '_')}_{export_view.replace('-', '').lower()}_cashflows.csv"
            else:
                csv = ""
                filename = "error.csv"

        st.download_button(
            label="Download Cashflows (CSV)",
            data=csv,
            file_name=filename,
            mime="text/csv",
        )
    else:
        st.info("Configure a deal to export cashflows")

# JSON Export
with col2:
    st.markdown("### Deal Configuration")
    st.markdown("Save deal parameters as JSON")

    if deal:
        deal_json = json.dumps(deal.to_dict(), indent=2)

        st.download_button(
            label="Download Deal Config (JSON)",
            data=deal_json,
            file_name=f"{deal_name.replace(' ', '_')}_config.json",
            mime="application/json",
        )

        # Save to local storage
        if st.button("Save to Library"):
            save_path = Path(__file__).parent.parent / "data" / "saved_deals"
            save_path.mkdir(parents=True, exist_ok=True)

            filepath = save_path / f"{deal_name.replace(' ', '_')}.json"
            deal.save_to_file(str(filepath))

            st.success(f"Saved to {filepath.name}")
    else:
        st.info("Configure a deal to export configuration")

# Summary Report
with col3:
    st.markdown("### Summary Report")
    st.markdown("Download executive summary")

    if results:
        sponsor = results.get("sponsor")

        # Build summary text
        summary = f"""
HUD FINANCING PLATFORM
DEAL SUMMARY REPORT
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}

{'='*50}
DEAL OVERVIEW
{'='*50}

Deal Name: {deal_name}
Property Address: {property_address or 'Not specified'}

Property Value: ${p['property_value']:,.0f}
Loan Amount: ${p['loan_amount']:,.0f}
LTV: {p['ltv']:.0%}
Term: {p['term_months']} months
Expected HUD: Month {p['hud_month']}

{'='*50}
PRICING
{'='*50}

Current SOFR: {p['current_sofr']:.2%}
Borrower Rate: {p['borrower_rate']:.2%}
Origination Fee: {p['orig_fee']:.2%}
Exit Fee: {p['exit_fee']:.2%}

{'='*50}
CAPITAL STACK
{'='*50}

A-Piece: {p['a_pct']:.0%} (${p['loan_amount'] * p['a_pct']:,.0f})
B-Piece: {p['b_pct']:.0%} (${p['loan_amount'] * p['b_pct']:,.0f})
C-Piece: {p['c_pct']:.0%} (${p['loan_amount'] * p['c_pct']:,.0f})

{'='*50}
KEY METRICS
{'='*50}

Sponsor IRR: {sponsor.irr:.1%}
Sponsor MOIC: {sponsor.moic:.2f}x
Total Profit: ${sponsor.total_profit:,.0f}

Blended Cost of Capital: {deal.get_blended_cost_of_capital(p['current_sofr']):.2%}
Spread Capture: {p['borrower_rate'] - deal.get_blended_cost_of_capital(p['current_sofr']):.2%}

{'='*50}
TRANCHE RETURNS
{'='*50}
""" if sponsor and deal else "Error generating summary"

        for name, key in [("A-Piece", "A"), ("B-Piece", "B"), ("C-Piece", "C")]:
            cf = results.get(key)
            if cf:
                summary += f"\n{name}: IRR {cf.irr:.1%}, MOIC {cf.moic:.2f}x"

        summary += f"""

{'='*50}
DISCLAIMER
{'='*50}

This analysis is for informational purposes only and does not constitute
investment advice. Past performance is not indicative of future results.
Actual returns may vary based on market conditions and timing.

Generated by HUD Financing Platform
"""

        st.download_button(
            label="Download Summary (TXT)",
            data=summary,
            file_name=f"{deal_name.replace(' ', '_')}_summary.txt",
            mime="text/plain",
        )
    else:
        st.info("Configure a deal to export summary")

st.divider()

# Scenario Export
st.subheader("Scenario Analysis Export")

if deal:
    scenarios = get_standard_scenarios(deal)
    scenario_results = run_scenarios(deal, scenarios, sofr_curve)

    scenario_df = pd.DataFrame([
        {
            "Scenario": r.scenario.name,
            "Exit_Month": r.scenario.exit_month,
            "Extension": r.scenario.has_extension,
            "Sponsor_IRR": r.sponsor_irr,
            "Sponsor_MOIC": r.sponsor_moic,
            "Sponsor_Profit": r.sponsor_profit,
            "A_IRR": r.a_irr,
            "B_IRR": r.b_irr,
            "C_IRR": r.c_irr,
        }
        for r in scenario_results
    ])

    st.dataframe(scenario_df, use_container_width=True, hide_index=True)

    scenario_csv = scenario_df.to_csv(index=False)
    st.download_button(
        label="Download Scenarios (CSV)",
        data=scenario_csv,
        file_name=f"{deal_name.replace(' ', '_')}_scenarios.csv",
        mime="text/csv",
    )
else:
    st.info("Configure a deal to view scenario analysis")

st.divider()

# Load Deal Section
st.subheader("Load Saved Deal")

saved_path = Path(__file__).parent.parent / "data" / "saved_deals"
if saved_path.exists():
    saved_files = list(saved_path.glob("*.json"))

    if saved_files:
        selected = st.selectbox(
            "Select saved deal",
            options=[""] + [f.stem for f in saved_files],
        )

        if selected:
            col1, col2 = st.columns(2)

            with col1:
                if st.button("Load Deal"):
                    filepath = saved_path / f"{selected}.json"
                    loaded_deal = Deal.load_from_file(str(filepath))
                    st.success(f"Loaded: {loaded_deal.deal_name}")

                    # Display loaded deal info
                    st.json(loaded_deal.to_dict())

            with col2:
                if st.button("Delete Deal", type="secondary"):
                    filepath = saved_path / f"{selected}.json"
                    filepath.unlink()
                    st.warning(f"Deleted: {selected}")
                    st.rerun()
    else:
        st.info("No saved deals found. Save a deal configuration above.")
else:
    st.info("Save a deal to create the library.")

st.divider()

# Templates section
st.subheader("Deal Templates")

templates_path = Path(__file__).parent.parent / "data" / "templates" / "deals.json"

if templates_path.exists():
    with open(templates_path) as f:
        templates = json.load(f)

    selected_template = st.selectbox(
        "Load from template",
        options=[""] + list(templates.keys()),
    )

    if selected_template and st.button("Apply Template"):
        template = templates[selected_template]
        st.success(f"Template applied: {selected_template}")
        st.json(template)
else:
    st.info("Deal templates will appear here once created")

st.divider()
st.caption("HUD Financing Platform | Export Center")
