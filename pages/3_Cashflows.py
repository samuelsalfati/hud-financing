"""
Cashflows Page - Monthly cashflow analysis and export
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
from components.charts import create_cashflow_chart, create_line_chart, create_area_chart

# Helper functions for safe formatting
def safe_pct(val, decimals=1):
    """Format percentage, handling inf/nan and large values"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    # For large percentages (100%+), use comma formatting
    if abs(val) >= 1.0:
        return f"{val*100:,.{decimals}f}%"
    return f"{val:.{decimals}%}"

def safe_moic(val):
    """Format MOIC, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.2f}x"

def safe_currency(val):
    """Format currency, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"${val:,.0f}"

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
fund_results = st.session_state.get('fund_results')
aggregator_summary = st.session_state.get('aggregator_summary')
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

# View selector - now includes LP views
view_options = ["A-Piece (Bank)", "B-Fund Gross", "B-Fund LP Net", "C-Fund Gross", "C-Fund LP Net", "Aggregator", "Borrower"]
selected_view = st.radio("Select View", view_options, horizontal=True)

# Get cashflow data based on selection
cf_data = None
view_description = ""

if selected_view == "A-Piece (Bank)":
    cf_data = results.get("A") if results else None
    view_description = "Bank investor returns (interest + fee allocation)"
elif selected_view == "B-Fund Gross":
    cf_data = results.get("B") if results else None
    view_description = "B-piece gross returns before management fees"
elif selected_view == "B-Fund LP Net":
    if fund_results and fund_results.get('B_fund'):
        cf_data = fund_results['B_fund'].lp_cashflows
        view_description = "LP returns after AUM fees and promote"
elif selected_view == "C-Fund Gross":
    cf_data = results.get("C") if results else None
    view_description = "C-piece gross returns before management fees"
elif selected_view == "C-Fund LP Net":
    if fund_results and fund_results.get('C_fund'):
        cf_data = fund_results['C_fund'].lp_cashflows
        view_description = "LP returns after AUM fees and promote (excludes co-invest)"
elif selected_view == "Aggregator":
    cf_data = results.get("sponsor") if results else None
    view_description = "Aggregator total returns (co-invest + fees + AUM + promote)"
elif selected_view == "Borrower":
    cf_data = results.get("borrower") if results else None
    view_description = "Borrower perspective (loan received vs payments)"

if view_description:
    st.caption(view_description)

if cf_data:
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("IRR", safe_pct(cf_data.irr))
    with col2:
        st.metric("MOIC", safe_moic(cf_data.moic))
    with col3:
        st.metric("Total Profit", safe_currency(cf_data.total_profit))
    with col4:
        initial_investment = abs(cf_data.total_flows[0]) if cf_data.total_flows else 0
        st.metric("Initial Investment", safe_currency(initial_investment))

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

    # Detailed cashflow table - collapsed for Aggregator (has full breakdown below)
    if selected_view == "Aggregator":
        with st.expander("📋 Basic Cashflow Table (Principal/Interest/Fees)", expanded=False):
            df = pd.DataFrame({
                "Month": cf_data.months,
                "Principal": cf_data.principal_flows,
                "Interest": cf_data.interest_flows,
                "Fees": cf_data.fee_flows,
                "Net Cashflow": cf_data.total_flows,
                "Cumulative": cumulative,
            })
            currency_cols = ["Principal", "Interest", "Fees", "Net Cashflow", "Cumulative"]
            styled_df = df.copy()
            for col in currency_cols:
                styled_df[col] = styled_df[col].apply(lambda x: f"${x:,.0f}")
            st.dataframe(styled_df, use_container_width=True, hide_index=True, height=400)
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Cashflows (CSV)",
                data=csv,
                file_name=f"{selected_view.lower()}_cashflows.csv",
                mime="text/csv",
            )
    else:
        st.subheader("Monthly Cashflow Detail")
        df = pd.DataFrame({
            "Month": cf_data.months,
            "Principal": cf_data.principal_flows,
            "Interest": cf_data.interest_flows,
            "Fees": cf_data.fee_flows,
            "Net Cashflow": cf_data.total_flows,
            "Cumulative": cumulative,
        })
        currency_cols = ["Principal", "Interest", "Fees", "Net Cashflow", "Cumulative"]
        styled_df = df.copy()
        for col in currency_cols:
            styled_df[col] = styled_df[col].apply(lambda x: f"${x:,.0f}")
        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=400)
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download Cashflows (CSV)",
            data=csv,
            file_name=f"{selected_view.lower()}_cashflows.csv",
            mime="text/csv",
        )

    st.divider()

    # =============================================================================
    # FUND ECONOMICS CASHFLOW - Shows AUM fees and promote timing
    # =============================================================================
    if selected_view in ["B-Fund LP Net", "C-Fund LP Net"]:
        st.subheader("Fund Economics Breakdown")

        st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1rem; margin-bottom:1rem; font-size:0.85rem; color:#b0bec5;">
<strong style="color:#4cc9f0;">Fund Economics:</strong> AUM fees are deducted monthly from LP capital. Promote (carry) is calculated and deducted at exit when returns exceed the hurdle rate.
</div>""", unsafe_allow_html=True)

        # Calculate monthly AUM and promote
        hold_months = p['hud_month']
        b_amt = p['loan_amount'] * p['b_pct']
        c_amt = p['loan_amount'] * p['c_pct']
        agg_coinvest = p.get('agg_coinvest', 0)
        c_lp_capital = c_amt * (1 - agg_coinvest)

        b_aum_monthly = b_amt * p.get('b_aum_fee', 0.015) / 12
        c_aum_monthly = c_lp_capital * p.get('c_aum_fee', 0.02) / 12

        b_promote = aggregator_summary.b_fund_promote if aggregator_summary else 0
        c_promote = aggregator_summary.c_fund_promote if aggregator_summary else 0

        # Build economics table for LP views
        econ_rows = []
        for month in range(hold_months + 1):
            row = {"Month": month}

            if selected_view == "B-Fund LP Net":
                row["AUM Fee (Out)"] = -b_aum_monthly if month > 0 and month <= hold_months else 0
                row["Promote (Out)"] = -b_promote if month == hold_months else 0
                row["Total Deductions"] = row["AUM Fee (Out)"] + row["Promote (Out)"]
            elif selected_view == "C-Fund LP Net":
                row["AUM Fee (Out)"] = -c_aum_monthly if month > 0 and month <= hold_months else 0
                row["Promote (Out)"] = -c_promote if month == hold_months else 0
                row["Total Deductions"] = row["AUM Fee (Out)"] + row["Promote (Out)"]

            econ_rows.append(row)

        econ_df = pd.DataFrame(econ_rows)

        # Format and display
        styled_econ = econ_df.copy()
        for col in styled_econ.columns:
            if col != "Month":
                styled_econ[col] = styled_econ[col].apply(lambda x: f"${x:,.0f}" if x >= 0 else f"(${abs(x):,.0f})")

        st.dataframe(styled_econ, use_container_width=True, hide_index=True, height=300)

        # LP view - show what's being deducted
        st.markdown("##### LP Fee Impact")
        if selected_view == "B-Fund LP Net":
            total_aum = b_aum_monthly * hold_months
            promote = b_promote
            fund_name = "B-Fund"
        else:
            total_aum = c_aum_monthly * hold_months
            promote = c_promote
            fund_name = "C-Fund"

        lp1, lp2, lp3 = st.columns(3)
        with lp1:
            st.metric(f"Total AUM Fees", f"(${total_aum:,.0f})", help=f"{hold_months} months of management fees")
        with lp2:
            st.metric(f"Promote/Carry", f"(${promote:,.0f})", help="GP share of profits above hurdle")
        with lp3:
            st.metric(f"Total Deductions", f"(${total_aum + promote:,.0f})", delta=f"-{((total_aum + promote) / (b_amt if 'B' in fund_name else c_lp_capital)) * 100:.1f}% of capital")

        st.divider()

    # =============================================================================
    # AGGREGATOR COMPREHENSIVE MONTHLY TABLE
    # =============================================================================
    if selected_view == "Aggregator":
        st.subheader("Aggregator Monthly Income Breakdown")

        st.markdown("""<div style="background:rgba(6,255,165,0.1); border:1px solid rgba(6,255,165,0.2); border-radius:8px; padding:0.8rem 1rem; margin-bottom:1rem; font-size:0.85rem; color:#b0bec5;">
<strong style="color:#06ffa5;">Complete Aggregator Economics:</strong> This table shows ALL income sources by month - Co-invest cash flows, Fee allocation, AUM fees from both funds, and Promote at exit.
</div>""", unsafe_allow_html=True)

        hold_months = p['hud_month']
        b_amt = p['loan_amount'] * p['b_pct']
        c_amt = p['loan_amount'] * p['c_pct']
        agg_coinvest = p.get('agg_coinvest', 0)
        coinvest_amt = c_amt * agg_coinvest
        c_lp_capital = c_amt * (1 - agg_coinvest)

        # Monthly AUM fees
        b_aum_monthly = b_amt * p.get('b_aum_fee', 0.015) / 12
        c_aum_monthly = c_lp_capital * p.get('c_aum_fee', 0.02) / 12

        # Fee allocation
        orig_fee_total = p['loan_amount'] * p['orig_fee'] * p['agg_fee_alloc']
        exit_fee_total = p['loan_amount'] * p['exit_fee'] * p['agg_fee_alloc']

        # Promote
        b_promote = aggregator_summary.b_fund_promote if aggregator_summary else 0
        c_promote = aggregator_summary.c_fund_promote if aggregator_summary else 0

        # Co-invest monthly interest (C-piece earns the C spread on SOFR)
        c_spread = p.get('c_target', 0.12) - p.get('current_sofr', 0.043) if p.get('c_target', 0) > p.get('current_sofr', 0) else 0.08
        coinvest_monthly_interest = coinvest_amt * (p.get('current_sofr', 0.043) + c_spread) / 12

        # Build comprehensive table
        agg_rows = []
        running_total = 0

        for month in range(hold_months + 1):
            row = {"Month": month}

            # Co-invest flows
            if month == 0:
                row["Co-Invest Principal"] = -coinvest_amt
                row["Co-Invest Interest"] = 0
            elif month == hold_months:
                row["Co-Invest Principal"] = coinvest_amt  # Principal returned
                row["Co-Invest Interest"] = coinvest_monthly_interest
            else:
                row["Co-Invest Principal"] = 0
                row["Co-Invest Interest"] = coinvest_monthly_interest

            # Fee allocation
            if month == 1:
                row["Origination Fee"] = orig_fee_total
            else:
                row["Origination Fee"] = 0

            if month == hold_months:
                row["Exit Fee"] = exit_fee_total
            else:
                row["Exit Fee"] = 0

            # AUM fees
            if month > 0 and month <= hold_months:
                row["B-Fund AUM"] = b_aum_monthly
                row["C-Fund AUM"] = c_aum_monthly
            else:
                row["B-Fund AUM"] = 0
                row["C-Fund AUM"] = 0

            # Promote at exit
            if month == hold_months:
                row["B-Fund Promote"] = b_promote
                row["C-Fund Promote"] = c_promote
            else:
                row["B-Fund Promote"] = 0
                row["C-Fund Promote"] = 0

            # Total for month
            row["Monthly Total"] = (
                row["Co-Invest Principal"] + row["Co-Invest Interest"] +
                row["Origination Fee"] + row["Exit Fee"] +
                row["B-Fund AUM"] + row["C-Fund AUM"] +
                row["B-Fund Promote"] + row["C-Fund Promote"]
            )

            running_total += row["Monthly Total"]
            row["Cumulative"] = running_total

            agg_rows.append(row)

        agg_df = pd.DataFrame(agg_rows)

        # Format and display in collapsible expander
        styled_agg = agg_df.copy()
        for col in styled_agg.columns:
            if col != "Month":
                styled_agg[col] = styled_agg[col].apply(lambda x: f"${x:,.0f}" if x >= 0 else f"(${abs(x):,.0f})")

        st.dataframe(styled_agg, use_container_width=True, hide_index=True, height=400)

        # Download button for aggregator cashflows
        csv_agg = agg_df.to_csv(index=False)
        st.download_button(
            label="Download Aggregator Cashflows (CSV)",
            data=csv_agg,
            file_name="aggregator_monthly_cashflows.csv",
            mime="text/csv",
        )

        st.markdown("##### Aggregator Income Totals")
        inc1, inc2, inc3, inc4, inc5, inc6 = st.columns(6)

        total_b_aum = b_aum_monthly * hold_months
        total_c_aum = c_aum_monthly * hold_months
        total_coinvest_interest = coinvest_monthly_interest * hold_months

        with inc1:
            st.metric("Fee Allocation", f"${orig_fee_total + exit_fee_total:,.0f}",
                      help=f"Orig: ${orig_fee_total:,.0f} + Exit: ${exit_fee_total:,.0f}")
        with inc2:
            st.metric("B-Fund AUM Fee", f"${total_b_aum:,.0f}",
                      help=f"{hold_months}mo × ${b_aum_monthly:,.0f}")
        with inc3:
            st.metric("C-Fund AUM Fee", f"${total_c_aum:,.0f}",
                      help=f"{hold_months}mo × ${c_aum_monthly:,.0f}")
        with inc4:
            st.metric("Total Promote", f"${b_promote + c_promote:,.0f}",
                      help=f"B: ${b_promote:,.0f} + C: ${c_promote:,.0f}")
        with inc5:
            st.metric("Co-Invest Interest", f"${total_coinvest_interest:,.0f}",
                      help=f"Interest on ${coinvest_amt:,.0f} co-invest")
        with inc6:
            grand_total = orig_fee_total + exit_fee_total + total_b_aum + total_c_aum + b_promote + c_promote + total_coinvest_interest
            st.metric("Grand Total", f"${grand_total:,.0f}",
                      help="All aggregator income (excl. principal)")

        st.divider()

    # All stakeholders comparison
    st.subheader("All Stakeholders Comparison")

    st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1rem; margin-bottom:1rem; font-size:0.85rem; color:#b0bec5;">
<strong style="color:#4cc9f0;">Gross vs Net:</strong> Gross = total tranche returns | Net = LP returns after AUM & promote<br>
<strong style="color:#06ffa5;">Aggregator:</strong> Co-invest returns + AUM fees + Promote + Fee allocation
</div>""", unsafe_allow_html=True)

    if results:
        # Build y_dict with available tranches - showing gross and net
        y_dict = {}
        if "A" in results:
            y_dict["A-Piece (Bank)"] = results["A"].total_flows
        if "B" in results:
            y_dict["B-Fund Gross"] = results["B"].total_flows
        if fund_results and fund_results.get('B_fund'):
            y_dict["B-Fund LP Net"] = fund_results['B_fund'].lp_cashflows.total_flows
        if "C" in results:
            y_dict["C-Fund Gross"] = results["C"].total_flows
        if fund_results and fund_results.get('C_fund'):
            y_dict["C-Fund LP Net"] = fund_results['C_fund'].lp_cashflows.total_flows

        fig = create_area_chart(
            x=results["sponsor"].months,
            y_dict=y_dict,
            title="Cashflow Comparison: Gross vs LP Net Returns",
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

    # A-Piece (Bank)
    if "A" in results:
        r = results["A"]
        summary_rows.append({
            "Stakeholder": "A-Piece (Bank)",
            "Type": "Gross",
            "Initial Investment": f"${abs(r.total_flows[0]) if r.total_flows else 0:,.0f}",
            "Net Profit": f"${r.total_profit:,.0f}",
            "IRR": f"{r.irr:.1%}",
            "MOIC": f"{r.moic:.2f}x",
        })

    # B-Fund Gross
    if "B" in results:
        r = results["B"]
        summary_rows.append({
            "Stakeholder": "B-Fund",
            "Type": "Gross",
            "Initial Investment": f"${abs(r.total_flows[0]) if r.total_flows else 0:,.0f}",
            "Net Profit": f"${r.total_profit:,.0f}",
            "IRR": f"{r.irr:.1%}",
            "MOIC": f"{r.moic:.2f}x",
        })

    # B-Fund LP Net
    if fund_results and fund_results.get('B_fund'):
        r = fund_results['B_fund'].lp_cashflows
        summary_rows.append({
            "Stakeholder": "B-Fund LP",
            "Type": "Net (after AUM/promote)",
            "Initial Investment": f"${abs(r.total_flows[0]) if r.total_flows else 0:,.0f}",
            "Net Profit": f"${r.total_profit:,.0f}",
            "IRR": f"{r.irr:.1%}",
            "MOIC": f"{r.moic:.2f}x",
        })

    # C-Fund Gross
    if "C" in results:
        r = results["C"]
        summary_rows.append({
            "Stakeholder": "C-Fund",
            "Type": "Gross",
            "Initial Investment": f"${abs(r.total_flows[0]) if r.total_flows else 0:,.0f}",
            "Net Profit": f"${r.total_profit:,.0f}",
            "IRR": f"{r.irr:.1%}",
            "MOIC": f"{r.moic:.2f}x",
        })

    # C-Fund LP Net
    if fund_results and fund_results.get('C_fund'):
        r = fund_results['C_fund'].lp_cashflows
        summary_rows.append({
            "Stakeholder": "C-Fund LP",
            "Type": "Net (after AUM/promote)",
            "Initial Investment": f"${abs(r.total_flows[0]) if r.total_flows else 0:,.0f}",
            "Net Profit": f"${r.total_profit:,.0f}",
            "IRR": f"{r.irr:.1%}",
            "MOIC": f"{r.moic:.2f}x",
        })

    # Aggregator summary
    if aggregator_summary:
        summary_rows.append({
            "Stakeholder": "Aggregator",
            "Type": "Total Income",
            "Initial Investment": f"${aggregator_summary.coinvest_amount:,.0f}",
            "Net Profit": f"${aggregator_summary.grand_total:,.0f}",
            "IRR": f"{aggregator_summary.coinvest_irr:.1%}" if aggregator_summary.coinvest_amount > 0 else "N/A",
            "MOIC": f"{aggregator_summary.coinvest_moic:.2f}x" if aggregator_summary.coinvest_amount > 0 else "N/A",
        })

    st.dataframe(summary_rows, use_container_width=True, hide_index=True)

    # Aggregator breakdown
    if aggregator_summary:
        st.markdown("##### Aggregator Income Breakdown")
        agg1, agg2, agg3, agg4, agg5 = st.columns(5)
        with agg1:
            st.metric("Fee Allocation", f"${aggregator_summary.aggregator_direct_fee_allocation:,.0f}")
        with agg2:
            st.metric("B-Fund AUM Fee", f"${aggregator_summary.b_fund_aum_fees:,.0f}")
        with agg3:
            st.metric("C-Fund AUM Fee", f"${aggregator_summary.c_fund_aum_fees:,.0f}")
        with agg4:
            st.metric("Total Promote", f"${aggregator_summary.total_promote:,.0f}")
        with agg5:
            st.metric("Co-Invest Profit", f"${aggregator_summary.c_fund_coinvest_returns:,.0f}")

st.divider()
st.caption("HUD Financing Platform | Cashflow Analysis")
