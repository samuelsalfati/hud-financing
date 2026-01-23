"""
Executive Summary Page - Deal configuration with fund economics
"""
import streamlit as st
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from components.gauges import create_irr_gauge, create_moic_gauge, create_ltv_gauge, create_dscr_gauge
from engine.deal import Deal, Tranche, TrancheType, RateType, FeeStructure, FundTerms
from engine.cashflows import generate_cashflows, generate_fund_cashflows
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


# =============================================================================
# SESSION STATE DEFAULTS - Persist inputs across page navigation
# =============================================================================

# Initialize session state only once at app start
if 'app_initialized' not in st.session_state:
    st.session_state.app_initialized = True
    st.session_state.input_values = {}


def get_default(key, default_value):
    """Get value from session state or return default"""
    if 'input_values' not in st.session_state:
        st.session_state.input_values = {}
    return st.session_state.input_values.get(key, default_value)


def save_input(key, value):
    """Save input value to session state"""
    if 'input_values' not in st.session_state:
        st.session_state.input_values = {}
    st.session_state.input_values[key] = value


def reset_all_inputs():
    """Reset all inputs to defaults"""
    st.session_state.input_values = {}
    # Clear deal-related session state
    for key in ['deal_params', 'deal', 'results', 'fund_results', 'aggregator_summary']:
        if key in st.session_state:
            del st.session_state[key]


# Helper functions for formatting
def safe_pct(val, decimals=1):
    """Format percentage, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.{decimals}%}"

def safe_moic(val):
    """Format MOIC, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.2f}x"

# Header with Reset button
header_col1, header_col2 = st.columns([6, 1])
with header_col1:
    st.markdown(page_header("Executive Summary", "Deal configuration & analysis"), unsafe_allow_html=True)
with header_col2:
    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)  # Spacer
    if st.button("🔄 Reset Deal", help="Clear all inputs and start fresh", type="secondary"):
        reset_all_inputs()
        st.rerun()

# =============================================================================
# EDUCATIONAL SECTION - Understanding the Structure
# =============================================================================
with st.expander("📚 How This Works - Key Terms & Fund Flow", expanded=False):
    st.markdown("""
    ### Capital Structure Overview

    This platform models a **bridge loan** for skilled nursing facilities (SNFs) awaiting HUD permanent financing.
    The loan is split into three tranches with different risk/return profiles:

    | Tranche | Risk Level | Typical Investor | Position |
    |---------|------------|------------------|----------|
    | **A-Piece** | Lowest | Bank | Senior (paid first) |
    | **B-Piece** | Medium | Mezz Fund LPs | Middle |
    | **C-Piece** | Highest | First Loss Fund LPs | Junior (paid last) |

    ---

    ### Key Terms Explained

    #### Returns: Gross vs Net

    | Term | Definition | Who Sees This |
    |------|------------|---------------|
    | **Gross IRR/MOIC** | Returns before any fund fees | The tranche itself |
    | **LP Net IRR/MOIC** | Returns after AUM fees & promote | What LPs actually receive |

    **Example:** If C-Piece Gross IRR = 15%, after 2% AUM fee and 20% promote, LP Net IRR ≈ 11%

    ---

    #### Fund Economics (B & C Funds)

    | Fee Type | What It Is | When Paid | Who Receives |
    |----------|------------|-----------|--------------|
    | **AUM Fee** | % of LP capital per year | Monthly | Aggregator |
    | **Promote (Carry)** | % of profits above hurdle | At Exit | Aggregator |
    | **Hurdle Rate** | Min return LPs get before promote kicks in | - | Threshold |

    **Example Flow:**
    1. C-Fund LP invests $1M
    2. Monthly: LP pays ~$1,667 AUM fee (2%/yr ÷ 12)
    3. At exit: If profit = $200K and hurdle (10%) achieved:
       - LP gets first 10% ($100K)
       - Remaining $100K split: 80% LP ($80K) + 20% Promote ($20K)

    ---

    #### Aggregator Income Sources

    ```
    ┌─────────────────────────────────────────────────────────────┐
    │                    AGGREGATOR TOTAL INCOME                   │
    ├─────────────────────────────────────────────────────────────┤
    │  1. Fee Allocation     → Share of origination & exit fees   │
    │  2. B-Fund AUM Fees    → Annual % of B-Fund LP capital      │
    │  3. C-Fund AUM Fees    → Annual % of C-Fund LP capital      │
    │  4. B-Fund Promote     → Carry on B-Fund profits > hurdle   │
    │  5. C-Fund Promote     → Carry on C-Fund profits > hurdle   │
    │  6. Co-Invest Returns  → Direct returns on own C investment │
    └─────────────────────────────────────────────────────────────┘
    ```

    ---

    #### Co-Investment

    When the Aggregator **co-invests** in the C-Piece:
    - They put their own capital at risk (alongside LPs)
    - Their portion is **fee-free** (no AUM fee on their own money)
    - They earn the **gross C-Piece return** on their investment
    - This aligns Aggregator interests with LPs

    ---

    ### Money Flow Diagram

    ```
    BORROWER pays interest
           ↓
    ┌──────────────────────────────────────────────────────────┐
    │                    LOAN WATERFALL                         │
    │  A-Piece (Bank) ←── Gets paid FIRST (senior)             │
    │  B-Piece Fund   ←── Gets paid SECOND (mezz)              │
    │  C-Piece Fund   ←── Gets paid LAST (first loss)          │
    └──────────────────────────────────────────────────────────┘
           ↓
    ┌──────────────────────────────────────────────────────────┐
    │               FUND WATERFALL (B & C)                      │
    │  1. Return LP capital (principal)                        │
    │  2. Pay LP hurdle return (e.g., 8-10%)                   │
    │  3. Split remaining: LP (80%) + Aggregator Promote (20%) │
    └──────────────────────────────────────────────────────────┘
    ```

    ---

    ### Quick Glossary

    | Term | Definition |
    |------|------------|
    | **IRR** | Internal Rate of Return - annualized return accounting for timing |
    | **MOIC** | Multiple on Invested Capital - total return / investment |
    | **LTV** | Loan-to-Value - loan amount / property value |
    | **SOFR** | Secured Overnight Financing Rate - benchmark interest rate |
    | **Spread** | Additional interest above SOFR (e.g., SOFR + 200bps) |
    | **bps** | Basis points - 1/100th of 1% (100 bps = 1%) |
    | **HUD Exit** | When permanent HUD financing closes & bridge loan repays |
    """)

# Custom CSS for beautiful sections
st.markdown("""<style>
.stNumberInput > div > div > input { padding: 0.4rem 0.5rem; font-size: 0.9rem; }
.stSelectbox > div > div { padding: 0.2rem 0; }

/* Section containers */
.section-box {
    background: linear-gradient(135deg, rgba(26,35,50,0.9), rgba(15,25,40,0.95));
    border-radius: 12px;
    padding: 1.2rem;
    margin: 0.8rem 0;
    border: 1px solid rgba(255,255,255,0.08);
}
.section-box-a {
    border-left: 4px solid #4cc9f0;
    background: linear-gradient(135deg, rgba(76,201,240,0.08), rgba(26,35,50,0.95));
}
.section-box-b {
    border-left: 4px solid #ffa15a;
    background: linear-gradient(135deg, rgba(255,161,90,0.08), rgba(26,35,50,0.95));
}
.section-box-c {
    border-left: 4px solid #ef553b;
    background: linear-gradient(135deg, rgba(239,85,59,0.08), rgba(26,35,50,0.95));
}
.section-box-agg {
    border-left: 4px solid #06ffa5;
    background: linear-gradient(135deg, rgba(6,255,165,0.08), rgba(26,35,50,0.95));
}

/* Section titles */
.section-title {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}
.section-title-a { color: #4cc9f0; }
.section-title-b { color: #ffa15a; }
.section-title-c { color: #ef553b; }
.section-title-agg { color: #06ffa5; }

/* Metric boxes */
.metric-box {
    background: rgba(0,0,0,0.2);
    border-radius: 8px;
    padding: 0.6rem;
    text-align: center;
}
.metric-label { font-size: 0.7rem; color: #78909c; margin-bottom: 0.2rem; }
.metric-value { font-size: 1.1rem; font-weight: 600; }
.metric-value-cyan { color: #4cc9f0; }
.metric-value-orange { color: #ffa15a; }
.metric-value-red { color: #ef553b; }
.metric-value-green { color: #06ffa5; }

/* LTV Summary box */
.ltv-summary {
    background: linear-gradient(135deg, rgba(6,255,165,0.15), rgba(76,201,240,0.1));
    border: 2px solid rgba(6,255,165,0.4);
    border-radius: 10px;
    padding: 1rem;
    margin: 1rem 0;
}

/* Compact inputs */
.compact-row { margin-bottom: 0.3rem; }
</style>""", unsafe_allow_html=True)

# =============================================================================
# SECTION 1: PROPERTY & DEAL BASICS
# =============================================================================
st.markdown("""<div class="section-box">
<div class="section-title" style="color:#e0e0e0;">📋 Property & Deal Basics</div>
</div>""", unsafe_allow_html=True)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    property_value = st.number_input(
        "Property Value ($M)", min_value=1, max_value=500,
        value=get_default('property_value_m', 120), step=5, key="prop_val"
    ) * 1_000_000
    save_input('property_value_m', property_value // 1_000_000)

with col2:
    ltv_pct = st.number_input(
        "Total LTV (%)", min_value=50, max_value=90,
        value=get_default('ltv_pct', 85), step=5, key="ltv_input"
    )
    save_input('ltv_pct', ltv_pct)
    ltv = ltv_pct / 100
    loan_amount = property_value * ltv

with col3:
    borrower_bps = st.number_input(
        "Borrower Spread (bps)", min_value=200, max_value=800,
        value=get_default('borrower_bps', 400), step=25, key="borr_spread"
    )
    save_input('borrower_bps', borrower_bps)
    borrower_spread = borrower_bps / 10000

with col4:
    term_months = st.selectbox(
        "Term (months)", [24, 30, 36, 42, 48, 54, 60],
        index=get_default('term_idx', 2), key="term_sel"
    )
    save_input('term_idx', [24, 30, 36, 42, 48, 54, 60].index(term_months))

with col5:
    hud_month = st.number_input(
        "Expected HUD Exit", min_value=12, max_value=60,
        value=get_default('hud_month', 24), key="hud_exit"
    )
    save_input('hud_month', hud_month)

# Calculated metrics row
equity_cushion = property_value - loan_amount
borrower_rate = current_sofr + borrower_spread

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-box"><div class="metric-label">Loan Amount</div><div class="metric-value metric-value-cyan">${loan_amount/1e6:.1f}M</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-box"><div class="metric-label">Borrower Equity</div><div class="metric-value metric-value-green">${equity_cushion/1e6:.1f}M ({1-ltv:.0%})</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'''<div class="metric-box">
        <div class="metric-label">SOFR (30-Day Avg)
            <span title="30-day average SOFR rate from NY Federal Reserve, updated daily" style="cursor:help; color:#4cc9f0; font-size:12px;">ⓘ</span>
        </div>
        <div class="metric-value metric-value-cyan">{current_sofr:.2%}</div>
    </div>''', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-box"><div class="metric-label">Borrower All-In Rate</div><div class="metric-value metric-value-orange">{borrower_rate:.2%}</div></div>', unsafe_allow_html=True)

# Fees row
st.markdown("##### Fees")
fee1, fee2, fee3, fee4 = st.columns(4)

with fee1:
    orig_fee_bps = st.number_input(
        "Origination (bps)", min_value=50, max_value=300,
        value=get_default('orig_fee_bps', 100), step=25, key="orig_fee"
    )
    save_input('orig_fee_bps', orig_fee_bps)
    orig_fee = orig_fee_bps / 10000

with fee2:
    exit_fee_bps = st.number_input(
        "Exit Fee (bps)", min_value=0, max_value=200,
        value=get_default('exit_fee_bps', 50), step=25, key="exit_fee"
    )
    save_input('exit_fee_bps', exit_fee_bps)
    exit_fee = exit_fee_bps / 10000

with fee3:
    ext_fee_bps = st.number_input(
        "Extension (bps)", min_value=0, max_value=200,
        value=get_default('ext_fee_bps', 50), step=25, key="ext_fee"
    )
    save_input('ext_fee_bps', ext_fee_bps)
    ext_fee = ext_fee_bps / 10000

with fee4:
    total_fees = loan_amount * (orig_fee + exit_fee)
    st.markdown(f'<div class="metric-box"><div class="metric-label">Total Fees (Orig+Exit)</div><div class="metric-value metric-value-green">${total_fees:,.0f}</div></div>', unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# SECTION 2: A-PIECE (BANK)
# =============================================================================
st.markdown("""<div class="section-box section-box-a">
<div class="section-title section-title-a">🏦 A-Piece (Senior Bank Debt)</div>
""", unsafe_allow_html=True)

a1, a2, a3, a4, a5 = st.columns([1,1,1,1,1.2])

with a1:
    # Input LTV directly, calculate % of loan
    a_ltv_input = st.number_input(
        "LTV (%)", min_value=40, max_value=80,
        value=get_default('a_ltv', 60), step=5, key="a_ltv_input",
        help="A-Piece LTV position on property"
    )
    save_input('a_ltv', a_ltv_input)
    a_ltv = a_ltv_input / 100
    a_pct = a_ltv / ltv if ltv > 0 else 0  # % of loan = LTV / Total LTV

with a2:
    a_spread_bps = st.number_input(
        "SOFR + (bps)", min_value=100, max_value=400,
        value=get_default('a_spread_bps', 200), step=25, key="a_spread"
    )
    save_input('a_spread_bps', a_spread_bps)
    a_spread = a_spread_bps / 10000

with a3:
    a_fee_alloc = st.number_input(
        "Fee Alloc (%)", min_value=0, max_value=50,
        value=get_default('a_fee_alloc', 10), step=5, key="a_fee_alloc",
        help="Bank's share of fees"
    ) / 100
    save_input('a_fee_alloc', int(a_fee_alloc * 100))

with a4:
    a_amt = loan_amount * a_pct
    st.markdown(f'<div class="metric-box"><div class="metric-label">Amount</div><div class="metric-value metric-value-cyan">${a_amt/1e6:.1f}M</div></div>', unsafe_allow_html=True)

with a5:
    st.markdown(f'<div class="metric-box"><div class="metric-label">% of Loan</div><div class="metric-value metric-value-cyan">{a_pct:.1%}</div></div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# SECTION 3: B-PIECE FUND
# =============================================================================
st.markdown("""<div class="section-box section-box-b">
<div class="section-title section-title-b">📊 B-Piece Fund (Mezzanine)</div>
""", unsafe_allow_html=True)

b1, b2, b3, b4, b5 = st.columns([1,1,1,1,1.2])

with b1:
    # Input LTV directly, calculate % of loan
    b_ltv_input = st.number_input(
        "LTV (%)", min_value=5, max_value=30,
        value=get_default('b_ltv', 17), step=1, key="b_ltv_input",
        help="B-Piece LTV position on property"
    )
    save_input('b_ltv', b_ltv_input)
    b_ltv = b_ltv_input / 100
    b_pct = b_ltv / ltv if ltv > 0 else 0  # % of loan = LTV / Total LTV

with b2:
    b_spread_bps = st.number_input(
        "SOFR + (bps)", min_value=300, max_value=1000,
        value=get_default('b_spread_bps', 600), step=50, key="b_spread"
    )
    save_input('b_spread_bps', b_spread_bps)
    b_spread = b_spread_bps / 10000

with b3:
    b_fee_alloc = st.number_input(
        "Fee Alloc (%)", min_value=0, max_value=50,
        value=get_default('b_fee_alloc', 0), step=5, key="b_fee_alloc"
    ) / 100
    save_input('b_fee_alloc', int(b_fee_alloc * 100))

with b4:
    b_amt = loan_amount * b_pct
    st.markdown(f'<div class="metric-box"><div class="metric-label">Amount</div><div class="metric-value metric-value-orange">${b_amt/1e6:.1f}M</div></div>', unsafe_allow_html=True)

with b5:
    st.markdown(f'<div class="metric-box"><div class="metric-label">% of Loan</div><div class="metric-value metric-value-orange">{b_pct:.1%}</div></div>', unsafe_allow_html=True)

# B-Piece Fund Economics
st.markdown("<div style='margin-top:0.8rem; padding-top:0.8rem; border-top:1px solid rgba(255,161,90,0.2);'><span style='color:#ffa15a; font-size:0.85rem;'>Fund Economics</span></div>", unsafe_allow_html=True)
b_econ1, b_econ2, b_econ3, b_econ4 = st.columns(4)

with b_econ1:
    b_aum_fee = st.number_input(
        "AUM Fee (%/yr)", min_value=0.0, max_value=3.0,
        value=get_default('b_aum_fee', 1.5), step=0.25, format="%.2f", key="b_aum"
    ) / 100
    save_input('b_aum_fee', b_aum_fee * 100)

with b_econ2:
    b_promote = st.number_input(
        "Promote (%)", min_value=0, max_value=30,
        value=get_default('b_promote', 20), step=5, key="b_promote"
    ) / 100
    save_input('b_promote', int(b_promote * 100))

with b_econ3:
    b_hurdle = st.number_input(
        "Hurdle (%)", min_value=0, max_value=15,
        value=get_default('b_hurdle', 8), step=1, key="b_hurdle"
    ) / 100
    save_input('b_hurdle', int(b_hurdle * 100))

with b_econ4:
    b_annual_aum = b_amt * b_aum_fee
    st.markdown(f'<div class="metric-box"><div class="metric-label">Annual AUM Fee</div><div class="metric-value metric-value-orange">${b_annual_aum:,.0f}</div></div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# SECTION 4: C-PIECE FUND
# =============================================================================
# Validate A + B LTV doesn't exceed total LTV
if a_ltv + b_ltv > ltv:
    st.error(f"⚠️ A-Piece LTV ({a_ltv:.0%}) + B-Piece LTV ({b_ltv:.0%}) = {(a_ltv + b_ltv):.0%} exceeds Total LTV ({ltv:.0%}). Please adjust.")
    c_ltv = 0.0
    c_pct = 0.0
else:
    c_ltv = ltv - a_ltv - b_ltv  # Remaining LTV goes to C-Piece
    c_pct = c_ltv / ltv if ltv > 0 else 0  # % of loan

c_amt = loan_amount * c_pct

st.markdown("""<div class="section-box section-box-c">
<div class="section-title section-title-c">🎯 C-Piece Fund (First Loss)</div>
""", unsafe_allow_html=True)

if c_ltv < 0.05 and c_ltv > 0:
    st.warning(f"C-Piece LTV is only {c_ltv:.1%} - may be too thin for first loss cushion")
elif c_ltv == 0:
    st.warning("C-Piece LTV is 0% - adjust A/B LTV allocation")

# Calculate C-piece spread as residual (what's left after A and B)
# C_spread = (borrower_spread - a_spread × a_pct - b_spread × b_pct) / c_pct
if c_pct > 0:
    c_spread = (borrower_spread - a_spread * a_pct - b_spread * b_pct) / c_pct
    c_spread_bps = int(c_spread * 10000)
else:
    c_spread = 0
    c_spread_bps = 0
c_target = current_sofr + c_spread  # Effective rate = SOFR + spread

c1, c2, c3, c4, c5 = st.columns([1,1,1,1,1.2])

with c1:
    st.markdown(f'<div class="metric-box"><div class="metric-label">LTV (Calculated)</div><div class="metric-value metric-value-red">{c_ltv:.1%}</div></div>', unsafe_allow_html=True)
    st.caption(f"({ltv:.0%} - {a_ltv:.0%} - {b_ltv:.0%})")

with c2:
    # C-spread is calculated (residual), not editable
    st.markdown(f'<div class="metric-box"><div class="metric-label">Spread (Residual)</div><div class="metric-value metric-value-red">S+{c_spread_bps:,}bps</div></div>', unsafe_allow_html=True)
    st.caption("Auto-calculated")

with c3:
    c_fee_alloc = st.number_input(
        "Fee Alloc (%)", min_value=0, max_value=50,
        value=get_default('c_fee_alloc', 0), step=5, key="c_fee_alloc"
    ) / 100
    save_input('c_fee_alloc', int(c_fee_alloc * 100))

with c4:
    st.markdown(f'<div class="metric-box"><div class="metric-label">Amount</div><div class="metric-value metric-value-red">${c_amt/1e6:.1f}M</div></div>', unsafe_allow_html=True)

with c5:
    st.markdown(f'<div class="metric-box"><div class="metric-label">Eff. Rate</div><div class="metric-value metric-value-red">{c_target:.2%}</div></div>', unsafe_allow_html=True)
    st.caption(f"SOFR ({current_sofr:.2%}) + {c_spread_bps:,}bps")

# C-Piece Fund Economics
st.markdown("<div style='margin-top:0.8rem; padding-top:0.8rem; border-top:1px solid rgba(239,85,59,0.2);'><span style='color:#ef553b; font-size:0.85rem;'>Fund Economics</span></div>", unsafe_allow_html=True)
c_econ1, c_econ2, c_econ3, c_econ4 = st.columns(4)

with c_econ1:
    c_aum_fee = st.number_input(
        "AUM Fee (%/yr)", min_value=0.0, max_value=3.0,
        value=get_default('c_aum_fee', 2.0), step=0.25, format="%.2f", key="c_aum"
    ) / 100
    save_input('c_aum_fee', c_aum_fee * 100)

with c_econ2:
    c_promote = st.number_input(
        "Promote (%)", min_value=0, max_value=30,
        value=get_default('c_promote', 20), step=5, key="c_promote"
    ) / 100
    save_input('c_promote', int(c_promote * 100))

with c_econ3:
    c_hurdle = st.number_input(
        "Hurdle (%)", min_value=0, max_value=20,
        value=get_default('c_hurdle', 10), step=1, key="c_hurdle"
    ) / 100
    save_input('c_hurdle', int(c_hurdle * 100))

with c_econ4:
    c_annual_aum = c_amt * c_aum_fee  # Placeholder, will recalculate after agg_coinvest
    st.markdown(f'<div class="metric-box"><div class="metric-label">Annual AUM Fee</div><div class="metric-value metric-value-red">${c_annual_aum:,.0f}</div></div>', unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# =============================================================================
# LTV SUMMARY BOX (Green)
# =============================================================================
total_ltv = a_ltv + b_ltv + c_ltv  # Should equal ltv

st.markdown(f"""<div class="ltv-summary">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
<div>
<div style="color:#06ffa5; font-weight:600; font-size:1rem;">Capital Stack Summary</div>
<div style="color:#78909c; font-size:0.8rem;">Total LTV on Property: <strong style="color:#06ffa5;">{ltv:.0%}</strong></div>
</div>
<div style="display:flex; gap:2rem; flex-wrap:wrap;">
<div style="text-align:center;">
<div style="color:#4cc9f0; font-size:1.2rem; font-weight:700;">{a_ltv:.1%}</div>
<div style="color:#78909c; font-size:0.7rem;">A-Piece LTV</div>
</div>
<div style="text-align:center;">
<div style="color:#ffa15a; font-size:1.2rem; font-weight:700;">{b_ltv:.1%}</div>
<div style="color:#78909c; font-size:0.7rem;">B-Piece LTV</div>
</div>
<div style="text-align:center;">
<div style="color:#ef553b; font-size:1.2rem; font-weight:700;">{c_ltv:.1%}</div>
<div style="color:#78909c; font-size:0.7rem;">C-Piece LTV</div>
</div>
<div style="text-align:center; padding-left:1rem; border-left:2px solid rgba(6,255,165,0.3);">
<div style="color:#06ffa5; font-size:1.2rem; font-weight:700;">{1-ltv:.0%}</div>
<div style="color:#78909c; font-size:0.7rem;">Borrower Equity</div>
</div>
</div>
</div>
</div>""", unsafe_allow_html=True)

# =============================================================================
# SECTION 5: AGGREGATOR
# =============================================================================

# Calculate aggregator fee allocation first
total_fee_alloc = a_fee_alloc + b_fee_alloc + c_fee_alloc
if total_fee_alloc > 1.0:
    st.warning(f"⚠️ Fee allocation ({total_fee_alloc:.0%}) exceeds 100%. Aggregator gets 0%.")
    agg_fee_alloc = 0
else:
    agg_fee_alloc = 1 - total_fee_alloc

# Get co-invest input first (needed for deal creation)
st.markdown("""<div class="section-box section-box-agg">
<div class="section-title section-title-agg">💼 Aggregator</div>
""", unsafe_allow_html=True)

agg_orig_fee = loan_amount * orig_fee * agg_fee_alloc
agg_exit_fee = loan_amount * exit_fee * agg_fee_alloc

# Co-invest input in Aggregator section
agg_input1, agg_input2, agg_input3, agg_input4 = st.columns(4)

with agg_input1:
    agg_coinvest = st.number_input(
        "Co-Invest in C (%)", min_value=0, max_value=100,
        value=get_default('agg_coinvest', 10), step=5, key="agg_coinvest",
        help="Aggregator co-invests in C-piece (fee-free)"
    ) / 100
    save_input('agg_coinvest', int(agg_coinvest * 100))

with agg_input2:
    agg_coinvest_amt = c_amt * agg_coinvest
    st.markdown(f'<div class="metric-box"><div class="metric-label">Co-Invest Amount</div><div class="metric-value metric-value-green">${agg_coinvest_amt/1e6:.2f}M</div></div>', unsafe_allow_html=True)

with agg_input3:
    c_lp_capital = c_amt * (1 - agg_coinvest)
    st.markdown(f'<div class="metric-box"><div class="metric-label">C-Fund LP Capital</div><div class="metric-value metric-value-red">${c_lp_capital/1e6:.2f}M</div></div>', unsafe_allow_html=True)

with agg_input4:
    c_annual_aum = c_lp_capital * c_aum_fee  # Recalculate with LP capital only
    total_annual_aum = b_annual_aum + c_annual_aum
    st.markdown(f'<div class="metric-box"><div class="metric-label">Total AUM/yr</div><div class="metric-value metric-value-green">${total_annual_aum:,.0f}</div></div>', unsafe_allow_html=True)

st.markdown("<div style='margin-top:0.8rem;'></div>", unsafe_allow_html=True)

# Calculate deal early so we can show actual promote amounts
try:
    _deal = Deal(
        property_value=property_value,
        loan_amount=loan_amount,
        term_months=term_months,
        expected_hud_month=hud_month,
        tranches=[
            Tranche(TrancheType.A, a_pct, RateType.FLOATING, a_spread, fee_allocation_pct=a_fee_alloc),
            Tranche(TrancheType.B, b_pct, RateType.FLOATING, b_spread, fee_allocation_pct=b_fee_alloc),
            Tranche(TrancheType.C, c_pct, RateType.FLOATING, c_spread, fee_allocation_pct=c_fee_alloc),
        ],
        fees=FeeStructure(origination_fee=orig_fee, exit_fee=exit_fee, extension_fee=ext_fee),
        borrower_spread=borrower_spread,
        b_fund_terms=FundTerms(aum_fee_pct=b_aum_fee, promote_pct=b_promote, hurdle_rate=b_hurdle),
        c_fund_terms=FundTerms(aum_fee_pct=c_aum_fee, promote_pct=c_promote, hurdle_rate=c_hurdle),
        aggregator_coinvest_pct=agg_coinvest,
    )
    _sofr_curve = [current_sofr] * 60
    _fund_results = generate_fund_cashflows(_deal, _sofr_curve, hud_month, has_extension=False)
    _agg_summary = _fund_results.get('aggregator')
    b_promote_amt = _agg_summary.b_fund_promote if _agg_summary else 0
    c_promote_amt = _agg_summary.c_fund_promote if _agg_summary else 0
    total_promote_amt = b_promote_amt + c_promote_amt
except:
    b_promote_amt = 0
    c_promote_amt = 0
    total_promote_amt = 0

agg_col1, agg_col2, agg_col3 = st.columns(3)

with agg_col1:
    st.markdown(f"""<div style="background:rgba(0,0,0,0.2); border-radius:8px; padding:0.8rem;">
<div style="color:#06ffa5; font-weight:600; font-size:0.85rem; margin-bottom:0.5rem;">Fee Income</div>
<div style="display:flex; justify-content:space-between; color:#b0bec5; font-size:0.8rem;">
<span>Origination ({agg_fee_alloc:.0%})</span><span style="color:#e0e0e0;">${agg_orig_fee:,.0f}</span>
</div>
<div style="display:flex; justify-content:space-between; color:#b0bec5; font-size:0.8rem;">
<span>Exit ({agg_fee_alloc:.0%})</span><span style="color:#e0e0e0;">${agg_exit_fee:,.0f}</span>
</div>
<div style="display:flex; justify-content:space-between; color:#06ffa5; font-size:0.9rem; font-weight:600; margin-top:0.5rem; padding-top:0.5rem; border-top:1px solid rgba(6,255,165,0.2);">
<span>Total</span><span>${agg_orig_fee + agg_exit_fee:,.0f}</span>
</div>
</div>""", unsafe_allow_html=True)

with agg_col2:
    # Calculate AUM for hold period
    b_aum_hold = b_annual_aum * (hud_month / 12)
    c_aum_hold = c_annual_aum * (hud_month / 12)
    total_aum_hold = b_aum_hold + c_aum_hold
    st.markdown(f"""<div style="background:rgba(0,0,0,0.2); border-radius:8px; padding:0.8rem;">
<div style="color:#06ffa5; font-weight:600; font-size:0.85rem; margin-bottom:0.5rem;">AUM Fees @ {hud_month}mo</div>
<div style="display:flex; justify-content:space-between; color:#b0bec5; font-size:0.8rem;">
<span>B-Fund ({b_aum_fee:.1%}/yr)</span><span style="color:#ffa15a;">${b_aum_hold:,.0f}</span>
</div>
<div style="display:flex; justify-content:space-between; color:#b0bec5; font-size:0.8rem;">
<span>C-Fund ({c_aum_fee:.1%}/yr)</span><span style="color:#ef553b;">${c_aum_hold:,.0f}</span>
</div>
<div style="display:flex; justify-content:space-between; color:#06ffa5; font-size:0.9rem; font-weight:600; margin-top:0.5rem; padding-top:0.5rem; border-top:1px solid rgba(6,255,165,0.2);">
<span>Total</span><span>${total_aum_hold:,.0f}</span>
</div>
</div>""", unsafe_allow_html=True)

with agg_col3:
    st.markdown(f"""<div style="background:rgba(0,0,0,0.2); border-radius:8px; padding:0.8rem;">
<div style="color:#06ffa5; font-weight:600; font-size:0.85rem; margin-bottom:0.5rem;">Promote (Carry) @ {hud_month}mo</div>
<div style="display:flex; justify-content:space-between; color:#b0bec5; font-size:0.8rem;">
<span>B-Fund ({b_promote:.0%}>{b_hurdle:.0%})</span><span style="color:#ffa15a;">${b_promote_amt:,.0f}</span>
</div>
<div style="display:flex; justify-content:space-between; color:#b0bec5; font-size:0.8rem;">
<span>C-Fund ({c_promote:.0%}>{c_hurdle:.0%})</span><span style="color:#ef553b;">${c_promote_amt:,.0f}</span>
</div>
<div style="display:flex; justify-content:space-between; color:#06ffa5; font-size:0.9rem; font-weight:600; margin-top:0.5rem; padding-top:0.5rem; border-top:1px solid rgba(6,255,165,0.2);">
<span>Total</span><span>${total_promote_amt:,.0f}</span>
</div>
</div>""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# BUILD DEAL & CALCULATE
# =============================================================================

# Save all params to session state
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
    'a_fee_alloc': a_fee_alloc,
    'b_fee_alloc': b_fee_alloc,
    'c_fee_alloc': c_fee_alloc,
    'agg_fee_alloc': agg_fee_alloc,
    'orig_fee': orig_fee,
    'exit_fee': exit_fee,
    'ext_fee': ext_fee,
    'borrower_spread': borrower_spread,
    'current_sofr': current_sofr,
    'borrower_rate': borrower_rate,
    'b_aum_fee': b_aum_fee,
    'b_promote': b_promote,
    'b_hurdle': b_hurdle,
    'c_aum_fee': c_aum_fee,
    'c_promote': c_promote,
    'c_hurdle': c_hurdle,
    'agg_coinvest': agg_coinvest,
    'agg_coinvest_amt': agg_coinvest_amt,
    'is_principal': agg_coinvest > 0,
}

try:
    deal = Deal(
        property_value=property_value,
        loan_amount=loan_amount,
        term_months=term_months,
        expected_hud_month=hud_month,
        tranches=[
            Tranche(TrancheType.A, a_pct, RateType.FLOATING, a_spread, fee_allocation_pct=a_fee_alloc),
            Tranche(TrancheType.B, b_pct, RateType.FLOATING, b_spread, fee_allocation_pct=b_fee_alloc),
            Tranche(TrancheType.C, c_pct, RateType.FLOATING, c_spread, fee_allocation_pct=c_fee_alloc),
        ],
        fees=FeeStructure(origination_fee=orig_fee, exit_fee=exit_fee, extension_fee=ext_fee),
        borrower_spread=borrower_spread,
        b_fund_terms=FundTerms(aum_fee_pct=b_aum_fee, promote_pct=b_promote, hurdle_rate=b_hurdle),
        c_fund_terms=FundTerms(aum_fee_pct=c_aum_fee, promote_pct=c_promote, hurdle_rate=c_hurdle),
        aggregator_coinvest_pct=agg_coinvest,
    )

    sofr_curve = [current_sofr] * 60

    is_principal = agg_coinvest > 0
    results = generate_cashflows(deal, sofr_curve, hud_month, sponsor_is_principal=is_principal)

    fund_results = generate_fund_cashflows(deal, sofr_curve, hud_month, has_extension=False)
    aggregator_summary = fund_results.get('aggregator')

    st.session_state['deal'] = deal
    st.session_state['results'] = results
    st.session_state['fund_results'] = fund_results
    st.session_state['aggregator_summary'] = aggregator_summary

    sponsor = results.get("sponsor")
    irr = sponsor.irr if sponsor else 0
    moic = sponsor.moic if sponsor else 1

except Exception as e:
    st.error(f"Error calculating deal: {e}")
    st.stop()

# =============================================================================
# CAPITAL STACK VISUALIZATION
# =============================================================================

st.markdown("### Capital Stack")

# Create stacked bar chart
fig = go.Figure()

# Add bars in order from bottom to top (C, B, A)
fig.add_trace(go.Bar(
    x=[c_amt], y=[""],
    orientation='h',
    marker_color="#ef553b",
    text=[f"C: {c_pct:.0%}"],
    textposition="inside",
    insidetextanchor="middle",
    textfont={"color": "white", "size": 13, "family": "Arial Black"}
))
fig.add_trace(go.Bar(
    x=[b_amt], y=[""],
    orientation='h',
    marker_color="#ffa15a",
    text=[f"B: {b_pct:.0%}"],
    textposition="inside",
    insidetextanchor="middle",
    textfont={"color": "white", "size": 13, "family": "Arial Black"}
))
fig.add_trace(go.Bar(
    x=[a_amt], y=[""],
    orientation='h',
    marker_color="#4cc9f0",
    text=[f"A: {a_pct:.0%}"],
    textposition="inside",
    insidetextanchor="middle",
    textfont={"color": "white", "size": 13, "family": "Arial Black"}
))

fig.update_layout(
    barmode='stack',
    height=50,
    showlegend=False,
    margin=dict(l=0, r=0, t=0, b=0, pad=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis={"visible": False, "fixedrange": True, "range": [0, loan_amount]},
    yaxis={"visible": False, "fixedrange": True},
    bargap=0,
)

# CSS to remove Streamlit's default padding on plotly charts
st.markdown("""<style>
[data-testid="stPlotlyChart"] > div { padding: 0 !important; }
[data-testid="stPlotlyChart"] iframe { width: 100% !important; }
</style>""", unsafe_allow_html=True)

st.plotly_chart(fig, use_container_width=True, key="capital_stack", config={"displayModeBar": False})

# Tranche summary row
t1, t2, t3 = st.columns(3, gap="small")
with t1:
    st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border-left:3px solid #4cc9f0; padding:0.5rem 0.8rem; border-radius:0 6px 6px 0;">
<strong style="color:#4cc9f0;">A-Piece</strong> <span style="color:#b0bec5; font-size:0.9rem;">{a_ltv:.0%} LTV | ${a_amt/1e6:.1f}M @ S+{a_spread_bps:,}bps</span>
</div>""", unsafe_allow_html=True)
with t2:
    st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-left:3px solid #ffa15a; padding:0.5rem 0.8rem; border-radius:0 6px 6px 0;">
<strong style="color:#ffa15a;">B-Piece</strong> <span style="color:#b0bec5; font-size:0.9rem;">{b_ltv:.0%} LTV | ${b_amt/1e6:.1f}M @ S+{b_spread_bps:,}bps</span>
</div>""", unsafe_allow_html=True)
with t3:
    st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-left:3px solid #ef553b; padding:0.5rem 0.8rem; border-radius:0 6px 6px 0;">
<strong style="color:#ef553b;">C-Piece</strong> <span style="color:#b0bec5; font-size:0.9rem;">{c_ltv:.0%} LTV | ${c_amt/1e6:.1f}M @ S+{c_spread_bps:,}bps</span>
</div>""", unsafe_allow_html=True)

st.markdown("---")

# =============================================================================
# RESULTS SECTION
# =============================================================================

st.markdown("### Returns Analysis")

# Calculated Aggregator Economics - Full Breakdown
if aggregator_summary:
    # Calculate totals for display
    total_fees = aggregator_summary.aggregator_direct_fee_allocation
    total_aum = aggregator_summary.total_aum_fees
    total_promote = aggregator_summary.total_promote
    coinvest_profit = aggregator_summary.coinvest_irr * agg_coinvest_amt if aggregator_summary.coinvest_irr else 0

    st.markdown(f"""<div style="background:linear-gradient(135deg, rgba(6,255,165,0.15), rgba(76,201,240,0.1)); border:2px solid rgba(6,255,165,0.4); border-radius:10px; padding:1.2rem; margin-bottom:1rem;">
<div style="color:#06ffa5; font-weight:600; font-size:1.1rem; margin-bottom:1rem;">Aggregator Economics ({hud_month}mo hold)</div>

<div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:1rem; margin-bottom:1rem;">
<div style="background:rgba(0,0,0,0.2); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#78909c; font-size:0.75rem;">Fee Allocation</div>
<div style="color:#e0e0e0; font-size:1.2rem; font-weight:600;">${total_fees:,.0f}</div>
</div>
<div style="background:rgba(0,0,0,0.2); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#78909c; font-size:0.75rem;">AUM Fees ({hud_month}mo)</div>
<div style="color:#e0e0e0; font-size:1.2rem; font-weight:600;">${total_aum:,.0f}</div>
</div>
<div style="background:rgba(0,0,0,0.2); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#78909c; font-size:0.75rem;">Promote (Carry)</div>
<div style="color:#e0e0e0; font-size:1.2rem; font-weight:600;">${total_promote:,.0f}</div>
<div style="color:#78909c; font-size:0.65rem;">B: ${aggregator_summary.b_fund_promote:,.0f} | C: ${aggregator_summary.c_fund_promote:,.0f}</div>
</div>
<div style="background:rgba(0,0,0,0.2); border-radius:8px; padding:0.8rem; text-align:center;">
<div style="color:#78909c; font-size:0.75rem;">Co-Invest Returns</div>
<div style="color:#e0e0e0; font-size:1.2rem; font-weight:600;">${aggregator_summary.c_fund_coinvest_returns:,.0f}</div>
<div style="color:#78909c; font-size:0.65rem;">on ${agg_coinvest_amt:,.0f}</div>
</div>
</div>

<div style="display:flex; justify-content:space-between; align-items:center; padding-top:0.8rem; border-top:2px solid rgba(6,255,165,0.3);">
<div style="color:#06ffa5; font-weight:600;">Grand Total</div>
<div style="color:#06ffa5; font-size:1.8rem; font-weight:700;">${aggregator_summary.grand_total:,.0f}</div>
</div>
</div>""", unsafe_allow_html=True)

# Get results for gauges
# Use fund_results for A-piece to include fee allocation
a_result = fund_results.get("A")  # Includes fee allocation
b_result = results.get("B")
c_result = results.get("C")
b_fund = fund_results.get('B_fund')
c_fund = fund_results.get('C_fund')

# IRR values
a_irr = a_result.irr if a_result else 0
b_gross_irr = b_result.irr if b_result else 0
b_lp_irr = b_fund.lp_cashflows.irr if b_fund else 0
c_gross_irr = c_result.irr if c_result else 0
c_lp_irr = c_fund.lp_cashflows.irr if c_fund else 0
# Full aggregator IRR (co-invest + fees + AUM + promote + spread)
agg_irr = sponsor.irr if sponsor else 0

# MOIC values
a_moic = a_result.moic if a_result else 1
b_lp_moic = b_fund.lp_cashflows.moic if b_fund else 1
c_lp_moic = c_fund.lp_cashflows.moic if c_fund else 1
agg_moic = sponsor.moic if sponsor else 1

# Dashboard-style IRR Gauges
st.markdown("#### IRR Dashboard")
g1, g2, g3, g4 = st.columns(4)

with g1:
    fig = create_irr_gauge(a_irr, "A-Piece (Bank)", max_val=0.15, thresholds=(0.05, 0.08, 0.12))
    st.plotly_chart(fig, use_container_width=True, key="gauge_a")

with g2:
    fig = create_irr_gauge(b_lp_irr, "B-Fund LP Net", max_val=0.25, thresholds=(0.08, 0.12, 0.18))
    st.plotly_chart(fig, use_container_width=True, key="gauge_b")

with g3:
    fig = create_irr_gauge(c_lp_irr, "C-Fund LP Net", max_val=0.30, thresholds=(0.10, 0.15, 0.20))
    st.plotly_chart(fig, use_container_width=True, key="gauge_c")

with g4:
    # Aggregator IRR can be very high - show as number with info tooltip
    agg_irr_display = f"{agg_irr:.0%}" if agg_irr < 10 else f"{agg_irr*100:,.0f}%"
    st.markdown(f"""<div style="background:rgba(6,255,165,0.1); border-radius:8px; padding:1rem; text-align:center; height:220px; display:flex; flex-direction:column; justify-content:center;">
<div style="color:#78909c; font-size:0.85rem; margin-bottom:0.3rem;">Aggregator IRR
<span title="Aggregator IRR = (Co-invest returns + Fee income + AUM fees + Promote) / Co-invest amount. High IRR reflects fee leverage on minimal capital at risk." style="cursor:help; color:#4cc9f0; font-size:0.7rem; margin-left:0.3rem;">ⓘ</span>
</div>
<div style="color:#06ffa5; font-size:2.5rem; font-weight:700;">{agg_irr_display}</div>
<div style="color:#78909c; font-size:0.75rem; margin-top:0.5rem;">on ${agg_coinvest_amt:,.0f} co-invest</div>
</div>""", unsafe_allow_html=True)

# MOIC Gauges
st.markdown("#### MOIC Dashboard")
m1, m2, m3, m4 = st.columns(4)

with m1:
    fig = create_moic_gauge(a_moic, "A-Piece", max_val=1.5)
    st.plotly_chart(fig, use_container_width=True, key="moic_a")

with m2:
    fig = create_moic_gauge(b_lp_moic, "B-Fund LP", max_val=1.8)
    st.plotly_chart(fig, use_container_width=True, key="moic_b")

with m3:
    fig = create_moic_gauge(c_lp_moic, "C-Fund LP", max_val=2.0)
    st.plotly_chart(fig, use_container_width=True, key="moic_c")

with m4:
    # Aggregator MOIC with profit
    agg_profit = sponsor.total_profit if sponsor else 0
    st.markdown(f"""<div style="background:rgba(6,255,165,0.1); border-radius:8px; padding:1rem; text-align:center; height:220px; display:flex; flex-direction:column; justify-content:center;">
<div style="color:#78909c; font-size:0.85rem; margin-bottom:0.3rem;">Aggregator MOIC</div>
<div style="color:#06ffa5; font-size:2.5rem; font-weight:700;">{agg_moic:.2f}x</div>
<div style="color:#78909c; font-size:0.75rem; margin-top:0.5rem;">Profit: ${agg_profit:,.0f}</div>
</div>""", unsafe_allow_html=True)

# Compact summary cards below gauges
st.markdown("#### Quick Summary")
r1, r2, r3, r4 = st.columns(4)

with r1:
    st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border-radius:8px; padding:0.8rem; text-align:center; border-left:3px solid #4cc9f0;">
<div style="color:#4cc9f0; font-weight:600; font-size:0.85rem;">A-Piece (Bank)</div>
<div style="color:#e0e0e0; font-size:1.4rem; font-weight:700;">{safe_pct(a_irr)}</div>
<div style="color:#78909c; font-size:0.7rem;">IRR | {safe_moic(a_moic)} MOIC</div>
</div>""", unsafe_allow_html=True)

with r2:
    st.markdown(f"""<div style="background:rgba(255,161,90,0.1); border-radius:8px; padding:0.8rem; text-align:center; border-left:3px solid #ffa15a;">
<div style="color:#ffa15a; font-weight:600; font-size:0.85rem;">B-Fund LP Net</div>
<div style="color:#e0e0e0; font-size:1.4rem; font-weight:700;">{safe_pct(b_lp_irr)}</div>
<div style="color:#78909c; font-size:0.7rem;">IRR | {safe_moic(b_lp_moic)} MOIC</div>
</div>""", unsafe_allow_html=True)

with r3:
    st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border-radius:8px; padding:0.8rem; text-align:center; border-left:3px solid #ef553b;">
<div style="color:#ef553b; font-weight:600; font-size:0.85rem;">C-Fund LP Net</div>
<div style="color:#e0e0e0; font-size:1.4rem; font-weight:700;">{safe_pct(c_lp_irr)}</div>
<div style="color:#78909c; font-size:0.7rem;">IRR | {safe_moic(c_lp_moic)} MOIC</div>
</div>""", unsafe_allow_html=True)

with r4:
    agg_irr_short = f"{agg_irr:.0%}" if agg_irr < 10 else f"{agg_irr*100:,.0f}%"
    agg_profit = sponsor.total_profit if sponsor else 0
    st.markdown(f"""<div style="background:rgba(6,255,165,0.1); border-radius:8px; padding:0.8rem; text-align:center; border-left:3px solid #06ffa5;">
<div style="color:#06ffa5; font-weight:600; font-size:0.85rem;">Aggregator <span title="IRR on co-invest capital. High due to fee income leverage." style="cursor:help; font-size:0.7rem;">ⓘ</span></div>
<div style="color:#e0e0e0; font-size:1.4rem; font-weight:700;">{agg_irr_short}</div>
<div style="color:#78909c; font-size:0.7rem;">{agg_moic:.1f}x MOIC | ${agg_profit:,.0f}</div>
</div>""", unsafe_allow_html=True)

st.markdown("---")

# Quick navigation
st.markdown("### Detailed Analysis")
n1, n2, n3, n4 = st.columns(4)
with n1:
    st.page_link("pages/2_Capital_Stack.py", label="📊 Capital Stack", use_container_width=True)
with n2:
    st.page_link("pages/3_Cashflows.py", label="💰 Cashflows", use_container_width=True)
with n3:
    st.page_link("pages/4_Scenarios.py", label="📈 Scenarios", use_container_width=True)
with n4:
    st.page_link("pages/6_Monte_Carlo.py", label="🎲 Monte Carlo", use_container_width=True)
