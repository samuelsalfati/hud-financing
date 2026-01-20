"""
Monte Carlo Page - Simulation results, distributions, and VaR
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
from components.charts import create_histogram, create_fan_chart, create_line_chart, create_multi_line_chart
from components.gauges import create_probability_gauge, create_irr_gauge
from engine.monte_carlo import (
    run_monte_carlo,
    MonteCarloConfig,
    VasicekParams,
    get_irr_distribution,
    get_sofr_fan_chart_data,
    calculate_probability_metrics,
    run_stress_test,
)


def fmt_pct(val):
    """Format percentage, handling inf/nan"""
    if math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.1%}"


def fmt_pct2(val):
    """Format percentage with 2 decimals, handling inf/nan"""
    if math.isinf(val) or math.isnan(val):
        return "N/A"
    return f"{val:.2%}"

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
is_principal = p.get('is_principal', True)

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

# Purpose explanation
st.markdown("""<div style="background:rgba(6,255,165,0.08); border:1px solid rgba(6,255,165,0.2); border-radius:8px; padding:1rem; margin-bottom:1.5rem;">
<strong style="color:#06ffa5;">📊 What is Monte Carlo Simulation?</strong>
<div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
Monte Carlo simulation runs <strong>thousands of random scenarios</strong> to understand the range of possible outcomes for your investment. Instead of a single "best guess" IRR, you get a probability distribution showing:
<ul style="margin:0.5rem 0 0 1rem; padding:0;">
<li><strong>Most likely returns</strong> (median/mean IRR)</li>
<li><strong>Downside risk</strong> (5th percentile, VaR)</li>
<li><strong>Upside potential</strong> (95th percentile)</li>
<li><strong>Probability of hitting targets</strong> (P(IRR > 15%), etc.)</li>
</ul>
</div>
</div>""", unsafe_allow_html=True)

# Simulation Parameters
st.subheader("Simulation Parameters")

# Rate Type Selection
st.markdown("#### Rate Type Analysis")
rate_type_col1, rate_type_col2 = st.columns([1, 2])

with rate_type_col1:
    rate_type = st.radio(
        "Rate Structure",
        ["Floating Rate (SOFR)", "Fixed Rate", "Compare Both"],
        help="Floating = SOFR + spread, varies monthly | Fixed = locked rate at origination",
        key="mc_rate_type"
    )

with rate_type_col2:
    if rate_type == "Fixed Rate" or rate_type == "Compare Both":
        default_fixed = (p['current_sofr'] + 0.04) * 100  # SOFR + typical spread, as percentage
        fixed_rate_pct = st.number_input(
            "Fixed Rate (%)",
            min_value=3.0,
            max_value=20.0,
            value=round(default_fixed, 2),
            step=0.25,
            format="%.2f",
            help="All-in fixed rate for borrower (e.g., 8.50 for 8.50%)",
        )
        fixed_rate = fixed_rate_pct / 100  # Convert back to decimal
    else:
        fixed_rate = None

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Basic Parameters**")
    num_sims = st.selectbox(
        "Number of Simulations",
        options=[100, 500, 1000, 2500, 5000],
        index=2,
        help="More simulations = more accurate but slower. 1000 is typically sufficient.",
    )

    st.markdown("""<div style="font-size:0.8rem; color:#6c757d; margin-top:0.5rem;">
    💡 Each simulation generates a different SOFR path and calculates the resulting IRR
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown("**Default Risk**")
    include_default = st.checkbox(
        "Include Default Risk",
        value=False,
        help="Model potential borrower defaults in simulation",
    )

    if include_default:
        default_prob = st.slider(
            "Annual Default Probability",
            min_value=0.01,
            max_value=0.10,
            value=0.02,
            format="%.1f%%",
            help="SNF bridge loans: 1-3% typical, 5%+ for distressed",
        )
        st.markdown("""<div style="font-size:0.8rem; color:#6c757d; margin-top:0.5rem;">
        💡 Default = borrower fails to repay. C-piece takes first loss.
        </div>""", unsafe_allow_html=True)
    else:
        default_prob = 0

with col3:
    st.markdown("**Vasicek Rate Model**")

    with st.expander("ℹ️ What is the Vasicek Model?", expanded=False):
        st.markdown("""
        The **Vasicek model** simulates how SOFR rates might evolve over time. It assumes rates:

        - **Mean-revert**: Tend to drift back toward a long-term average
        - **Are random**: Subject to daily/monthly fluctuations

        **Formula:** `dS = κ(θ - S)dt + σdW`

        Where:
        - `κ` (kappa) = speed of mean reversion
        - `θ` (theta) = long-run equilibrium rate
        - `σ` (sigma) = volatility of rate changes
        """)

    mean_reversion = st.slider(
        "Mean Reversion Speed (κ)",
        min_value=0.1,
        max_value=1.0,
        value=0.3,
        help="Higher = rates snap back to mean faster. 0.3 = moderate (typical market)",
    )

    long_run_mean = st.slider(
        "Long-Run Mean (θ)",
        min_value=0.02,
        max_value=0.08,
        value=0.04,
        format="%.2f%%",
        help="Where SOFR trends toward. Fed's 'neutral' rate is ~2.5-3%, historical avg ~4%",
    )

    volatility = st.slider(
        "Rate Volatility (σ)",
        min_value=0.005,
        max_value=0.04,
        value=0.015,
        format="%.3f",
        help="How much rates fluctuate. 0.015 = normal, 0.03+ = high volatility period",
    )

    st.markdown(f"""<div style="font-size:0.8rem; color:#6c757d; margin-top:0.5rem;">
    Current SOFR: <strong>{p['current_sofr']:.2%}</strong> → Model expects drift toward <strong>{long_run_mean:.2%}</strong>
    </div>""", unsafe_allow_html=True)

# Run simulation button
st.divider()
run_col1, run_col2 = st.columns([1, 3])
with run_col1:
    run_button = st.button("🎲 Run Monte Carlo Simulation", type="primary", use_container_width=True)

with run_col2:
    st.markdown(f"""<div style="color:#b0bec5; font-size:0.9rem; padding-top:0.5rem;">
    Will run <strong>{num_sims}</strong> simulations for <strong>{rate_type}</strong> structure
    {f'with <strong>{default_prob:.1%}</strong> annual default risk' if include_default else '(no default risk)'}
    </div>""", unsafe_allow_html=True)

if run_button:
    try:
        with st.spinner(f"Running {num_sims} simulations..."):
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

            # Run floating rate simulation
            result_float = run_monte_carlo(
                deal,
                p['hud_month'],
                config=config,
                vasicek_params=vasicek,
                sponsor_is_principal=is_principal,
            )

            # Store results
            st.session_state.mc_result = result_float
            st.session_state.mc_rate_type = rate_type

            # If comparing both, also run fixed rate
            if rate_type == "Fixed Rate" or rate_type == "Compare Both":
                # For fixed rate, create a flat SOFR curve that results in same all-in rate
                # Essentially, the "SOFR" is constant at a level that gives fixed_rate as all-in
                implied_flat_sofr = fixed_rate - 0.04  # Approximate, depends on spread structure
                fixed_vasicek = VasicekParams(
                    kappa=10.0,  # Very high mean reversion = nearly constant
                    theta=implied_flat_sofr,
                    sigma=0.0001,  # Near-zero volatility
                    r0=implied_flat_sofr,
                )

                result_fixed = run_monte_carlo(
                    deal,
                    p['hud_month'],
                    config=config,
                    vasicek_params=fixed_vasicek,
                    sponsor_is_principal=is_principal,
                )
                st.session_state.mc_result_fixed = result_fixed
                st.session_state.mc_fixed_rate = fixed_rate

    except Exception as e:
        st.error(f"Error running simulation: {str(e)}")

# Display results if available
if "mc_result" in st.session_state:
    result = st.session_state.mc_result
    stored_rate_type = st.session_state.get('mc_rate_type', 'Floating Rate (SOFR)')

    st.divider()

    # Float vs Fixed Comparison (if applicable)
    if stored_rate_type == "Compare Both" and "mc_result_fixed" in st.session_state:
        result_fixed = st.session_state.mc_result_fixed
        stored_fixed_rate = st.session_state.get('mc_fixed_rate', 0.08)

        st.subheader("📊 Floating vs Fixed Rate Comparison")

        st.markdown(f"""<div style="background:rgba(76,201,240,0.08); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:1rem; margin-bottom:1rem;">
        <strong style="color:#4cc9f0;">Rate Structure Analysis</strong>
        <div style="color:#b0bec5; font-size:0.9rem; margin-top:0.5rem;">
        Comparing <strong>Floating Rate</strong> (SOFR + spread, rate varies monthly) vs <strong>Fixed Rate</strong> ({stored_fixed_rate:.2%} locked all-in rate).
        Floating rates expose you to rate risk but may outperform if rates fall.
        </div>
        </div>""", unsafe_allow_html=True)

        comp_col1, comp_col2, comp_col3 = st.columns(3)

        metric_label = "IRR" if is_principal else "Yield"

        with comp_col1:
            st.markdown("**Metric**")
            st.markdown(f"Mean {metric_label}")
            st.markdown(f"Median {metric_label}")
            st.markdown("Std Dev (Risk)")
            st.markdown("5th Percentile")
            st.markdown("95th Percentile")

        with comp_col2:
            st.markdown("**Floating Rate**")
            st.markdown(f"**{fmt_pct(result.irr_mean)}**")
            st.markdown(fmt_pct(result.irr_median))
            st.markdown(fmt_pct(result.irr_std))
            st.markdown(fmt_pct(result.irr_5th))
            st.markdown(fmt_pct(result.irr_95th))

        with comp_col3:
            st.markdown("**Fixed Rate**")
            st.markdown(f"**{fmt_pct(result_fixed.irr_mean)}**")
            st.markdown(fmt_pct(result_fixed.irr_median))
            st.markdown(fmt_pct(result_fixed.irr_std))
            st.markdown(fmt_pct(result_fixed.irr_5th))
            st.markdown(fmt_pct(result_fixed.irr_95th))

        # Recommendation
        float_better = result.irr_mean > result_fixed.irr_mean
        float_riskier = result.irr_std > result_fixed.irr_std
        spread = abs(result.irr_mean - result_fixed.irr_mean)

        if float_better and spread > 0.01:
            rec_text = f"**Floating rate** shows higher expected {metric_label.lower()} (+{spread:.1%}), but with higher volatility. Suitable if you can tolerate rate risk."
            rec_color = "#06ffa5"
        elif not float_better and spread > 0.01:
            rec_text = f"**Fixed rate** shows higher expected {metric_label.lower()} (+{spread:.1%}) with lower volatility. More predictable returns."
            rec_color = "#4cc9f0"
        else:
            rec_text = f"Both structures show similar expected returns (within {spread:.1%}). Fixed provides more certainty."
            rec_color = "#b0bec5"

        st.markdown(f"""<div style="background:rgba(6,255,165,0.1); border-left:4px solid {rec_color}; padding:1rem; margin:1rem 0; border-radius:0 8px 8px 0;">
        <strong style="color:{rec_color};">Recommendation:</strong>
        <div style="color:#e0e0e0;">{rec_text}</div>
        </div>""", unsafe_allow_html=True)

        st.divider()

    # Key Statistics
    metric_label = "IRR" if is_principal else "Yield"
    st.subheader(f"{metric_label} Distribution Statistics")

    # Aggregator mode notice
    if not is_principal:
        st.markdown("""<div style="background:rgba(6,255,165,0.1); border:1px solid rgba(6,255,165,0.2); border-radius:8px; padding:0.8rem; margin-bottom:1rem; font-size:0.9rem;">
        <strong style="color:#06ffa5;">Aggregator Mode:</strong> As aggregator, you earn fees without capital at risk.
        "Yield" represents your fee income as an annualized return on deal volume.
        </div>""", unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(f"Mean {metric_label}", fmt_pct(result.irr_mean))
        st.metric("Std Dev", fmt_pct(result.irr_std))

    with col2:
        st.metric(f"Median {metric_label}", fmt_pct(result.irr_median))
        st.metric("5th Percentile", fmt_pct(result.irr_5th))

    with col3:
        st.metric("95th Percentile", fmt_pct(result.irr_95th))
        st.metric("VaR (95%)", fmt_pct(result.var_95))

    with col4:
        st.metric("Expected Shortfall", fmt_pct(result.expected_shortfall_95))
        if result.default_rate > 0:
            st.metric("Default Rate", fmt_pct(result.default_rate))

    st.divider()

    # IRR Distribution Histogram
    st.subheader(f"{metric_label} Distribution")

    irr_data = get_irr_distribution(result)

    fig = create_histogram(
        values=irr_data["values"],
        title=f"Monte Carlo {metric_label} Distribution",
        x_title=metric_label,
        bins=50,
        show_mean=True,
        show_percentiles=True,
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Probability metrics
    prob_metrics = calculate_probability_metrics(result)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        fig = create_probability_gauge(
            prob_metrics["prob_positive_irr"],
            f"P({metric_label} > 0%)",
            invert_colors=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = create_probability_gauge(
            prob_metrics["prob_irr_above_10"],
            f"P({metric_label} > 10%)",
            invert_colors=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col3:
        fig = create_probability_gauge(
            prob_metrics["prob_irr_above_15"],
            f"P({metric_label} > 15%)",
            invert_colors=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = create_probability_gauge(
            prob_metrics["prob_irr_above_20"],
            f"P({metric_label} > 20%)",
            invert_colors=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # SOFR Path Fan Chart
    st.subheader("SOFR Path Distribution")

    fan_data = get_sofr_fan_chart_data(result)

    fig = create_fan_chart(
        x=fan_data["months"],
        percentile_data=fan_data["percentiles"],
        title="Simulated SOFR Paths (Vasicek Model)",
        x_title="Month",
        y_title="SOFR Rate",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Summary Statistics Table
    st.subheader("Detailed Statistics")

    stats_data = [
        {"Metric": "Number of Simulations", "Value": f"{result.config.num_simulations:,}"},
        {"Metric": f"Mean {metric_label}", "Value": fmt_pct2(result.irr_mean)},
        {"Metric": "Standard Deviation", "Value": fmt_pct2(result.irr_std)},
        {"Metric": f"Median {metric_label}", "Value": fmt_pct2(result.irr_median)},
        {"Metric": "5th Percentile", "Value": fmt_pct2(result.irr_5th)},
        {"Metric": "25th Percentile", "Value": fmt_pct2(result.irr_25th)},
        {"Metric": "75th Percentile", "Value": fmt_pct2(result.irr_75th)},
        {"Metric": "95th Percentile", "Value": fmt_pct2(result.irr_95th)},
        {"Metric": "Value at Risk (95%)", "Value": fmt_pct2(result.var_95)},
        {"Metric": "Value at Risk (99%)", "Value": fmt_pct2(result.var_99)},
        {"Metric": "Expected Shortfall (95%)", "Value": fmt_pct2(result.expected_shortfall_95)},
    ]

    # Only show MOIC for Principal mode
    if is_principal:
        moic_str = f"{result.moic_mean:.2f}x" if not math.isinf(result.moic_mean) and not math.isnan(result.moic_mean) else "N/A"
        stats_data.append({"Metric": "Mean MOIC", "Value": moic_str})

    profit_str = f"${result.profit_mean:,.0f}" if not math.isinf(result.profit_mean) and not math.isnan(result.profit_mean) else "N/A"
    stats_data.append({"Metric": "Mean Profit", "Value": profit_str})

    if result.default_rate > 0:
        stats_data.extend([
            {"Metric": "Simulated Default Rate", "Value": fmt_pct2(result.default_rate)},
            {"Metric": "Loss Given Default", "Value": f"{result.loss_given_default:.0%}"},
        ])

    st.dataframe(stats_data, use_container_width=True, hide_index=True)

    # Key insights
    irr_range_bps = (result.irr_95th - result.irr_5th) * 10000
    st.markdown(f"""<div style="background:rgba(76,201,240,0.1); border:1px solid rgba(76,201,240,0.2); border-radius:8px; padding:1rem; margin:1rem 0;">
    <strong style="color:#4cc9f0;">📈 Monte Carlo Insights</strong>
    <ul style="color:#e0e0e0; margin:0.5rem 0 0 1rem; padding:0;">
        <li>There is a <strong>{prob_metrics['prob_irr_above_15']*100:.0f}%</strong> probability of achieving {metric_label} > 15%</li>
        <li><strong>95% VaR:</strong> In the worst 5% of scenarios, {metric_label} falls below <strong>{fmt_pct(result.var_95)}</strong></li>
        <li>The {metric_label} range (5th-95th percentile) is <strong>{irr_range_bps:.0f} bps</strong></li>
        <li>{'<strong style="color:#ff6b6b;">Default risk</strong> contributes to downside tail - consider credit enhancement' if result.default_rate > 0 else '<strong>Rate volatility</strong> is the primary risk driver'}</li>
    </ul>
    </div>""", unsafe_allow_html=True)

else:
    st.info("👆 Configure parameters above and click 'Run Monte Carlo Simulation' to generate probabilistic analysis")

    # Show example interpretation
    st.markdown("""
    ### How Monte Carlo Works

    The simulation models thousands of possible future outcomes:

    | Step | What Happens |
    |------|--------------|
    | 1️⃣ | **Generate SOFR paths** - Simulate how rates might evolve using Vasicek model |
    | 2️⃣ | **Calculate cashflows** - For each path, compute monthly interest, fees, principal |
    | 3️⃣ | **Compute returns** - Calculate IRR/yield for each scenario |
    | 4️⃣ | **Aggregate statistics** - Mean, median, percentiles, VaR |

    ### Key Risk Metrics Explained

    | Metric | What It Means |
    |--------|--------------|
    | **Mean/Median IRR** | Expected return (median is more robust to outliers) |
    | **Standard Deviation** | How much returns vary - higher = more uncertainty |
    | **5th Percentile** | "Bad case" - 95% of outcomes are better than this |
    | **95th Percentile** | "Good case" - only 5% of outcomes are better |
    | **VaR (95%)** | Value at Risk - worst IRR in 95% of cases |
    | **Expected Shortfall** | Average loss when things go really wrong (worst 5%) |

    ### Floating vs Fixed Rate

    - **Floating (SOFR + spread)**: Your return varies with interest rates
      - ✅ Benefits if rates rise (higher interest income)
      - ❌ Hurts if rates fall
    - **Fixed Rate**: Locked return regardless of rate movements
      - ✅ Predictable, easier to model
      - ❌ May underperform if rates rise
    """)

st.divider()
st.caption("HUD Financing Platform | Monte Carlo Simulation")
