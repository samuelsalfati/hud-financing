"""
Borrower View Page - Rate comparison and competitive positioning
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from components.charts import create_bar_chart, create_grouped_bar_chart, create_line_chart
from engine.dscr import calculate_dscr_from_deal, calculate_max_loan_for_dscr

# Page config
st.set_page_config(
    page_title="Borrower View | HUD Financing",
    page_icon="🏦",
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
    "Borrower View",
    "Rate comparison and financing analysis from borrower perspective"
), unsafe_allow_html=True)

# Deal Summary Bar
st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
<span style="color:#b0bec5;">Property: <strong style="color:#4cc9f0;">${p['property_value']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">Loan: <strong style="color:#4cc9f0;">${p['loan_amount']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">LTV: <strong style="color:#4cc9f0;">{p['ltv']:.0%}</strong></span>
<span style="color:#b0bec5;">Term: <strong style="color:#4cc9f0;">{p['term_months']}mo</strong></span>
<span style="color:#b0bec5;">SOFR: <strong style="color:#06ffa5;">{p['current_sofr']:.2%}</strong></span>
</div>""", unsafe_allow_html=True)

# Borrower Rate Summary
st.subheader("Your Financing Terms")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Loan Amount", f"${p['loan_amount']:,.0f}")

with col2:
    st.metric("Interest Rate", f"{p['borrower_rate']:.2%}")

with col3:
    monthly_payment = p["loan_amount"] * p["borrower_rate"] / 12
    st.metric("Monthly Interest", f"${monthly_payment:,.0f}")

with col4:
    total_interest = monthly_payment * p["hud_month"]
    st.metric("Total Interest Cost", f"${total_interest:,.0f}")

st.divider()

# Rate Breakdown
st.subheader("Rate Breakdown")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Rate Components")

    rate_data = [
        {"Component": "Base Rate (SOFR)", "Rate": f"{p['current_sofr']:.2%}"},
        {"Component": "Credit Spread", "Rate": f"+{p['borrower_spread']:.2%}"},
        {"Component": "**All-In Rate**", "Rate": f"**{p['borrower_rate']:.2%}**"},
    ]
    st.table(pd.DataFrame(rate_data))

    st.markdown("### Fee Summary")

    orig_fee_amt = deal.fees.calculate_origination(p["loan_amount"]) if deal else p['loan_amount'] * p['orig_fee']
    exit_fee_amt = deal.fees.calculate_exit(p["loan_amount"]) if deal else p['loan_amount'] * p['exit_fee']

    fee_data = [
        {"Fee": "Origination", "Rate": f"{p['orig_fee']:.2%}", "Amount": f"${orig_fee_amt:,.0f}"},
        {"Fee": "Exit", "Rate": f"{p['exit_fee']:.2%}", "Amount": f"${exit_fee_amt:,.0f}"},
        {"Fee": "**Total Fees**", "Rate": f"{p['orig_fee'] + p['exit_fee']:.2%}", "Amount": f"**${orig_fee_amt + exit_fee_amt:,.0f}**"},
    ]
    st.table(pd.DataFrame(fee_data))

with col2:
    st.markdown("### Effective Cost Analysis")

    # Calculate all-in cost
    total_fees = orig_fee_amt + exit_fee_amt
    annualized_fee_cost = total_fees / p["hud_month"] * 12
    fee_as_rate = annualized_fee_cost / p["loan_amount"]
    all_in_cost = p["borrower_rate"] + fee_as_rate

    st.markdown(f"""
    | Metric | Value |
    |--------|-------|
    | Interest Rate | {p['borrower_rate']:.2%} |
    | Annualized Fee Cost | {fee_as_rate:.2%} |
    | **Effective All-In Cost** | **{all_in_cost:.2%}** |
    """)

    # Total cost over loan life
    total_cost = total_interest + total_fees
    st.metric("Total Financing Cost", f"${total_cost:,.0f}")

st.divider()

# Competitive Analysis
st.subheader("Competitive Positioning")

st.markdown("""
Compare our bridge financing against market alternatives.
""")

# Market comparison data
competitors = [
    {"Lender": "Traditional Bridge", "Rate": p["current_sofr"] + 0.055, "Orig": 0.02, "Exit": 0.01},
    {"Lender": "Regional Bank", "Rate": p["current_sofr"] + 0.045, "Orig": 0.015, "Exit": 0.005},
    {"Lender": "Debt Fund", "Rate": p["current_sofr"] + 0.05, "Orig": 0.0175, "Exit": 0.0075},
    {"Lender": "**Our Platform**", "Rate": p["borrower_rate"], "Orig": p["orig_fee"], "Exit": p["exit_fee"]},
]

# Calculate all-in for each
for c in competitors:
    fee_cost = (c["Orig"] + c["Exit"]) / p["hud_month"] * 12
    c["All-In"] = c["Rate"] + fee_cost
    c["Monthly Payment"] = p["loan_amount"] * c["Rate"] / 12

comparison_df = pd.DataFrame(competitors)
comparison_df["Rate"] = comparison_df["Rate"].apply(lambda x: f"{x:.2%}")
comparison_df["Orig"] = comparison_df["Orig"].apply(lambda x: f"{x:.2%}")
comparison_df["Exit"] = comparison_df["Exit"].apply(lambda x: f"{x:.2%}")
comparison_df["All-In"] = comparison_df["All-In"].apply(lambda x: f"{x:.2%}")
comparison_df["Monthly Payment"] = comparison_df["Monthly Payment"].apply(lambda x: f"${x:,.0f}")

st.dataframe(comparison_df, use_container_width=True, hide_index=True)

# Visual comparison
all_in_rates = [c["Rate"] + (c["Orig"] + c["Exit"]) / p["hud_month"] * 12
                for c in [
                    {"Rate": p["current_sofr"] + 0.055, "Orig": 0.02, "Exit": 0.01},
                    {"Rate": p["current_sofr"] + 0.045, "Orig": 0.015, "Exit": 0.005},
                    {"Rate": p["current_sofr"] + 0.05, "Orig": 0.0175, "Exit": 0.0075},
                    {"Rate": p["borrower_rate"], "Orig": p["orig_fee"], "Exit": p["exit_fee"]},
                ]]

fig = create_bar_chart(
    x=["Traditional Bridge", "Regional Bank", "Debt Fund", "Our Platform"],
    y=[r * 100 for r in all_in_rates],
    title="All-In Cost Comparison (%)",
    y_title="Effective Rate (%)",
    color="#4cc9f0",
)
st.plotly_chart(fig, use_container_width=True)

# Calculate savings
our_cost = all_in_rates[3]
best_alternative = min(all_in_rates[:3])
annual_savings = (best_alternative - our_cost) * p["loan_amount"]

if annual_savings > 0:
    st.success(f"""
    **Your Savings with Our Platform:**
    - Annual savings vs best alternative: **${annual_savings:,.0f}**
    - Total savings over {p['hud_month']} months: **${annual_savings * p['hud_month'] / 12:,.0f}**
    """)
else:
    st.info("Adjust terms in Executive Summary to see potential savings")

st.divider()

# DSCR Analysis
st.subheader("Debt Service Analysis")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### Property NOI Input")

    noi_method = st.radio(
        "NOI Input Method",
        ["Enter NOI", "Enter Cap Rate"],
        horizontal=True,
    )

    if noi_method == "Enter NOI":
        noi_annual = st.number_input(
            "Annual NOI ($)",
            value=int(p["property_value"] * 0.08),
            step=100_000,
        )
    else:
        cap_rate = st.slider(
            "Cap Rate",
            min_value=0.05,
            max_value=0.12,
            value=0.08,
            format="%.1f%%",
        )
        noi_annual = p["property_value"] * cap_rate

    st.metric("Annual NOI", f"${noi_annual:,.0f}")

with col2:
    st.markdown("### DSCR Analysis")

    dscr_result = calculate_dscr_from_deal(
        p["loan_amount"],
        p["borrower_rate"],
        noi_annual,
    )

    # DSCR status
    if dscr_result.dscr >= 1.25:
        dscr_status = "Strong"
        dscr_color = "#06ffa5"
    elif dscr_result.dscr >= 1.10:
        dscr_status = "Adequate"
        dscr_color = "#4cc9f0"
    elif dscr_result.dscr >= 1.0:
        dscr_status = "Weak"
        dscr_color = "#ffa15a"
    else:
        dscr_status = "Below Coverage"
        dscr_color = "#ef553b"

    st.markdown(f"""
    <div style="
        background: rgba({int(dscr_color[1:3], 16)}, {int(dscr_color[3:5], 16)}, {int(dscr_color[5:7], 16)}, 0.15);
        border: 2px solid {dscr_color};
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    ">
        <div style="font-size: 0.8rem; color: #b0bec5;">DSCR</div>
        <div style="font-size: 2.5rem; font-weight: 700; color: {dscr_color};">{dscr_result.dscr:.2f}x</div>
        <div style="color: {dscr_color};">{dscr_status}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    **Coverage Analysis:**
    - Annual Debt Service: ${dscr_result.debt_service:,.0f}
    - Coverage Cushion: ${dscr_result.coverage_cushion:,.0f}
    - Breakeven NOI: ${dscr_result.breakeven_noi:,.0f}
    """)

# Max loan sizing
st.markdown("### Maximum Loan Sizing")

max_loan_125 = calculate_max_loan_for_dscr(noi_annual, p["borrower_rate"], 1.25)
max_loan_120 = calculate_max_loan_for_dscr(noi_annual, p["borrower_rate"], 1.20)
max_loan_110 = calculate_max_loan_for_dscr(noi_annual, p["borrower_rate"], 1.10)

sizing_data = [
    {"Target DSCR": "1.25x (Strong)", "Max Loan": f"${max_loan_125:,.0f}", "Max LTV": f"{max_loan_125/p['property_value']:.0%}"},
    {"Target DSCR": "1.20x (Standard)", "Max Loan": f"${max_loan_120:,.0f}", "Max LTV": f"{max_loan_120/p['property_value']:.0%}"},
    {"Target DSCR": "1.10x (Minimum)", "Max Loan": f"${max_loan_110:,.0f}", "Max LTV": f"{max_loan_110/p['property_value']:.0%}"},
    {"Target DSCR": "**Current**", "Max Loan": f"**${p['loan_amount']:,.0f}**", "Max LTV": f"**{p['ltv']:.0%}**"},
]

st.dataframe(sizing_data, use_container_width=True, hide_index=True)

st.divider()

# Payment Schedule Preview
st.subheader("Payment Schedule Preview")

borrower_cf = results.get("borrower") if results else None
if borrower_cf:
    months_to_show = min(12, len(borrower_cf.months))

    payment_data = []
    for i in range(months_to_show):
        payment_data.append({
            "Month": borrower_cf.months[i],
            "Interest": f"${abs(borrower_cf.interest_flows[i]):,.0f}",
            "Fees": f"${abs(borrower_cf.fee_flows[i]):,.0f}" if borrower_cf.fee_flows[i] != 0 else "-",
            "Total": f"${abs(borrower_cf.total_flows[i]):,.0f}",
        })

    st.dataframe(payment_data, use_container_width=True, hide_index=True)
else:
    st.info("Payment schedule will appear once deal is configured.")

st.divider()
st.caption("HUD Financing Platform | Borrower View")
