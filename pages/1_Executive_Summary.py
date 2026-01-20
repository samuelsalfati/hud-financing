"""
Executive Summary Page - Clean, professional deal analysis
"""
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from components.gauges import create_irr_gauge, create_moic_gauge, create_ltv_gauge, create_dscr_gauge
from engine.deal import Deal, Tranche, TrancheType, RateType, FeeStructure
from engine.cashflows import generate_cashflows
from engine.dscr import calculate_dscr_from_deal
import plotly.graph_objects as go

st.set_page_config(page_title="Executive Summary", page_icon="📊", layout="wide")

if not check_password():
    st.stop()

st.markdown(get_page_css(), unsafe_allow_html=True)

# Sidebar
sofr_data = render_sofr_indicator()
current_sofr = sofr_data.rate
render_logo()

# Header
st.markdown(page_header("Executive Summary", "Deal analysis at a glance"), unsafe_allow_html=True)

# =============================================================================
# COMPACT DEAL CONFIG
# =============================================================================

# Custom CSS for tighter inputs
st.markdown("""<style>
.stNumberInput > div > div > input { padding: 0.4rem 0.5rem; }
.stSelectbox > div > div { padding: 0.2rem; }
div[data-testid="stMetric"] { background: rgba(76,201,240,0.05); padding: 0.5rem; border-radius: 8px; }
div[data-testid="stMetric"] label { font-size: 0.75rem; }
div[data-testid="stMetric"] div[data-testid="stMetricValue"] { font-size: 1.1rem; }
.calculated-metric { background: linear-gradient(135deg, rgba(6,255,165,0.1), rgba(76,201,240,0.1)); border: 1px solid rgba(6,255,165,0.3); border-radius: 8px; padding: 0.6rem; text-align: center; }
.calculated-metric .label { font-size: 0.75rem; color: #78909c; }
.calculated-metric .value { font-size: 1.2rem; font-weight: 600; color: #06ffa5; }
</style>""", unsafe_allow_html=True)

# Config in columns - no expander, just clean layout
st.markdown("##### ⚙️ Deal Parameters")

# Row 1: Property & Loan
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

with c1:
    property_value = st.number_input("Property ($M)", min_value=1, max_value=500, value=120, step=5) * 1_000_000

with c2:
    ltv_pct = st.number_input("LTV (%)", min_value=50, max_value=90, value=85, step=5)
    ltv = ltv_pct / 100
    loan_amount = property_value * ltv

with c3:
    equity_cushion = property_value - loan_amount
    st.markdown(f'<div class="calculated-metric"><div class="label">Borrower Equity</div><div class="value">${equity_cushion/1e6:.1f}M</div></div>', unsafe_allow_html=True)

with c4:
    term_months = st.selectbox("Term (mo)", [24, 30, 36, 42, 48], index=2)

with c5:
    hud_month = st.number_input("HUD Exit (mo)", min_value=12, max_value=48, value=24)

with c6:
    borrower_bps = st.number_input("Borr Sprd (bps)", min_value=200, max_value=800, value=400, step=25)
    borrower_spread = borrower_bps / 10000

with c7:
    st.markdown(f'<div class="calculated-metric"><div class="label">Loan Amount</div><div class="value">${loan_amount/1e6:.0f}M</div></div>', unsafe_allow_html=True)

# Row 2: Capital Stack - Allocation & Pricing
c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    a_pct = st.number_input("A-Piece (%)", min_value=50, max_value=85, value=70, step=5) / 100

with c2:
    b_pct = st.number_input("B-Piece (%)", min_value=5, max_value=40, value=20, step=5) / 100

with c3:
    c_pct = max(0, 1 - a_pct - b_pct)
    st.markdown(f'<div class="calculated-metric"><div class="label">C-Piece (%)</div><div class="value">{c_pct:.0%}</div></div>', unsafe_allow_html=True)

with c4:
    a_spread = st.number_input("A Sprd (bps)", min_value=100, max_value=400, value=200, step=25) / 10000

with c5:
    b_spread = st.number_input("B Sprd (bps)", min_value=300, max_value=1000, value=600, step=50) / 10000

with c6:
    c_target = st.number_input("C Return (%)", min_value=8, max_value=25, value=12, help="Target return for equity") / 100

# Row 2b: Sponsor Role
st.markdown("##### 🎯 Sponsor Role")
role_col1, role_col2, role_col3 = st.columns([2, 2, 3])

with role_col1:
    sponsor_role = st.radio(
        "Your Role",
        ["Principal", "Aggregator"],
        horizontal=True,
        help="Principal = invest C-piece | Aggregator = earn fees only",
        key="sponsor_role_selector"
    )
    is_principal = sponsor_role == "Principal"

with role_col2:
    if is_principal:
        st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border:1px solid rgba(239,85,59,0.3); border-radius:8px; padding:0.6rem; margin-top:0.5rem;">
<div style="color:#ef553b; font-weight:600; font-size:0.85rem;">💰 You Invest C-Piece</div>
<div style="color:#b0bec5; font-size:0.8rem;">Capital at risk: ${loan_amount * c_pct / 1e6:.1f}M</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style="background:rgba(6,255,165,0.1); border:1px solid rgba(6,255,165,0.3); border-radius:8px; padding:0.6rem; margin-top:0.5rem;">
<div style="color:#06ffa5; font-weight:600; font-size:0.85rem;">🔄 Capital-Light Model</div>
<div style="color:#b0bec5; font-size:0.8rem;">No capital at risk • Fee income only</div>
</div>""", unsafe_allow_html=True)

with role_col3:
    if is_principal:
        st.markdown("""<div style="color:#78909c; font-size:0.8rem; margin-top:0.5rem;">
<strong>You earn:</strong> C-piece returns + origination fee + exit fee + spread income<br>
<strong>Risk:</strong> First-loss position if borrower defaults
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="color:#78909c; font-size:0.8rem; margin-top:0.5rem;">
<strong>You earn:</strong> Origination fee + exit fee + management fees + spread<br>
<strong>Risk:</strong> Operational only • C-piece sold to investor
</div>""", unsafe_allow_html=True)

# Row 3: Fees & Rates
c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    orig_fee = st.number_input("Orig Fee (bps)", min_value=50, max_value=300, value=100, step=25) / 10000

with c2:
    exit_fee = st.number_input("Exit Fee (bps)", min_value=0, max_value=200, value=50, step=25) / 10000

with c3:
    ext_fee = st.number_input("Ext Fee (bps)", min_value=0, max_value=200, value=50, step=25) / 10000

with c4:
    st.markdown(f'<div class="calculated-metric"><div class="label">SOFR (Live)</div><div class="value">{current_sofr:.2%}</div></div>', unsafe_allow_html=True)

with c5:
    borrower_rate = current_sofr + borrower_spread
    st.markdown(f'<div class="calculated-metric"><div class="label">Borrower Rate</div><div class="value">{borrower_rate:.2%}</div></div>', unsafe_allow_html=True)

with c6:
    blended_cost = (a_pct * (current_sofr + a_spread) + b_pct * (current_sofr + b_spread) + c_pct * c_target)
    st.markdown(f'<div class="calculated-metric"><div class="label">Blended Cost</div><div class="value">{blended_cost:.2%}</div></div>', unsafe_allow_html=True)

st.divider()

# =============================================================================
# BUILD & CALCULATE
# =============================================================================

# Save deal params to session state for other pages
st.session_state['deal_params'] = {
    'property_value': property_value,
    'loan_amount': loan_amount,
    'equity_cushion': equity_cushion,
    'ltv': ltv,
    'term_months': term_months,
    'hud_month': hud_month,
    'a_pct': a_pct,
    'b_pct': b_pct,
    'c_pct': c_pct,
    'a_spread': a_spread,
    'b_spread': b_spread,
    'c_target': c_target,
    'orig_fee': orig_fee,
    'exit_fee': exit_fee,
    'ext_fee': ext_fee,
    'borrower_spread': borrower_spread,
    'current_sofr': current_sofr,
    'borrower_rate': borrower_rate,
    'sponsor_role': sponsor_role,
    'is_principal': is_principal,
}

try:
    deal = Deal(
        property_value=property_value,
        loan_amount=loan_amount,
        term_months=term_months,
        expected_hud_month=hud_month,
        tranches=[
            Tranche(TrancheType.A, a_pct, RateType.FLOATING, a_spread),
            Tranche(TrancheType.B, b_pct, RateType.FLOATING, b_spread),
            Tranche(TrancheType.C, c_pct, RateType.FIXED, c_target),
        ],
        fees=FeeStructure(origination_fee=orig_fee, exit_fee=exit_fee, extension_fee=ext_fee),
        borrower_spread=borrower_spread,
    )

    results = generate_cashflows(deal, [current_sofr] * 60, hud_month, sponsor_is_principal=is_principal)
    st.session_state['deal'] = deal
    st.session_state['results'] = results
    sponsor = results.get("sponsor")
    irr = sponsor.irr if sponsor else 0
    moic = sponsor.moic if sponsor else 1
except Exception as e:
    st.error(f"Error calculating deal: {e}")
    deal = None
    results = None
    sponsor = None
    irr = 0
    moic = 1
    st.stop()

# =============================================================================
# KEY METRICS - Compact gauges
# =============================================================================

c1, c2, c3, c4 = st.columns(4)

with c1:
    if is_principal:
        st.plotly_chart(create_irr_gauge(irr, "IRR"), use_container_width=True, key="g1")
    else:
        # Aggregator mode - show Yield on Deal instead of IRR
        annual_profit = sponsor.total_profit * (12 / hud_month) if hud_month > 0 and sponsor else 0
        yield_pct = annual_profit / loan_amount if loan_amount > 0 else 0
        st.plotly_chart(create_irr_gauge(yield_pct, "Yield"), use_container_width=True, key="g1")
with c2:
    if is_principal:
        st.plotly_chart(create_moic_gauge(moic, "MOIC"), use_container_width=True, key="g2")
    else:
        # Show total profit in $K
        profit_display = sponsor.total_profit / 1000 if sponsor else 0
        st.metric("Total Profit", f"${sponsor.total_profit:,.0f}" if sponsor else "$0")
with c3:
    st.plotly_chart(create_ltv_gauge(ltv, "LTV"), use_container_width=True, key="g3")
with c4:
    dscr = calculate_dscr_from_deal(loan_amount, borrower_rate, loan_amount * 0.10)
    st.plotly_chart(create_dscr_gauge(dscr.dscr, "DSCR"), use_container_width=True, key="g4")

# =============================================================================
# CAPITAL STACK - Full width section
# =============================================================================

a_amt = loan_amount * a_pct
b_amt = loan_amount * b_pct
c_amt = loan_amount * c_pct

st.markdown("### Capital Stack")

fig = go.Figure()
fig.add_trace(go.Bar(x=[c_amt], y=[""], orientation='h', marker_color="#ef553b",
    text=[f"C-Piece {c_pct:.0%}"], textposition="inside", textfont={"color":"white", "size":14},
    insidetextanchor="middle"))
fig.add_trace(go.Bar(x=[b_amt], y=[""], orientation='h', marker_color="#ffa15a",
    text=[f"B-Piece {b_pct:.0%}"], textposition="inside", textfont={"color":"white", "size":14},
    insidetextanchor="middle"))
fig.add_trace(go.Bar(x=[a_amt], y=[""], orientation='h', marker_color="#4cc9f0",
    text=[f"A-Piece {a_pct:.0%}"], textposition="inside", textfont={"color":"white", "size":14},
    insidetextanchor="middle"))
fig.update_layout(barmode='stack', height=80, showlegend=False, margin=dict(l=0,r=0,t=10,b=10),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    xaxis={"visible":False}, yaxis={"visible":False},
    uniformtext={"minsize":12, "mode":"show"})
st.plotly_chart(fig, use_container_width=True, key="stack")

# Tranche details
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border-left:4px solid #4cc9f0; padding:0.8rem; border-radius:4px;">
<div style="color:#4cc9f0; font-weight:600;">A-Piece (Senior)</div>
<div style="color:#b0bec5; font-size:0.9rem;">${a_amt/1e6:.1f}M ({a_pct:.0%}) @ SOFR+{a_spread*10000:.0f}bps</div>
<div style="color:#78909c; font-size:0.8rem;">Bank funding • First loss protection</div>
</div>""", unsafe_allow_html=True)
with c2:
    st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-left:4px solid #ffa15a; padding:0.8rem; border-radius:4px;">
<div style="color:#ffa15a; font-weight:600;">B-Piece (Mezzanine)</div>
<div style="color:#b0bec5; font-size:0.9rem;">${b_amt/1e6:.1f}M ({b_pct:.0%}) @ SOFR+{b_spread*10000:.0f}bps</div>
<div style="color:#78909c; font-size:0.8rem;">Yield investors • Second loss</div>
</div>""", unsafe_allow_html=True)
with c3:
    if is_principal:
        st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-left:4px solid #ef553b; padding:0.8rem; border-radius:4px;">
<div style="color:#ef553b; font-weight:600;">C-Piece (You Keep)</div>
<div style="color:#b0bec5; font-size:0.9rem;">${c_amt/1e6:.1f}M ({c_pct:.0%}) @ {c_target:.0%} target</div>
<div style="color:#78909c; font-size:0.8rem;">Your capital • First loss position</div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-left:4px solid #ef553b; padding:0.8rem; border-radius:4px;">
<div style="color:#ef553b; font-weight:600;">C-Piece (Sold to Investor)</div>
<div style="color:#b0bec5; font-size:0.9rem;">${c_amt/1e6:.1f}M ({c_pct:.0%}) @ {c_target:.0%} target</div>
<div style="color:#78909c; font-size:0.8rem;">Third-party investor • You earn spread</div>
</div>""", unsafe_allow_html=True)

st.divider()

# =============================================================================
# RECOMMENDATION - Full section with risk analysis
# =============================================================================

st.markdown("### Investment Recommendation")

if irr >= 0.20 and moic >= 1.3 and ltv <= 0.80:
    rec, color, desc = "STRONG INVEST", "#06ffa5", "Exceptional risk-adjusted returns with conservative leverage. Proceed with standard diligence."
elif irr >= 0.15 and moic >= 1.2:
    rec, color, desc = "INVEST", "#00cc96", "Solid returns meeting all investment criteria. Deal is attractive at current terms."
elif irr >= 0.10:
    rec, color, desc = "CONDITIONAL", "#ffa15a", "Returns meet minimum threshold but leave limited margin for error. Consider negotiating better terms."
else:
    rec, color, desc = "PASS", "#ef553b", "Returns below investment threshold. Do not proceed without significant restructuring."

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown(f"""<div style="background:rgba(0,0,0,0.3); border:3px solid {color}; border-radius:12px; padding:1.5rem; text-align:center;">
<div style="font-size:0.8rem; color:#78909c; text-transform:uppercase; letter-spacing:1px;">Recommendation</div>
<div style="font-size:2.2rem; font-weight:700; color:{color}; margin:0.5rem 0;">{rec}</div>
<div style="font-size:0.85rem; color:#b0bec5;">{desc}</div>
</div>""", unsafe_allow_html=True)

with col2:
    # Metrics check
    st.markdown("**Investment Criteria**")
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        status = "✅" if irr >= 0.15 else "⚠️" if irr >= 0.10 else "❌"
        st.metric("IRR", f"{irr:.1%}", delta=f"{status} Target ≥15%", delta_color="off")
    with mc2:
        status = "✅" if moic >= 1.2 else "⚠️" if moic >= 1.1 else "❌"
        st.metric("MOIC", f"{moic:.2f}x", delta=f"{status} Target ≥1.2x", delta_color="off")
    with mc3:
        status = "✅" if ltv <= 0.80 else "⚠️" if ltv <= 0.85 else "❌"
        st.metric("LTV", f"{ltv:.0%}", delta=f"{status} Target ≤80%", delta_color="off")
    with mc4:
        status = "✅" if 18 <= hud_month <= 30 else "⚠️"
        st.metric("HUD Exit", f"Month {hud_month}", delta=f"{status} Typical 18-30", delta_color="off")

    # Risk factors
    st.markdown("**Key Risks**")
    rc1, rc2 = st.columns(2)
    with rc1:
        rate_risk = "High" if borrower_spread < 0.035 else "Medium" if borrower_spread < 0.05 else "Low"
        timing_risk = "High" if hud_month > 30 else "Medium" if hud_month > 24 else "Low"
        st.markdown(f"• **Rate Risk:** {rate_risk} - {'Thin spread buffer' if rate_risk=='High' else 'Adequate spread cushion'}")
        st.markdown(f"• **Timing Risk:** {timing_risk} - HUD exit at month {hud_month}")
    with rc2:
        leverage_risk = "High" if ltv > 0.85 else "Medium" if ltv > 0.75 else "Low"
        concentration_risk = "Medium" if c_pct < 0.15 else "Low"
        st.markdown(f"• **Leverage Risk:** {leverage_risk} - {ltv:.0%} LTV")
        st.markdown(f"• **Concentration:** {concentration_risk} - ${c_amt/1e6:.1f}M equity at risk")

st.divider()

# =============================================================================
# RETURNS SUMMARY
# =============================================================================

st.markdown("### Returns Summary")

# Get tranche results
a_result = results.get("A")
b_result = results.get("B")
c_result = results.get("C")

# Tranche Returns
st.markdown("**Returns by Tranche**")
c1, c2, c3 = st.columns(3)

with c1:
    a_irr = a_result.irr if a_result else 0
    a_profit = a_result.total_profit if a_result else 0
    st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#4cc9f0; font-weight:600; font-size:0.9rem;">A-Piece (Senior)</div>
<div style="color:#b0bec5; font-size:1.4rem; font-weight:700;">{a_irr:.1%} IRR</div>
<div style="color:#78909c; font-size:0.8rem;">Profit: ${a_profit:,.0f}</div>
</div>""", unsafe_allow_html=True)

with c2:
    b_irr = b_result.irr if b_result else 0
    b_profit = b_result.total_profit if b_result else 0
    st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#ffa15a; font-weight:600; font-size:0.9rem;">B-Piece (Mezz)</div>
<div style="color:#b0bec5; font-size:1.4rem; font-weight:700;">{b_irr:.1%} IRR</div>
<div style="color:#78909c; font-size:0.8rem;">Profit: ${b_profit:,.0f}</div>
</div>""", unsafe_allow_html=True)

with c3:
    c_irr = c_result.irr if c_result else 0
    c_profit = c_result.total_profit if c_result else 0
    st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#ef553b; font-weight:600; font-size:0.9rem;">C-Piece (Equity)</div>
<div style="color:#b0bec5; font-size:1.4rem; font-weight:700;">{c_irr:.1%} IRR</div>
<div style="color:#78909c; font-size:0.8rem;">Profit: ${c_profit:,.0f}</div>
</div>""", unsafe_allow_html=True)

# Our Returns (Sponsor/Investor)
if is_principal:
    st.markdown("**Our Returns (Principal - C-Piece + Fees)**")
else:
    st.markdown("**Our Returns (Aggregator - Fees + Spread Only)**")

if sponsor and sponsor.months:
    import math

    if is_principal:
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.metric("Investment", f"${c_amt:,.0f}")
        with c2:
            st.metric("Interest Income", f"${sum(sponsor.interest_flows):,.0f}")
        with c3:
            st.metric("Fee Income", f"${sum(sponsor.fee_flows):,.0f}")
        with c4:
            st.metric("Total Profit", f"${sponsor.total_profit:,.0f}")
        with c5:
            st.metric("IRR", f"{irr:.1%}")
        with c6:
            moic_display = f"{moic:.2f}x" if not math.isinf(moic) else "N/A"
            st.metric("MOIC", moic_display)
    else:
        # Aggregator mode - no investment, show fee breakdown
        spread_income = sum(sponsor.interest_flows)
        fee_income = sum(sponsor.fee_flows)
        total_profit = sponsor.total_profit
        annual_profit = total_profit * (12 / hud_month) if hud_month > 0 else 0
        yield_on_deal = annual_profit / loan_amount if loan_amount > 0 else 0

        st.markdown("""<div style="background:rgba(6,255,165,0.1); border:1px solid rgba(6,255,165,0.3); border-radius:8px; padding:0.8rem 1rem; margin-bottom:1rem;">
<strong style="color:#06ffa5;">💡 Aggregator Mode:</strong>
<span style="color:#b0bec5;"> IRR is N/A (no capital invested). Use Yield on Deal and Total Profit as key metrics.</span>
</div>""", unsafe_allow_html=True)

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.metric("Investment", "$0")
        with c2:
            st.metric("Spread Income", f"${spread_income:,.0f}")
        with c3:
            st.metric("Fee Income", f"${fee_income:,.0f}")
        with c4:
            st.metric("Total Profit", f"${total_profit:,.0f}")
        with c5:
            st.metric("Yield on Deal", f"{yield_on_deal:.2%}")
        with c6:
            st.metric("IRR", "N/A", help="No investment = no IRR")

        # Fee breakdown detail
        with st.expander("📋 Fee Breakdown"):
            orig = orig_fee * loan_amount
            exit_f = exit_fee * loan_amount
            mgmt = (hud_month - 1) * 0  # Management fees if any
            st.markdown(f"""
| Fee Type | Amount |
|----------|--------|
| Origination Fee ({orig_fee*10000:.0f} bps) | ${orig:,.0f} |
| Exit Fee ({exit_fee*10000:.0f} bps) | ${exit_f:,.0f} |
| Monthly Spread × {hud_month} months | ${spread_income:,.0f} |
| **Total** | **${total_profit:,.0f}** |
            """)

st.divider()

# =============================================================================
# QUICK LINKS
# =============================================================================

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.page_link("pages/2_Capital_Stack.py", label="📊 Capital Stack")
with c2:
    st.page_link("pages/3_Cashflows.py", label="💰 Cashflows")
with c3:
    st.page_link("pages/4_Scenarios.py", label="📈 Scenarios")
with c4:
    st.page_link("pages/6_Monte_Carlo.py", label="🎲 Monte Carlo")
