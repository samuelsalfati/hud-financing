"""
Capital Stack Page - Tranche structure and funding breakdown
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
from engine.deal import Deal, Tranche, TrancheType, RateType, FeeStructure, FundTerms
from engine.cashflows import generate_cashflows, generate_fund_cashflows
import plotly.graph_objects as go

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

st.set_page_config(page_title="Capital Stack", page_icon="🏗️", layout="wide")

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

# Header
st.markdown(page_header("Capital Stack", "Tranche structure and funding breakdown"), unsafe_allow_html=True)

# Current Deal Summary Bar
st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
<span style="color:#b0bec5;">Property: <strong style="color:#4cc9f0;">${p['property_value']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">Loan: <strong style="color:#4cc9f0;">${p['loan_amount']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">LTV: <strong style="color:#4cc9f0;">{p['ltv']:.0%}</strong></span>
<span style="color:#b0bec5;">Term: <strong style="color:#4cc9f0;">{p['term_months']}mo</strong></span>
<span style="color:#b0bec5;">SOFR: <strong style="color:#06ffa5;">{p['current_sofr']:.2%}</strong></span>
</div>""", unsafe_allow_html=True)

# Calculate amounts
a_amt = p['loan_amount'] * p['a_pct']
b_amt = p['loan_amount'] * p['b_pct']
c_amt = p['loan_amount'] * p['c_pct']

# =============================================================================
# CAPITAL STRUCTURE VISUALIZATION
# =============================================================================

st.markdown("### Capital Structure")

col1, col2 = st.columns([2, 1])

with col1:
    # Property value breakdown - vertical waterfall
    fig = go.Figure()

    # Stacked bar showing property breakdown - text centered
    fig.add_trace(go.Bar(
        name='Borrower Equity',
        x=['Property Value'],
        y=[p['equity_cushion']],
        marker_color='#06ffa5',
        text=[f"Equity {1-p['ltv']:.0%}"],
        textposition='inside',
        textfont={'color': 'white', 'size': 14},
        insidetextanchor='middle'
    ))

    fig.add_trace(go.Bar(
        name='C-Piece (Sponsor)',
        x=['Property Value'],
        y=[c_amt],
        marker_color='#ef553b',
        text=[f"C-Piece {p['c_pct']:.0%}"],
        textposition='inside',
        textfont={'color': 'white', 'size': 14},
        insidetextanchor='middle'
    ))

    fig.add_trace(go.Bar(
        name='B-Piece (Mezz)',
        x=['Property Value'],
        y=[b_amt],
        marker_color='#ffa15a',
        text=[f"B-Piece {p['b_pct']:.0%}"],
        textposition='inside',
        textfont={'color': 'white', 'size': 14},
        insidetextanchor='middle'
    ))

    fig.add_trace(go.Bar(
        name='A-Piece (Senior)',
        x=['Property Value'],
        y=[a_amt],
        marker_color='#4cc9f0',
        text=[f"A-Piece {p['a_pct']:.0%}"],
        textposition='inside',
        textfont={'color': 'white', 'size': 14},
        insidetextanchor='middle'
    ))

    fig.update_layout(
        barmode='stack',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#b0bec5'},
        showlegend=False,
        yaxis={'tickformat': '$,.0f', 'gridcolor': 'rgba(76,201,240,0.1)', 'title': ''},
        xaxis={'visible': False},
        margin=dict(l=60, r=20, t=20, b=20),
    )

    st.plotly_chart(fig, use_container_width=True, key="cap_structure")

with col2:
    # Calculate LTV on property for each tranche
    a_ltv = p['a_pct'] * p['ltv']
    b_ltv = p['b_pct'] * p['ltv']
    c_ltv = p['c_pct'] * p['ltv']

    # Legend / Summary Cards
    st.markdown(f"""
<div style="background:rgba(6,255,165,0.1); border-left:4px solid #06ffa5; padding:0.8rem; margin-bottom:0.8rem; border-radius:0 8px 8px 0;">
<div style="color:#06ffa5; font-weight:600;">Borrower Equity</div>
<div style="color:#b0bec5; font-size:1.3rem; font-weight:700;">${p['equity_cushion']/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.8rem;">{1-p['ltv']:.0%} equity cushion</div>
</div>

<div style="background:rgba(76,201,240,0.1); border-left:4px solid #4cc9f0; padding:0.8rem; margin-bottom:0.8rem; border-radius:0 8px 8px 0;">
<div style="color:#4cc9f0; font-weight:600;">A-Piece (Bank)</div>
<div style="color:#b0bec5; font-size:1.3rem; font-weight:700;">${a_amt/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.8rem;">SOFR + {p['a_spread']*10000:.0f}bps | LTV: {a_ltv:.1%} | Fee: {p['a_fee_alloc']:.0%}</div>
</div>

<div style="background:rgba(255,161,90,0.1); border-left:4px solid #ffa15a; padding:0.8rem; margin-bottom:0.8rem; border-radius:0 8px 8px 0;">
<div style="color:#ffa15a; font-weight:600;">B-Piece Fund</div>
<div style="color:#b0bec5; font-size:1.3rem; font-weight:700;">${b_amt/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.8rem;">SOFR + {p['b_spread']*10000:.0f}bps | LTV: {b_ltv:.1%} | Fee: {p['b_fee_alloc']:.0%}</div>
</div>

<div style="background:rgba(239,85,59,0.1); border-left:4px solid #ef553b; padding:0.8rem; border-radius:0 8px 8px 0;">
<div style="color:#ef553b; font-weight:600;">C-Piece Fund</div>
<div style="color:#b0bec5; font-size:1.3rem; font-weight:700;">${c_amt/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.8rem;">Target: {p['c_target']:.0%} | LTV: {c_ltv:.1%} | Fee: {p['c_fee_alloc']:.0%}</div>
</div>
""", unsafe_allow_html=True)

st.divider()

# =============================================================================
# COST OF CAPITAL
# =============================================================================

st.markdown("### Cost of Capital")

blended_cost = (p['a_pct'] * (p['current_sofr'] + p['a_spread']) +
                p['b_pct'] * (p['current_sofr'] + p['b_spread']) +
                p['c_pct'] * p['c_target'])
spread_profit = p['borrower_rate'] - blended_cost

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("Blended Cost", f"{blended_cost:.2%}")
with c2:
    st.metric("Borrower Rate", f"{p['borrower_rate']:.2%}")
with c3:
    st.metric("Spread Capture", f"{spread_profit:.2%}", delta=f"${p['loan_amount'] * spread_profit / 12:,.0f}/mo")
with c4:
    annual_spread = p['loan_amount'] * spread_profit
    st.metric("Annual Spread Income", f"${annual_spread:,.0f}")

# Rate comparison bar chart
st.markdown("##### Rate Comparison")

rates_data = {
    'Tranche': ['A-Piece', 'B-Piece', 'C-Piece', 'Blended Cost', 'Borrower Rate'],
    'Rate': [
        p['current_sofr'] + p['a_spread'],
        p['current_sofr'] + p['b_spread'],
        p['c_target'],
        blended_cost,
        p['borrower_rate']
    ],
    'Color': ['#4cc9f0', '#ffa15a', '#ef553b', '#06ffa5', '#ab63fa']
}

fig = go.Figure()
fig.add_trace(go.Bar(
    x=rates_data['Tranche'],
    y=[r * 100 for r in rates_data['Rate']],
    marker_color=rates_data['Color'],
    text=[f"{r:.2%}" for r in rates_data['Rate']],
    textposition='outside',
    textfont={'color': '#b0bec5'}
))

fig.update_layout(
    height=300,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    font={'color': '#b0bec5'},
    yaxis={'title': 'Rate (%)', 'gridcolor': 'rgba(76,201,240,0.1)'},
    xaxis={'title': ''},
    margin=dict(l=40, r=20, t=20, b=40),
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True, key="rate_compare")

st.divider()

# =============================================================================
# TRANCHE RETURNS
# =============================================================================

st.markdown("### Tranche Returns")

if results:
    a_result = results.get("A")
    b_result = results.get("B")
    c_result = results.get("C")

    # Get fund-level results for LP returns
    b_fund = fund_results.get('B_fund') if fund_results else None
    c_fund = fund_results.get('C_fund') if fund_results else None

    c1, c2, c3 = st.columns(3)

    with c1:
        a_irr = a_result.irr if a_result else 0
        a_moic = a_result.moic if a_result else 1
        a_profit = a_result.total_profit if a_result else 0
        st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border-radius:10px; padding:1.2rem; text-align:center;">
<div style="color:#4cc9f0; font-weight:600; font-size:1rem;">A-Piece (Bank)</div>
<div style="color:#b0bec5; font-size:2rem; font-weight:700;">{safe_pct(a_irr)}</div>
<div style="color:#78909c; font-size:0.9rem;">IRR</div>
<hr style="border-color:rgba(76,201,240,0.2); margin:0.8rem 0;">
<div style="display:flex; justify-content:space-around;">
<div><div style="color:#78909c; font-size:0.75rem;">MOIC</div><div style="color:#b0bec5;">{safe_moic(a_moic)}</div></div>
<div><div style="color:#78909c; font-size:0.75rem;">Profit</div><div style="color:#b0bec5;">{safe_currency(a_profit)}</div></div>
</div>
</div>""", unsafe_allow_html=True)

    with c2:
        # Show gross and net LP returns
        b_gross_irr = b_result.irr if b_result else 0
        b_lp_irr = b_fund.lp_cashflows.irr if b_fund else b_gross_irr
        b_lp_profit = b_fund.lp_cashflows.total_profit if b_fund else (b_result.total_profit if b_result else 0)
        b_aum = b_fund.total_aum_fees if b_fund else 0
        st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-radius:10px; padding:1.2rem; text-align:center;">
<div style="color:#ffa15a; font-weight:600; font-size:1rem;">B-Piece Fund</div>
<div style="color:#b0bec5; font-size:1.5rem; font-weight:700;">{safe_pct(b_gross_irr)} gross</div>
<div style="color:#ffa15a; font-size:1.1rem; font-weight:600;">{safe_pct(b_lp_irr)} LP net</div>
<hr style="border-color:rgba(255,161,90,0.2); margin:0.8rem 0;">
<div style="display:flex; justify-content:space-around;">
<div><div style="color:#78909c; font-size:0.7rem;">LP Profit</div><div style="color:#b0bec5; font-size:0.9rem;">{safe_currency(b_lp_profit)}</div></div>
<div><div style="color:#78909c; font-size:0.7rem;">AUM Fee</div><div style="color:#b0bec5; font-size:0.9rem;">{safe_currency(b_aum)}</div></div>
</div>
</div>""", unsafe_allow_html=True)

    with c3:
        # Show gross and net LP returns
        c_gross_irr = c_result.irr if c_result else 0
        c_lp_irr = c_fund.lp_cashflows.irr if c_fund else c_gross_irr
        c_lp_profit = c_fund.lp_cashflows.total_profit if c_fund else (c_result.total_profit if c_result else 0)
        c_aum = c_fund.total_aum_fees if c_fund else 0
        st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:10px; padding:1.2rem; text-align:center;">
<div style="color:#ef553b; font-weight:600; font-size:1rem;">C-Piece Fund</div>
<div style="color:#b0bec5; font-size:1.5rem; font-weight:700;">{safe_pct(c_gross_irr)} gross</div>
<div style="color:#ef553b; font-size:1.1rem; font-weight:600;">{safe_pct(c_lp_irr)} LP net</div>
<hr style="border-color:rgba(239,85,59,0.2); margin:0.8rem 0;">
<div style="display:flex; justify-content:space-around;">
<div><div style="color:#78909c; font-size:0.7rem;">LP Profit</div><div style="color:#b0bec5; font-size:0.9rem;">{safe_currency(c_lp_profit)}</div></div>
<div><div style="color:#78909c; font-size:0.7rem;">AUM Fee</div><div style="color:#b0bec5; font-size:0.9rem;">{safe_currency(c_aum)}</div></div>
</div>
</div>""", unsafe_allow_html=True)
else:
    st.warning("No results available. Please configure deal in Executive Summary first.")

st.divider()

# =============================================================================
# FEE ALLOCATION BY TRANCHE
# =============================================================================

st.markdown("### Fee Allocation")

orig_amt = p['loan_amount'] * p['orig_fee']
exit_amt = p['loan_amount'] * p['exit_fee']
ext_amt = p['loan_amount'] * p['ext_fee']
total_base_fees = orig_amt + exit_amt
hold_months = p['hud_month']

# Calculate fee allocation by tranche
a_fee = total_base_fees * p['a_fee_alloc']
b_fee = total_base_fees * p['b_fee_alloc']
c_fee = total_base_fees * p['c_fee_alloc']
agg_fee = total_base_fees * p['agg_fee_alloc']

st.markdown("##### Total Fees and Allocation")

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""<div style="background:rgba(128,128,128,0.1); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#78909c; font-size:0.75rem;">Total Fees</div>
<div style="color:#e0e0e0; font-size:1.3rem; font-weight:700;">${total_base_fees:,.0f}</div>
<div style="color:#546e7a; font-size:0.65rem;">{(p['orig_fee']+p['exit_fee'])*10000:.0f} bps</div>
</div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#4cc9f0; font-size:0.75rem;">A-Piece ({p['a_fee_alloc']:.0%})</div>
<div style="color:#4cc9f0; font-size:1.3rem; font-weight:700;">${a_fee:,.0f}</div>
<div style="color:#546e7a; font-size:0.65rem;">Bank share</div>
</div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#ffa15a; font-size:0.75rem;">B-Piece ({p['b_fee_alloc']:.0%})</div>
<div style="color:#ffa15a; font-size:1.3rem; font-weight:700;">${b_fee:,.0f}</div>
<div style="color:#546e7a; font-size:0.65rem;">Fund allocation</div>
</div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#ef553b; font-size:0.75rem;">C-Piece ({p['c_fee_alloc']:.0%})</div>
<div style="color:#ef553b; font-size:1.3rem; font-weight:700;">${c_fee:,.0f}</div>
<div style="color:#546e7a; font-size:0.65rem;">Fund allocation</div>
</div>""", unsafe_allow_html=True)

with c5:
    st.markdown(f"""<div style="background:rgba(6,255,165,0.15); border:1px solid rgba(6,255,165,0.4); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#06ffa5; font-size:0.75rem;">Aggregator ({p['agg_fee_alloc']:.0%})</div>
<div style="color:#06ffa5; font-size:1.3rem; font-weight:700;">${agg_fee:,.0f}</div>
<div style="color:#546e7a; font-size:0.65rem;">Direct income</div>
</div>""", unsafe_allow_html=True)

# Fee breakdown table - includes deal fees AND fund economics
st.markdown("##### Complete Fee & Economics Details")

# Calculate fund economics
b_amt = p['loan_amount'] * p['b_pct']
c_amt = p['loan_amount'] * p['c_pct']
agg_coinvest = p.get('agg_coinvest', 0)
c_lp_capital = c_amt * (1 - agg_coinvest)

# AUM fees (annual, prorated for hold period)
hold_years = hold_months / 12
b_aum_total = b_amt * p.get('b_aum_fee', 0.015) * hold_years
c_aum_total = c_lp_capital * p.get('c_aum_fee', 0.02) * hold_years

# Get promote from aggregator summary if available
b_promote_amt = aggregator_summary.b_fund_promote if aggregator_summary else 0
c_promote_amt = aggregator_summary.c_fund_promote if aggregator_summary else 0

fee_data = [
    # Deal Fees Section
    {"Category": "Deal Fees", "Fee Type": "Origination", "Rate/Terms": f"{p['orig_fee']*10000:.0f} bps", "Total": f"${orig_amt:,.0f}", "A-Piece": f"${orig_amt*p['a_fee_alloc']:,.0f}", "B-Fund": f"${orig_amt*p['b_fee_alloc']:,.0f}", "C-Fund": f"${orig_amt*p['c_fee_alloc']:,.0f}", "Aggregator": f"${orig_amt*p['agg_fee_alloc']:,.0f}", "Timing": "Day 1"},
    {"Category": "Deal Fees", "Fee Type": "Exit", "Rate/Terms": f"{p['exit_fee']*10000:.0f} bps", "Total": f"${exit_amt:,.0f}", "A-Piece": f"${exit_amt*p['a_fee_alloc']:,.0f}", "B-Fund": f"${exit_amt*p['b_fee_alloc']:,.0f}", "C-Fund": f"${exit_amt*p['c_fee_alloc']:,.0f}", "Aggregator": f"${exit_amt*p['agg_fee_alloc']:,.0f}", "Timing": "At HUD"},
    {"Category": "Deal Fees", "Fee Type": "Extension", "Rate/Terms": f"{p['ext_fee']*10000:.0f} bps", "Total": f"${ext_amt:,.0f}", "A-Piece": f"${ext_amt*p['a_fee_alloc']:,.0f}", "B-Fund": f"${ext_amt*p['b_fee_alloc']:,.0f}", "C-Fund": f"${ext_amt*p['c_fee_alloc']:,.0f}", "Aggregator": f"${ext_amt*p['agg_fee_alloc']:,.0f}", "Timing": "If needed"},
    # Fund Economics Section
    {"Category": "Fund AUM", "Fee Type": "B-Fund AUM Fee", "Rate/Terms": f"{p.get('b_aum_fee', 0.015)*100:.1f}%/yr", "Total": f"${b_aum_total:,.0f}", "A-Piece": "-", "B-Fund": f"(${b_aum_total:,.0f})", "C-Fund": "-", "Aggregator": f"${b_aum_total:,.0f}", "Timing": "Monthly"},
    {"Category": "Fund AUM", "Fee Type": "C-Fund AUM Fee", "Rate/Terms": f"{p.get('c_aum_fee', 0.02)*100:.1f}%/yr", "Total": f"${c_aum_total:,.0f}", "A-Piece": "-", "B-Fund": "-", "C-Fund": f"(${c_aum_total:,.0f})", "Aggregator": f"${c_aum_total:,.0f}", "Timing": "Monthly"},
    # Promote Section
    {"Category": "Promote", "Fee Type": "B-Fund Promote", "Rate/Terms": f"{p.get('b_promote', 0.20)*100:.0f}% > {p.get('b_hurdle', 0.08)*100:.0f}%", "Total": f"${b_promote_amt:,.0f}", "A-Piece": "-", "B-Fund": f"(${b_promote_amt:,.0f})", "C-Fund": "-", "Aggregator": f"${b_promote_amt:,.0f}", "Timing": "At Exit"},
    {"Category": "Promote", "Fee Type": "C-Fund Promote", "Rate/Terms": f"{p.get('c_promote', 0.20)*100:.0f}% > {p.get('c_hurdle', 0.10)*100:.0f}%", "Total": f"${c_promote_amt:,.0f}", "A-Piece": "-", "B-Fund": "-", "C-Fund": f"(${c_promote_amt:,.0f})", "Aggregator": f"${c_promote_amt:,.0f}", "Timing": "At Exit"},
]

st.dataframe(fee_data, use_container_width=True, hide_index=True)

# Summary totals
st.markdown("##### Fee Flow Summary")
total_deal_fees = orig_amt + exit_amt
total_aum = b_aum_total + c_aum_total
total_promote = b_promote_amt + c_promote_amt

sum1, sum2, sum3, sum4 = st.columns(4)
with sum1:
    st.markdown(f"""<div style="background:rgba(128,128,128,0.1); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#78909c; font-size:0.75rem;">Deal Fees (Orig+Exit)</div>
<div style="color:#e0e0e0; font-size:1.2rem; font-weight:700;">${total_deal_fees:,.0f}</div>
</div>""", unsafe_allow_html=True)

with sum2:
    st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#ffa15a; font-size:0.75rem;">Total AUM Fees ({hold_months}mo)</div>
<div style="color:#ffa15a; font-size:1.2rem; font-weight:700;">${total_aum:,.0f}</div>
</div>""", unsafe_allow_html=True)

with sum3:
    st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#ef553b; font-size:0.75rem;">Total Promote</div>
<div style="color:#ef553b; font-size:1.2rem; font-weight:700;">${total_promote:,.0f}</div>
</div>""", unsafe_allow_html=True)

with sum4:
    agg_total = agg_fee + total_aum + total_promote
    st.markdown(f"""<div style="background:rgba(6,255,165,0.15); border:1px solid rgba(6,255,165,0.4); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#06ffa5; font-size:0.75rem;">Aggregator Total</div>
<div style="color:#06ffa5; font-size:1.2rem; font-weight:700;">${agg_total:,.0f}</div>
</div>""", unsafe_allow_html=True)

# Aggregator total income
if aggregator_summary:
    st.markdown("##### Aggregator Economics Summary")
    ag1, ag2, ag3, ag4 = st.columns(4)
    with ag1:
        st.metric("Fee Income", f"${aggregator_summary.aggregator_direct_fee_allocation:,.0f}")
    with ag2:
        st.metric("AUM Fees", f"${aggregator_summary.total_aum_fees:,.0f}")
    with ag3:
        st.metric("Promote", f"${aggregator_summary.total_promote:,.0f}")
    with ag4:
        st.metric("Total", f"${aggregator_summary.grand_total:,.0f}", delta="All sources")

st.divider()

# =============================================================================
# NAVIGATION
# =============================================================================

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.page_link("pages/1_Executive_Summary.py", label="← Executive Summary")
with c2:
    st.page_link("pages/3_Cashflows.py", label="💰 Cashflows →")
with c3:
    st.page_link("pages/4_Scenarios.py", label="📈 Scenarios")
with c4:
    st.page_link("pages/5_Risk_Analysis.py", label="⚠️ Risk Analysis")

st.caption("HUD Financing Platform | Capital Stack")
