"""
Monte Carlo Page - Simulation results, distributions, and VaR
Redesigned with better explanations and cleaner layout
"""
import streamlit as st
import numpy as np
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from components.styles import get_page_css, page_header
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator
from components.charts import create_histogram, create_fan_chart
from engine.monte_carlo import (
    run_monte_carlo,
    MonteCarloConfig,
    VasicekParams,
    get_irr_distribution,
    get_sofr_fan_chart_data,
    calculate_probability_metrics,
)


def fmt_pct(val, decimals=1):
    """Format percentage, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.{decimals}%}"


def fmt_currency(val):
    """Format currency, handling inf/nan"""
    if val is None or math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"${val:,.0f}"


# Page config
st.set_page_config(
    page_title="Monte Carlo | HUD Financing",
    page_icon="🎲",
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
coinvest_pct = p.get('agg_coinvest', 0.10)

# Monte Carlo always simulates C-piece investment returns
# This shows what investors (LPs or co-invest) would earn
# Aggregator fee income is shown separately
is_principal = True  # Always simulate C-piece IRR

# Safety check
if deal is None:
    st.warning("⚠️ Deal not properly configured. Please set up your deal in Executive Summary first.")
    st.page_link("pages/1_Executive_Summary.py", label="→ Go to Executive Summary")
    st.stop()

# Header
st.markdown(page_header(
    "Monte Carlo Simulation",
    "Probabilistic analysis with rate path modeling"
), unsafe_allow_html=True)

# Deal Summary Bar
c_pct = p.get('c_pct', 0.10)
c_amt = p['loan_amount'] * c_pct
st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem 1.2rem; margin-bottom:1.5rem; display:flex; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
<span style="color:#b0bec5;">Property: <strong style="color:#4cc9f0;">${p['property_value']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">Loan: <strong style="color:#4cc9f0;">${p['loan_amount']/1e6:.0f}M</strong></span>
<span style="color:#b0bec5;">LTV: <strong style="color:#4cc9f0;">{p['ltv']:.0%}</strong></span>
<span style="color:#b0bec5;">C-Piece: <strong style="color:#ef553b;">${c_amt/1e6:.1f}M ({c_pct:.0%})</strong></span>
<span style="color:#b0bec5;">Exit: <strong style="color:#4cc9f0;">{p['hud_month']}mo</strong></span>
<span style="color:#b0bec5;">SOFR: <strong style="color:#06ffa5;">{p['current_sofr']:.2%}</strong></span>
</div>""", unsafe_allow_html=True)

# Check if C-piece exists and has valid size
if c_pct <= 0 or c_amt <= 0:
    st.error(f"""
    **No C-Piece to simulate!**

    Your capital stack has C-Piece = {c_pct:.0%} (${c_amt:,.0f}).

    Monte Carlo simulates C-Piece investment returns. Please go to Executive Summary
    and ensure A% + B% < 100% so there's a C-Piece.

    **Current stack:** A = {p.get('a_pct', 0):.0%}, B = {p.get('b_pct', 0):.0%}, C = {c_pct:.0%}
    """)
    st.stop()

# Explain what's being simulated
st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border:1px solid rgba(239,85,59,0.2); border-radius:8px; padding:1rem; margin-bottom:1rem;">
<strong style="color:#ef553b;">What This Simulates: C-Piece Investment Returns</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
This Monte Carlo shows returns for <strong>investing in the C-Piece</strong> (${c_amt/1e6:.1f}M first-loss tranche at {c_pct:.0%} of loan).
Whether you're an LP in the C-Fund or the Aggregator co-investing, this is the return profile for that capital.
<br><br>
<span style="color:#78909c;">Note: Fund-level fees (AUM, promote) are not deducted here — this shows <strong>gross C-Piece IRR</strong>.
For LP net returns after fees, see the Scenarios tab.</span>
</div>
</div>""", unsafe_allow_html=True)

# =============================================================================
# EDUCATIONAL SECTION
# =============================================================================
with st.expander("📚 What is Monte Carlo Simulation? (Click to Learn)", expanded=False):
    st.markdown("""
    ### The Problem: We Can't Predict Interest Rates

    In the Scenarios tab, we calculate IRR assuming SOFR stays flat at today's rate.
    But **SOFR moves constantly** — it could spike, drop, or fluctuate wildly.

    **Your floating-rate income depends on where SOFR goes.** So how do you know what your *real* expected return is?

    ---

    ### The Solution: Run 1,000 "What If" Scenarios

    **Monte Carlo simulation** runs your deal through thousands of different interest rate futures:

    | Simulation | SOFR Path | Your IRR |
    |------------|-----------|----------|
    | #1 | Rates rise steadily | 14.2% |
    | #2 | Rates spike then fall | 12.8% |
    | #3 | Rates stay flat | 11.5% |
    | #4 | Rates drop sharply | 9.3% |
    | ... | ... | ... |
    | #1000 | Rates volatile | 13.1% |

    Then we look at all 1,000 IRRs and ask:
    - **What's the average?** (Mean IRR)
    - **What's the worst 5%?** (Downside risk)
    - **What's the spread?** (How uncertain are we?)

    ---

    ### What the Results Tell You

    | Metric | Plain English | Example |
    |--------|---------------|---------|
    | **Mean IRR** | "On average, across all scenarios, you'll earn..." | 12.5% |
    | **5th Percentile** | "In bad scenarios (bottom 5%), you'd only earn..." | 8.0% |
    | **95th Percentile** | "In great scenarios (top 5%), you could earn..." | 17.0% |
    | **Std Deviation** | "How spread out are the outcomes?" | 2.5% = moderate uncertainty |
    | **VaR (95%)** | "95% confident your IRR stays above..." | 8.5% |

    ---

    ### Why SOFR Doesn't Move Like Stocks

    Stock prices can go anywhere. But **interest rates** behave differently:
    - They tend to **revert to a "normal" level** over time
    - The Fed targets a neutral rate (~3-4%)
    - Extreme rates (very high or very low) don't last forever

    This is why we use the **Vasicek model** — it captures this "mean-reverting" behavior.

    ---

    ### Real-World Example

    Let's say SOFR is **4.5% today** and you expect it to drift toward **4.0% long-run**:

    ```
    Month 1:  SOFR = 4.5%  (starting point)
    Month 6:  SOFR = 4.8%  (random spike)
    Month 12: SOFR = 4.3%  (drifting back)
    Month 18: SOFR = 3.9%  (below target)
    Month 24: SOFR = 4.1%  (back near target)
    ```

    Each simulation generates a **different path** like this. Your interest income (and IRR) differs for each path.

    ---

    ### When Default Risk is Included

    If you enable default risk, we also simulate **borrower defaults**:

    1. Each month, there's a small chance the borrower defaults
    2. If they default, the property is sold at a loss (e.g., 65% of value)
    3. Losses flow through the capital stack: **C-Piece → B-Piece → A-Piece**

    This is exactly how **CLOs (Collateralized Loan Obligations)** work — junior tranches absorb losses first.
    """)

st.divider()

# =============================================================================
# SIMULATION PARAMETERS
# =============================================================================
st.markdown("### Simulation Setup")

# Row 1: Basic settings
st.markdown("##### Basic Settings")
basic_col1, basic_col2, basic_col3, basic_col4 = st.columns(4)

with basic_col1:
    num_sims = st.selectbox(
        "Number of Simulations",
        options=[100, 500, 1000, 2500, 5000],
        index=2,
        help="More = more accurate but slower. 1000 is usually sufficient.",
    )

with basic_col2:
    exit_month = st.number_input(
        "Exit Month",
        min_value=12,
        max_value=60,
        value=p['hud_month'],
        step=6,
        help="When HUD takeout occurs"
    )

with basic_col3:
    include_default = st.checkbox(
        "Include Default Risk",
        value=False,
        help="Model borrower defaults - losses flow through tranches like a CLO"
    )

with basic_col4:
    if include_default:
        default_prob = st.number_input(
            "Annual Default Prob (%)",
            min_value=1,
            max_value=10,
            value=2,
            help="1-3% typical for SNFs, 5%+ for distressed properties"
        ) / 100
    else:
        default_prob = 0
        st.markdown("""<div style="padding-top:1.8rem; color:#78909c; font-size:0.85rem;">
        Default risk disabled
        </div>""", unsafe_allow_html=True)

# Default explanation (only show when enabled)
if include_default:
    st.markdown(f"""<div style="background:rgba(239,85,59,0.1); border:1px solid rgba(239,85,59,0.2); border-radius:8px; padding:1rem; margin-top:0.5rem;">
<strong style="color:#ef553b;">How Default Works (CLO-Style Waterfall)</strong>
<div style="color:#b0bec5; font-size:0.85rem; margin-top:0.5rem;">
When a borrower <strong>defaults</strong>, they stop paying and the property is sold at a loss. The losses flow through the capital stack:

<div style="background:rgba(0,0,0,0.2); border-radius:6px; padding:0.8rem; margin:0.8rem 0; font-family:monospace; font-size:0.8rem;">
<div style="color:#ef553b;">LOSS OCCURS</div>
<div style="color:#78909c;">↓</div>
<div><span style="color:#ef553b;">C-Piece absorbs first</span> (first loss / equity tranche)</div>
<div style="color:#78909c;">↓ if loss > C-Piece</div>
<div><span style="color:#ffa15a;">B-Piece absorbs next</span> (mezzanine tranche)</div>
<div style="color:#78909c;">↓ if loss > C + B</div>
<div><span style="color:#4cc9f0;">A-Piece absorbs last</span> (senior / bank tranche)</div>
</div>

<strong>With {default_prob:.0%} annual default probability:</strong>
<ul style="margin:0.3rem 0 0 1rem; padding:0; font-size:0.8rem;">
<li>Each simulation randomly decides if/when default happens</li>
<li>If default occurs, property sells at ~60-70% recovery</li>
<li>C-Fund LPs (and your co-invest) take first hit</li>
<li>This is why C-Piece earns higher returns — it's riskier!</li>
</ul>
</div>
</div>""", unsafe_allow_html=True)

# Row 2: Rate model parameters
st.markdown("##### SOFR Rate Simulation")

st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:1rem; margin-bottom:1rem;">
<strong style="color:#4cc9f0;">What We're Simulating</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
<strong>SOFR</strong> (Secured Overnight Financing Rate) is the benchmark rate that determines your floating-rate interest payments.
When SOFR goes <span style="color:#06ffa5;">up</span>, you earn more interest income. When it goes <span style="color:#ef553b;">down</span>, you earn less.
<br><br>
We simulate <strong>thousands of possible SOFR paths</strong> to see how your returns might vary. The model assumes SOFR:
<ul style="margin:0.3rem 0 0 1rem; padding:0;">
<li>Moves randomly each month (like a stock price)</li>
<li>But tends to drift back toward a "normal" level over time (unlike stocks)</li>
</ul>
</div>
</div>""", unsafe_allow_html=True)

rate_col1, rate_col2, rate_col3 = st.columns(3)

with rate_col1:
    st.markdown("""<div style="background:rgba(6,255,165,0.08); border-radius:8px; padding:0.8rem; margin-bottom:0.5rem;">
<div style="color:#06ffa5; font-weight:600; font-size:0.85rem;">Where Will SOFR Go?</div>
<div style="color:#78909c; font-size:0.75rem;">Long-run target rate</div>
</div>""", unsafe_allow_html=True)

    long_run_mean = st.number_input(
        "SOFR Long-Run Target (%)",
        min_value=1.0,
        max_value=8.0,
        value=4.0,
        step=0.5,
        help="The Federal Reserve's 'neutral' rate is ~2.5-3%. Historical average ~4%. If you think rates will stay high, use 4-5%."
    ) / 100

    st.markdown(f"""<div style="color:#78909c; font-size:0.75rem; padding:0.3rem;">
<strong>Example:</strong> If SOFR is {p['current_sofr']:.1%} today and long-run is {long_run_mean:.1%},
the model expects SOFR to {'rise' if long_run_mean > p['current_sofr'] else 'fall'} over time.
</div>""", unsafe_allow_html=True)

with rate_col2:
    st.markdown("""<div style="background:rgba(255,161,90,0.08); border-radius:8px; padding:0.8rem; margin-bottom:0.5rem;">
<div style="color:#ffa15a; font-weight:600; font-size:0.85rem;">How Fast Does It Get There?</div>
<div style="color:#78909c; font-size:0.75rem;">Speed of mean reversion</div>
</div>""", unsafe_allow_html=True)

    mean_reversion = st.number_input(
        "Reversion Speed (0.1-1.0)",
        min_value=0.1,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="Higher = SOFR snaps back to target faster. 0.3 = moderate (typical). 0.1 = slow drift. 0.8 = quick snapback."
    )

    speed_desc = "slow drift" if mean_reversion < 0.2 else "moderate" if mean_reversion < 0.5 else "fast snapback"
    st.markdown(f"""<div style="color:#78909c; font-size:0.75rem; padding:0.3rem;">
<strong>You chose:</strong> {speed_desc}<br>
If SOFR spikes to 6%, it will return to {long_run_mean:.1%} {'slowly over years' if mean_reversion < 0.2 else 'within 1-2 years' if mean_reversion < 0.5 else 'within months'}.
</div>""", unsafe_allow_html=True)

with rate_col3:
    st.markdown("""<div style="background:rgba(239,85,59,0.08); border-radius:8px; padding:0.8rem; margin-bottom:0.5rem;">
<div style="color:#ef553b; font-weight:600; font-size:0.85rem;">How Bumpy Is the Ride?</div>
<div style="color:#78909c; font-size:0.75rem;">Monthly volatility of SOFR</div>
</div>""", unsafe_allow_html=True)

    volatility = st.number_input(
        "SOFR Volatility (%)",
        min_value=0.5,
        max_value=4.0,
        value=1.5,
        step=0.5,
        help="How much SOFR jumps around month-to-month. 1% = calm markets. 2%+ = turbulent (like 2022-2023)."
    ) / 100

    vol_desc = "calm" if volatility < 0.012 else "normal" if volatility < 0.02 else "volatile"
    vol_example = volatility * 1.5  # ~1.5 std devs for monthly move
    st.markdown(f"""<div style="color:#78909c; font-size:0.75rem; padding:0.3rem;">
<strong>You chose:</strong> {vol_desc} markets<br>
SOFR might swing ±{vol_example:.1%} in a typical month.
Over a year, could move ±{volatility*100:.0f}% from today.
</div>""", unsafe_allow_html=True)

# Visual summary
st.markdown(f"""<div style="background:rgba(26,35,50,0.8); border:1px solid rgba(76,201,240,0.3); border-radius:8px; padding:1rem; margin-top:0.5rem;">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
<div style="text-align:center;">
<div style="color:#78909c; font-size:0.7rem;">TODAY</div>
<div style="color:#4cc9f0; font-size:1.3rem; font-weight:700;">{p['current_sofr']:.2%}</div>
</div>
<div style="color:#78909c; font-size:1.5rem;">→</div>
<div style="text-align:center;">
<div style="color:#78909c; font-size:0.7rem;">DRIFTS TO</div>
<div style="color:#06ffa5; font-size:1.3rem; font-weight:700;">{long_run_mean:.2%}</div>
</div>
<div style="color:#78909c; font-size:1.5rem;">±</div>
<div style="text-align:center;">
<div style="color:#78909c; font-size:0.7rem;">WITH NOISE</div>
<div style="color:#ffa15a; font-size:1.3rem; font-weight:700;">±{volatility:.1%}/yr</div>
</div>
</div>
</div>""", unsafe_allow_html=True)

st.divider()

# =============================================================================
# RUN SIMULATION
# =============================================================================
run_col1, run_col2, run_col3 = st.columns([1, 1, 2])

with run_col1:
    run_button = st.button(
        "🎲 Run Simulation",
        type="primary",
        use_container_width=True,
    )

with run_col2:
    if "mc_result" in st.session_state:
        clear_button = st.button(
            "🗑️ Clear Results",
            type="secondary",
            use_container_width=True,
        )
        if clear_button:
            del st.session_state['mc_result']
            st.rerun()

with run_col3:
    default_text = f" with {default_prob:.1%} default risk" if include_default else ""
    st.markdown(f"""<div style="color:#b0bec5; font-size:0.9rem; padding-top:0.5rem;">
    <strong>{num_sims:,}</strong> simulations × <strong>{exit_month}</strong> months{default_text}
    </div>""", unsafe_allow_html=True)

if run_button:
    try:
        with st.spinner(f"Running {num_sims:,} simulations..."):
            config = MonteCarloConfig(
                num_simulations=num_sims,
                random_seed=42,
                include_default=include_default,
                default_probability=default_prob if include_default else 0,
            )

            vasicek = VasicekParams(
                kappa=mean_reversion,
                theta=long_run_mean,
                sigma=volatility,
                r0=p['current_sofr'],
            )

            # Verify deal configuration
            c_tranche = next((t for t in deal.tranches if t.tranche_type.value == "C"), None)
            if c_tranche is None:
                st.error("C-Tranche not found in deal - cannot run simulation")
                st.stop()

            result = run_monte_carlo(
                deal,
                exit_month,
                config=config,
                vasicek_params=vasicek,
                sponsor_is_principal=is_principal,
            )

            st.session_state.mc_result = result
            st.session_state.mc_params = {
                'num_sims': num_sims,
                'exit_month': exit_month,
                'long_run_mean': long_run_mean,
                'mean_reversion': mean_reversion,
                'volatility': volatility,
                'include_default': include_default,
                'default_prob': default_prob,
            }


    except Exception as e:
        st.error(f"Error running simulation: {str(e)}")
        import traceback
        st.code(traceback.format_exc())

# =============================================================================
# RESULTS
# =============================================================================
if "mc_result" in st.session_state:
    result = st.session_state.mc_result
    params = st.session_state.get('mc_params', {})

    st.divider()

    # Results header
    st.markdown("### Simulation Results")

    # Key metrics in cards
    st.markdown("##### C-Piece Return Distribution")

    metric_label = "C-Piece IRR"  # Always showing C-piece investment returns

    # Row of key metrics
    m1, m2, m3, m4, m5 = st.columns(5)

    with m1:
        st.markdown(f"""<div style="background:rgba(6,255,165,0.15); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#06ffa5; font-weight:600; font-size:0.85rem;">Mean {metric_label}</div>
<div style="color:#e0e0e0; font-size:1.8rem; font-weight:700;">{fmt_pct(result.irr_mean)}</div>
<div style="color:#78909c; font-size:0.75rem;">Expected Return</div>
</div>""", unsafe_allow_html=True)

    with m2:
        st.markdown(f"""<div style="background:rgba(76,201,240,0.15); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#4cc9f0; font-weight:600; font-size:0.85rem;">Median {metric_label}</div>
<div style="color:#e0e0e0; font-size:1.8rem; font-weight:700;">{fmt_pct(result.irr_median)}</div>
<div style="color:#78909c; font-size:0.75rem;">50th Percentile</div>
</div>""", unsafe_allow_html=True)

    with m3:
        st.markdown(f"""<div style="background:rgba(255,161,90,0.15); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#ffa15a; font-weight:600; font-size:0.85rem;">Std Deviation</div>
<div style="color:#e0e0e0; font-size:1.8rem; font-weight:700;">{fmt_pct(result.irr_std)}</div>
<div style="color:#78909c; font-size:0.75rem;">Uncertainty</div>
</div>""", unsafe_allow_html=True)

    with m4:
        st.markdown(f"""<div style="background:rgba(239,85,59,0.15); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#ef553b; font-weight:600; font-size:0.85rem;">5th Percentile</div>
<div style="color:#e0e0e0; font-size:1.8rem; font-weight:700;">{fmt_pct(result.irr_5th)}</div>
<div style="color:#78909c; font-size:0.75rem;">Downside Case</div>
</div>""", unsafe_allow_html=True)

    with m5:
        st.markdown(f"""<div style="background:rgba(76,201,240,0.15); border-radius:8px; padding:1rem; text-align:center;">
<div style="color:#4cc9f0; font-weight:600; font-size:0.85rem;">95th Percentile</div>
<div style="color:#e0e0e0; font-size:1.8rem; font-weight:700;">{fmt_pct(result.irr_95th)}</div>
<div style="color:#78909c; font-size:0.75rem;">Upside Case</div>
</div>""", unsafe_allow_html=True)

    st.divider()

    # IRR Distribution Chart
    st.markdown("##### C-Piece IRR Distribution")

    st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem; margin-bottom:1rem; font-size:0.85rem;">
<strong style="color:#4cc9f0;">How to Read This:</strong>
<span style="color:#b0bec5;"> Each bar shows how many simulations resulted in that IRR range. Taller bars = more likely outcomes. The green line is the mean, red lines are 5th/95th percentiles.</span>
</div>""", unsafe_allow_html=True)

    irr_data = get_irr_distribution(result)

    fig = create_histogram(
        values=irr_data["values"],
        title=f"{metric_label} Distribution ({params.get('num_sims', 1000):,} Simulations)",
        x_title=f"{metric_label} (%)",
        bins=50,
        show_mean=True,
        show_percentiles=True,
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Probability Analysis
    st.markdown("##### Probability of Hitting Targets")

    prob_metrics = calculate_probability_metrics(result)

    prob_col1, prob_col2, prob_col3, prob_col4 = st.columns(4)

    # Helper to create probability card
    def prob_card(prob, label, target, color):
        prob_pct = prob * 100
        bar_width = min(prob * 100, 100)
        return f"""<div style="background:rgba(26,35,50,0.8); border:1px solid rgba(255,255,255,0.1); border-radius:8px; padding:1rem;">
<div style="color:#b0bec5; font-size:0.8rem; margin-bottom:0.3rem;">{label}</div>
<div style="color:{color}; font-size:1.6rem; font-weight:700;">{prob_pct:.0f}%</div>
<div style="background:rgba(255,255,255,0.1); border-radius:4px; height:8px; margin-top:0.5rem;">
<div style="background:{color}; height:100%; width:{bar_width}%; border-radius:4px;"></div>
</div>
<div style="color:#78909c; font-size:0.7rem; margin-top:0.3rem;">chance of {metric_label} > {target}</div>
</div>"""

    with prob_col1:
        st.markdown(prob_card(prob_metrics["prob_positive_irr"], "Break Even", "0%", "#06ffa5"), unsafe_allow_html=True)

    with prob_col2:
        st.markdown(prob_card(prob_metrics["prob_irr_above_10"], "Double Digits", "10%", "#4cc9f0"), unsafe_allow_html=True)

    with prob_col3:
        st.markdown(prob_card(prob_metrics["prob_irr_above_15"], "Strong Return", "15%", "#ffa15a"), unsafe_allow_html=True)

    with prob_col4:
        st.markdown(prob_card(prob_metrics["prob_irr_above_20"], "Exceptional", "20%", "#ef553b"), unsafe_allow_html=True)

    st.divider()

    # SOFR Path Fan Chart
    st.markdown("##### Simulated SOFR Paths")

    st.markdown("""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:0.8rem; margin-bottom:1rem; font-size:0.85rem;">
<strong style="color:#4cc9f0;">How to Read This:</strong>
<span style="color:#b0bec5;"> The shaded area shows the range of SOFR paths across simulations. Darker = more likely. The line shows the median path. Current SOFR: {:.2%} → Long-run target: {:.2%}</span>
</div>""".format(p['current_sofr'], params.get('long_run_mean', 0.04)), unsafe_allow_html=True)

    fan_data = get_sofr_fan_chart_data(result)

    fig = create_fan_chart(
        x=fan_data["months"],
        percentile_data=fan_data["percentiles"],
        title="SOFR Rate Paths (Vasicek Model)",
        x_title="Month",
        y_title="SOFR Rate",
        height=350,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Risk Metrics
    st.markdown("##### Risk Metrics")

    risk_col1, risk_col2 = st.columns(2)

    with risk_col1:
        st.markdown("""<div style="background:rgba(239,85,59,0.1); border:1px solid rgba(239,85,59,0.2); border-radius:8px; padding:1rem;">
<div style="color:#ef553b; font-weight:600; margin-bottom:0.8rem;">Value at Risk (VaR)</div>
<div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
<span style="color:#b0bec5;">VaR (95%)</span>
<span style="color:#e0e0e0; font-weight:600;">{}</span>
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
<span style="color:#b0bec5;">VaR (99%)</span>
<span style="color:#e0e0e0; font-weight:600;">{}</span>
</div>
<div style="display:flex; justify-content:space-between; padding-top:0.5rem; border-top:1px solid rgba(239,85,59,0.3);">
<span style="color:#b0bec5;">Expected Shortfall (95%)</span>
<span style="color:#ef553b; font-weight:600;">{}</span>
</div>
<div style="color:#78909c; font-size:0.75rem; margin-top:0.5rem;">
VaR = worst {} in X% of scenarios. ES = average {} in worst 5%.
</div>
</div>""".format(
            fmt_pct(result.var_95),
            fmt_pct(result.var_99),
            fmt_pct(result.expected_shortfall_95),
            metric_label,
            metric_label,
        ), unsafe_allow_html=True)

    with risk_col2:
        # Additional stats
        moic_display = f"{result.moic_mean:.2f}x" if is_principal and not (math.isinf(result.moic_mean) or math.isnan(result.moic_mean)) else "N/A"
        profit_display = fmt_currency(result.profit_mean)

        st.markdown(f"""<div style="background:rgba(6,255,165,0.1); border:1px solid rgba(6,255,165,0.2); border-radius:8px; padding:1rem;">
<div style="color:#06ffa5; font-weight:600; margin-bottom:0.8rem;">Additional Metrics</div>
<div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
<span style="color:#b0bec5;">Mean MOIC</span>
<span style="color:#e0e0e0; font-weight:600;">{moic_display}</span>
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
<span style="color:#b0bec5;">Mean Profit</span>
<span style="color:#e0e0e0; font-weight:600;">{profit_display}</span>
</div>
<div style="display:flex; justify-content:space-between; margin-bottom:0.5rem;">
<span style="color:#b0bec5;">{metric_label} Range (5th-95th)</span>
<span style="color:#e0e0e0; font-weight:600;">{(result.irr_95th - result.irr_5th)*10000:.0f} bps</span>
</div>
<div style="display:flex; justify-content:space-between; padding-top:0.5rem; border-top:1px solid rgba(6,255,165,0.3);">
<span style="color:#b0bec5;">Simulations Run</span>
<span style="color:#06ffa5; font-weight:600;">{result.config.num_simulations:,}</span>
</div>
</div>""", unsafe_allow_html=True)

    st.divider()

    # Key Insights
    st.markdown("##### Key Insights")

    # Determine insights based on results
    insights = []

    # IRR range insight
    irr_range_bps = (result.irr_95th - result.irr_5th) * 10000
    if irr_range_bps < 200:
        insights.append(("Stable Returns", f"Tight {metric_label} range ({irr_range_bps:.0f} bps) suggests predictable outcomes", "#06ffa5"))
    elif irr_range_bps < 400:
        insights.append(("Moderate Uncertainty", f"{metric_label} range of {irr_range_bps:.0f} bps reflects typical rate risk", "#ffa15a"))
    else:
        insights.append(("High Uncertainty", f"Wide {metric_label} range ({irr_range_bps:.0f} bps) — significant rate exposure", "#ef553b"))

    # Probability insight
    if prob_metrics["prob_irr_above_15"] > 0.8:
        insights.append(("Strong Upside", f"{prob_metrics['prob_irr_above_15']*100:.0f}% chance of >15% {metric_label} — excellent risk/reward", "#06ffa5"))
    elif prob_metrics["prob_irr_above_10"] > 0.9:
        insights.append(("Solid Base Case", f"{prob_metrics['prob_irr_above_10']*100:.0f}% chance of double-digit returns", "#4cc9f0"))
    elif prob_metrics["prob_positive_irr"] < 0.95:
        insights.append(("Loss Risk", f"Only {prob_metrics['prob_positive_irr']*100:.0f}% chance of positive {metric_label} — review structure", "#ef553b"))

    # Default risk insight
    if result.default_rate > 0:
        insights.append(("Default Modeled", f"Simulation includes {result.default_rate:.1%} default rate — impacts downside tail", "#ffa15a"))

    for insight_name, insight_desc, insight_color in insights:
        st.markdown(f"""<div style="display:flex; align-items:center; margin-bottom:0.5rem; padding:0.8rem; background:rgba(255,255,255,0.02); border-radius:8px; border-left:3px solid {insight_color};">
<div>
<div style="color:{insight_color}; font-size:0.95rem; font-weight:600;">{insight_name}</div>
<div style="color:#b0bec5; font-size:0.85rem;">{insight_desc}</div>
</div>
</div>""", unsafe_allow_html=True)

    # Summary recommendation
    if result.irr_mean > 0.12 and prob_metrics["prob_positive_irr"] > 0.95:
        rec_color = "#06ffa5"
        rec_text = "Strong risk-adjusted returns with high probability of positive outcome."
    elif result.irr_mean > 0.08 and prob_metrics["prob_positive_irr"] > 0.90:
        rec_color = "#4cc9f0"
        rec_text = "Acceptable returns with manageable downside risk."
    else:
        rec_color = "#ffa15a"
        rec_text = "Consider adjusting deal structure to improve risk/return profile."

    st.markdown(f"""<div style="background:linear-gradient(135deg, rgba({int(rec_color[1:3], 16)}, {int(rec_color[3:5], 16)}, {int(rec_color[5:7], 16)}, 0.15), rgba(26,35,50,0.9)); border:1px solid {rec_color}; border-radius:8px; padding:1rem; margin-top:1rem;">
<div style="color:{rec_color}; font-weight:600; margin-bottom:0.3rem;">Bottom Line</div>
<div style="color:#e0e0e0;">{rec_text}</div>
</div>""", unsafe_allow_html=True)

else:
    # No results yet - show placeholder
    st.markdown("""<div style="background:rgba(76,201,240,0.05); border:2px dashed rgba(76,201,240,0.3); border-radius:12px; padding:3rem; text-align:center; margin:2rem 0;">
<div style="font-size:3rem; margin-bottom:1rem;">🎲</div>
<div style="color:#4cc9f0; font-size:1.2rem; font-weight:600; margin-bottom:0.5rem;">Ready to Run Simulation</div>
<div style="color:#b0bec5;">Configure parameters above and click "Run Simulation" to see probabilistic results</div>
</div>""", unsafe_allow_html=True)

    # Quick explanation
    st.markdown("### What You'll Get")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""<div style="background:rgba(6,255,165,0.1); border-radius:8px; padding:1rem; height:150px;">
<div style="color:#06ffa5; font-weight:600; margin-bottom:0.5rem;">📊 Return Distribution</div>
<div style="color:#b0bec5; font-size:0.85rem;">
See the full range of possible IRRs — not just one "best guess" but the entire probability distribution.
</div>
</div>""", unsafe_allow_html=True)

    with col2:
        st.markdown("""<div style="background:rgba(76,201,240,0.1); border-radius:8px; padding:1rem; height:150px;">
<div style="color:#4cc9f0; font-weight:600; margin-bottom:0.5rem;">📈 SOFR Paths</div>
<div style="color:#b0bec5; font-size:0.85rem;">
Visualize how interest rates might evolve over your hold period using the Vasicek model.
</div>
</div>""", unsafe_allow_html=True)

    with col3:
        st.markdown("""<div style="background:rgba(239,85,59,0.1); border-radius:8px; padding:1rem; height:150px;">
<div style="color:#ef553b; font-weight:600; margin-bottom:0.5rem;">⚠️ Risk Metrics</div>
<div style="color:#b0bec5; font-size:0.85rem;">
Understand downside risk with VaR, Expected Shortfall, and probability of hitting return targets.
</div>
</div>""", unsafe_allow_html=True)

st.divider()
st.caption("HUD Financing Platform | Monte Carlo Simulation")
