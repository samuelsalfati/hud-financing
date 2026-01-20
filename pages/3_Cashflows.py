"""
Cashflows Page - Monthly cashflow analysis and export
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from components.charts import create_cashflow_chart, create_line_chart, create_area_chart

# Page config
st.set_page_config(
    page_title="Cashflows | HUD Financing",
    page_icon="💰",
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

# Header
st.markdown(page_header(
    "Cashflow Analysis",
    "Monthly cashflows by stakeholder"
), unsafe_allow_html=True)

# Deal Summary Bar
role_label = "Principal" if is_principal else "Aggregator"
role_color = "#ef553b" if is_principal else "#06ffa5"
st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
<span style="color:#b0bec5;">Property: <strong style="color:#4cc9f0;">${p['property_value']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">Loan: <strong style="color:#4cc9f0;">${p['loan_amount']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">LTV: <strong style="color:#4cc9f0;">{p['ltv']:.0%}</strong></span>
<span style="color:#b0bec5;">Term: <strong style="color:#4cc9f0;">{p['term_months']}mo</strong></span>
<span style="color:#b0bec5;">SOFR: <strong style="color:#06ffa5;">{p['current_sofr']:.2%}</strong></span>
<span style="color:#b0bec5;">Role: <strong style="color:{role_color};">{role_label}</strong></span>
</div>""", unsafe_allow_html=True)

# Loan Structure Explanation
st.markdown(f"""<div style="background:rgba(6,255,165,0.1); border:1px solid rgba(6,255,165,0.2); border-radius:8px; padding:1rem; margin-bottom:1.5rem;">
<strong style="color:#06ffa5;">Loan Structure: Interest-Only Bridge Loan</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
• <strong>Interest-Only</strong> monthly payments (no amortization)<br>
• <strong>Balloon payment</strong> of full principal at HUD refinancing (Month {p['hud_month']})<br>
• HUD permanent financing pays off the bridge loan in full
</div>
</div>""", unsafe_allow_html=True)

# View selector
view_options = ["Sponsor", "A-Piece", "B-Piece", "C-Piece", "Borrower"]
selected_view = st.radio("Select View", view_options, horizontal=True)

# Map selection to results key
view_key_map = {
    "Sponsor": "sponsor",
    "A-Piece": "A",
    "B-Piece": "B",
    "C-Piece": "C",
    "Borrower": "borrower",
}
view_key = view_key_map[selected_view]
cf_data = results.get(view_key) if results else None

if cf_data:
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("IRR", f"{cf_data.irr:.1%}")
    with col2:
        st.metric("MOIC", f"{cf_data.moic:.2f}x")
    with col3:
        st.metric("Total Profit", f"${cf_data.total_profit:,.0f}")
    with col4:
        initial_investment = abs(cf_data.total_flows[0]) if cf_data.total_flows else 0
        st.metric("Initial Investment", f"${initial_investment:,.0f}")

    st.divider()

    # Cashflow chart
    st.subheader(f"{selected_view} Monthly Cashflows")

    fig = create_cashflow_chart(
        months=cf_data.months,
        principal=cf_data.principal_flows,
        interest=cf_data.interest_flows,
        fees=cf_data.fee_flows,
        title=f"{selected_view} Cashflows",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Cumulative cashflow
    st.subheader("Cumulative Cashflow")

    cumulative = []
    running_total = 0
    for flow in cf_data.total_flows:
        running_total += flow
        cumulative.append(running_total)

    fig = create_line_chart(
        x=cf_data.months,
        y=cumulative,
        name="Cumulative CF",
        title="Cumulative Cashflow Over Time",
        x_title="Month",
        y_title="Cumulative ($)",
        fill=True,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Detailed cashflow table
    st.subheader("Monthly Cashflow Detail")

    df = pd.DataFrame({
        "Month": cf_data.months,
        "Principal": cf_data.principal_flows,
        "Interest": cf_data.interest_flows,
        "Fees": cf_data.fee_flows,
        "Net Cashflow": cf_data.total_flows,
        "Cumulative": cumulative,
    })

    # Format currency columns
    currency_cols = ["Principal", "Interest", "Fees", "Net Cashflow", "Cumulative"]
    styled_df = df.copy()
    for col in currency_cols:
        styled_df[col] = styled_df[col].apply(lambda x: f"${x:,.0f}")

    st.dataframe(styled_df, use_container_width=True, hide_index=True, height=400)

    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Cashflows (CSV)",
        data=csv,
        file_name=f"{selected_view.lower()}_cashflows.csv",
        mime="text/csv",
    )

    st.divider()

    # All stakeholders comparison
    st.subheader("All Stakeholders Comparison")

    st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1rem; margin-bottom:1rem; font-size:0.85rem; color:#b0bec5;">
<strong style="color:#4cc9f0;">Capital Stack:</strong> A-Piece (Senior) + B-Piece (Mezz) + C-Piece (Sponsor Equity) = Total Loan<br>
<strong style="color:#06ffa5;">Sponsor Total:</strong> C-Piece returns + Fees + Spread income
</div>""", unsafe_allow_html=True)

    if results:
        # Build y_dict with available tranches
        y_dict = {}
        if "A" in results:
            y_dict["A-Piece"] = results["A"].total_flows
        if "B" in results:
            y_dict["B-Piece"] = results["B"].total_flows
        if "C" in results:
            y_dict["C-Piece"] = results["C"].total_flows
        y_dict["Sponsor Total"] = results["sponsor"].total_flows

        fig = create_area_chart(
            x=results["sponsor"].months,
            y_dict=y_dict,
            title="Cashflow Comparison by Tranche",
            x_title="Month",
            y_title="Cashflow ($)",
            stacked=False,
        )
        st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("No cashflow data available for this view")

# Summary table
if results:
    st.subheader("Returns Summary")

    summary_rows = []
    for name, key in [("Sponsor", "sponsor"), ("A-Piece", "A"), ("B-Piece", "B"), ("C-Piece", "C")]:
        if key in results:
            r = results[key]
            summary_rows.append({
                "Stakeholder": name,
                "Initial Investment": f"${abs(r.total_flows[0]) if r.total_flows else 0:,.0f}",
                "Total Returns": f"${sum(f for f in r.total_flows if f > 0):,.0f}",
                "Net Profit": f"${r.total_profit:,.0f}",
                "IRR": f"{r.irr:.1%}",
                "MOIC": f"{r.moic:.2f}x",
            })

    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

st.divider()
st.caption("HUD Financing Platform | Cashflow Analysis")
