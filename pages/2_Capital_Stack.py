"""
Capital Stack Page - Tranche structure and funding breakdown
"""
import streamlit as st
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from engine.deal import Deal, Tranche, TrancheType, RateType, FeeStructure
from engine.cashflows import generate_cashflows
import plotly.graph_objects as go

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
    # Legend / Summary Cards
    st.markdown(f"""
<div style="background:rgba(6,255,165,0.1); border-left:4px solid #06ffa5; padding:0.8rem; margin-bottom:0.8rem; border-radius:0 8px 8px 0;">
<div style="color:#06ffa5; font-weight:600;">Borrower Equity</div>
<div style="color:#b0bec5; font-size:1.3rem; font-weight:700;">${p['equity_cushion']/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.8rem;">{1-p['ltv']:.0%} equity cushion</div>
</div>

<div style="background:rgba(76,201,240,0.1); border-left:4px solid #4cc9f0; padding:0.8rem; margin-bottom:0.8rem; border-radius:0 8px 8px 0;">
<div style="color:#4cc9f0; font-weight:600;">A-Piece (Senior)</div>
<div style="color:#b0bec5; font-size:1.3rem; font-weight:700;">${a_amt/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.8rem;">SOFR + {p['a_spread']*10000:.0f}bps = {p['current_sofr']+p['a_spread']:.2%}</div>
</div>

<div style="background:rgba(255,161,90,0.1); border-left:4px solid #ffa15a; padding:0.8rem; margin-bottom:0.8rem; border-radius:0 8px 8px 0;">
<div style="color:#ffa15a; font-weight:600;">B-Piece (Mezzanine)</div>
<div style="color:#b0bec5; font-size:1.3rem; font-weight:700;">${b_amt/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.8rem;">SOFR + {p['b_spread']*10000:.0f}bps = {p['current_sofr']+p['b_spread']:.2%}</div>
</div>

<div style="background:rgba(239,85,59,0.1); border-left:4px solid #ef553b; padding:0.8rem; border-radius:0 8px 8px 0;">
<div style="color:#ef553b; font-weight:600;">C-Piece (Sponsor Equity)</div>
<div style="color:#b0bec5; font-size:1.3rem; font-weight:700;">${c_amt/1e6:.1f}M</div>
<div style="color:#78909c; font-size:0.8rem;">Target return: {p['c_target']:.0%}</div>
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

    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border-radius:10px; padding:1.2rem; text-align:center;">
<div style="color:#4cc9f0; font-weight:600; font-size:1rem;">A-Piece (Senior)</div>
<div style="color:#b0bec5; font-size:2rem; font-weight:700;">{a_result.irr:.1%}</div>
<div style="color:#78909c; font-size:0.9rem;">IRR</div>
<hr style="border-color:rgba(76,201,240,0.2); margin:0.8rem 0;">
<div style="display:flex; justify-content:space-around;">
<div><div style="color:#78909c; font-size:0.75rem;">MOIC</div><div style="color:#b0bec5;">{a_result.moic:.2f}x</div></div>
<div><div style="color:#78909c; font-size:0.75rem;">Profit</div><div style="color:#b0bec5;">${a_result.total_profit:,.0f}</div></div>
</div>
</div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-radius:10px; padding:1.2rem; text-align:center;">
<div style="color:#ffa15a; font-weight:600; font-size:1rem;">B-Piece (Mezz)</div>
<div style="color:#b0bec5; font-size:2rem; font-weight:700;">{b_result.irr:.1%}</div>
<div style="color:#78909c; font-size:0.9rem;">IRR</div>
<hr style="border-color:rgba(255,161,90,0.2); margin:0.8rem 0;">
<div style="display:flex; justify-content:space-around;">
<div><div style="color:#78909c; font-size:0.75rem;">MOIC</div><div style="color:#b0bec5;">{b_result.moic:.2f}x</div></div>
<div><div style="color:#78909c; font-size:0.75rem;">Profit</div><div style="color:#b0bec5;">${b_result.total_profit:,.0f}</div></div>
</div>
</div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:10px; padding:1.2rem; text-align:center;">
<div style="color:#ef553b; font-weight:600; font-size:1rem;">C-Piece (Sponsor)</div>
<div style="color:#b0bec5; font-size:2rem; font-weight:700;">{c_result.irr:.1%}</div>
<div style="color:#78909c; font-size:0.9rem;">IRR</div>
<hr style="border-color:rgba(239,85,59,0.2); margin:0.8rem 0;">
<div style="display:flex; justify-content:space-around;">
<div><div style="color:#78909c; font-size:0.75rem;">MOIC</div><div style="color:#b0bec5;">{c_result.moic:.2f}x</div></div>
<div><div style="color:#78909c; font-size:0.75rem;">Profit</div><div style="color:#b0bec5;">${c_result.total_profit:,.0f}</div></div>
</div>
</div>""", unsafe_allow_html=True)

st.divider()

# =============================================================================
# FEE INCOME & RETURN CONTRIBUTION
# =============================================================================

st.markdown("### Fee Income & Return Contribution")

orig_amt = p['loan_amount'] * p['orig_fee']
exit_amt = p['loan_amount'] * p['exit_fee']
ext_amt = p['loan_amount'] * p['ext_fee']
total_base_fees = orig_amt + exit_amt
hold_months = p['hud_month']

# Fee return metrics
fee_return_on_c = total_base_fees / c_amt  # Total fee return on C investment
fee_irr_contribution = (fee_return_on_c / (hold_months / 12))  # Annualized

st.markdown("##### Since we raise capital separately for each tranche, our return primarily comes from fees:")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(f"""<div style="background:rgba(6,255,165,0.15); border:1px solid #06ffa5; border-radius:10px; padding:1rem; text-align:center;">
<div style="color:#78909c; font-size:0.8rem;">Total Fee Income</div>
<div style="color:#06ffa5; font-size:1.8rem; font-weight:700;">${total_base_fees:,.0f}</div>
<div style="color:#78909c; font-size:0.75rem;">on ${p['loan_amount']/1e6:.0f}M loan</div>
</div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""<div style="background:rgba(6,255,165,0.15); border:1px solid #06ffa5; border-radius:10px; padding:1rem; text-align:center;">
<div style="color:#78909c; font-size:0.8rem;">Fee Return on C</div>
<div style="color:#06ffa5; font-size:1.8rem; font-weight:700;">{fee_return_on_c:.1%}</div>
<div style="color:#78909c; font-size:0.75rem;">${total_base_fees:,.0f} / ${c_amt:,.0f}</div>
</div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""<div style="background:rgba(6,255,165,0.15); border:1px solid #06ffa5; border-radius:10px; padding:1rem; text-align:center;">
<div style="color:#78909c; font-size:0.8rem;">Annualized Fee IRR</div>
<div style="color:#06ffa5; font-size:1.8rem; font-weight:700;">{fee_irr_contribution:.1%}</div>
<div style="color:#78909c; font-size:0.75rem;">over {hold_months} months</div>
</div>""", unsafe_allow_html=True)

with c4:
    # Fee multiple
    fee_moic = 1 + fee_return_on_c
    st.markdown(f"""<div style="background:rgba(6,255,165,0.15); border:1px solid #06ffa5; border-radius:10px; padding:1rem; text-align:center;">
<div style="color:#78909c; font-size:0.8rem;">Fee MOIC</div>
<div style="color:#06ffa5; font-size:1.8rem; font-weight:700;">{fee_moic:.2f}x</div>
<div style="color:#78909c; font-size:0.75rem;">from fees alone</div>
</div>""", unsafe_allow_html=True)

# Fee breakdown table
st.markdown("##### Fee Breakdown")
fee_data = [
    {"Fee": "Origination", "Rate": f"{p['orig_fee']*10000:.0f} bps", "Amount": f"${orig_amt:,.0f}", "% of C": f"{orig_amt/c_amt:.1%}", "Timing": "Day 1 (upfront)"},
    {"Fee": "Exit", "Rate": f"{p['exit_fee']*10000:.0f} bps", "Amount": f"${exit_amt:,.0f}", "% of C": f"{exit_amt/c_amt:.1%}", "Timing": "At HUD payoff"},
    {"Fee": "Extension", "Rate": f"{p['ext_fee']*10000:.0f} bps", "Amount": f"${ext_amt:,.0f}", "% of C": f"{ext_amt/c_amt:.1%}", "Timing": "If extension needed"},
]
st.dataframe(fee_data, use_container_width=True, hide_index=True)

st.info(f"""
**Key Insight:** Fees alone generate **{fee_return_on_c:.1%}** return on our C-piece investment (${c_amt/1e6:.1f}M) — that's **{fee_irr_contribution:.1%}** annualized over {hold_months} months.
The spread income and C-piece interest are additional upside.
""")

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
