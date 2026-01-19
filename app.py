"""
SNF Bridge Lending Platform - Investor Dashboard
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from engine.deal import Deal, Tranche, TrancheType, RateType, FeeStructure, create_default_deal
from engine.cashflows import generate_cashflows
from engine.scenarios import get_standard_scenarios, get_rate_scenarios, run_scenarios

# Page config
st.set_page_config(
    page_title="SNF Bridge Lending Platform",
    page_icon="🏥",
    layout="wide",
)

st.title("SNF Bridge Lending Platform")
st.markdown("*Dynamic investor dashboard for HUD bridge financing analysis*")

# -----------------------------------------------------------------------------
# SIDEBAR - INPUTS
# -----------------------------------------------------------------------------
st.sidebar.header("Deal Parameters")

# Property & Loan
st.sidebar.subheader("Property & Loan")
property_value = st.sidebar.number_input(
    "Property Value ($)",
    min_value=1_000_000,
    max_value=500_000_000,
    value=120_000_000,
    step=1_000_000,
    format="%d",
)

ltv = st.sidebar.slider(
    "Loan-to-Value (LTV)",
    min_value=0.50,
    max_value=0.90,
    value=0.85,
    step=0.01,
    format="%.0f%%",
)

loan_amount = property_value * ltv
st.sidebar.markdown(f"**Loan Amount: ${loan_amount:,.0f}**")

term_months = st.sidebar.selectbox(
    "Base Term (months)",
    options=[24, 30, 36, 42, 48],
    index=2,
)

expected_hud_month = st.sidebar.slider(
    "Expected HUD Takeout (month)",
    min_value=12,
    max_value=48,
    value=24,
    step=1,
)

# SOFR
st.sidebar.subheader("Interest Rates")
current_sofr = st.sidebar.slider(
    "Current SOFR",
    min_value=0.01,
    max_value=0.08,
    value=0.043,
    step=0.001,
    format="%.2f%%",
)

borrower_spread = st.sidebar.slider(
    "Borrower Spread over SOFR",
    min_value=0.02,
    max_value=0.08,
    value=0.04,
    step=0.005,
    format="%.2f%%",
)

borrower_rate = current_sofr + borrower_spread
st.sidebar.markdown(f"**Borrower All-In Rate: {borrower_rate:.2%}**")

# Tranche Structure
st.sidebar.subheader("Capital Stack")

a_pct = st.sidebar.slider(
    "A-Piece %",
    min_value=0.50,
    max_value=0.85,
    value=0.70,
    step=0.05,
    format="%.0f%%",
)

b_pct = st.sidebar.slider(
    "B-Piece %",
    min_value=0.05,
    max_value=0.40,
    value=0.20,
    step=0.05,
    format="%.0f%%",
)

c_pct = 1 - a_pct - b_pct
if c_pct < 0:
    st.sidebar.error("A + B cannot exceed 100%")
    c_pct = 0
else:
    st.sidebar.markdown(f"**C-Piece (Sponsor): {c_pct:.0%}**")

# Tranche Rates
st.sidebar.subheader("Tranche Pricing")
a_spread = st.sidebar.slider(
    "A-Piece Spread (SOFR +)",
    min_value=0.01,
    max_value=0.04,
    value=0.02,
    step=0.0025,
    format="%.2f%%",
)

b_spread = st.sidebar.slider(
    "B-Piece Spread (SOFR +)",
    min_value=0.03,
    max_value=0.10,
    value=0.06,
    step=0.005,
    format="%.2f%%",
)

c_target = st.sidebar.slider(
    "C-Piece Target Return (Fixed)",
    min_value=0.08,
    max_value=0.25,
    value=0.12,
    step=0.01,
    format="%.0f%%",
)

# Fees
st.sidebar.subheader("Fee Structure")
origination_fee = st.sidebar.slider(
    "Origination Fee",
    min_value=0.005,
    max_value=0.03,
    value=0.01,
    step=0.0025,
    format="%.2f%%",
)

exit_fee = st.sidebar.slider(
    "Exit Fee",
    min_value=0.0,
    max_value=0.02,
    value=0.005,
    step=0.0025,
    format="%.2f%%",
)

extension_fee = st.sidebar.slider(
    "Extension Fee",
    min_value=0.0,
    max_value=0.02,
    value=0.005,
    step=0.0025,
    format="%.2f%%",
)

# -----------------------------------------------------------------------------
# BUILD DEAL
# -----------------------------------------------------------------------------
deal = Deal(
    property_value=property_value,
    loan_amount=loan_amount,
    term_months=term_months,
    expected_hud_month=expected_hud_month,
    tranches=[
        Tranche(TrancheType.A, a_pct, RateType.FLOATING, a_spread),
        Tranche(TrancheType.B, b_pct, RateType.FLOATING, b_spread),
        Tranche(TrancheType.C, c_pct, RateType.FIXED, c_target),
    ],
    fees=FeeStructure(
        origination_fee=origination_fee,
        exit_fee=exit_fee,
        extension_fee=extension_fee,
    ),
    borrower_spread=borrower_spread,
)

# SOFR curve (flat for now)
sofr_curve = [current_sofr] * 60

# Generate base case cashflows
base_results = generate_cashflows(
    deal=deal,
    sofr_curve=sofr_curve,
    exit_month=expected_hud_month,
    has_extension=False,
)

# -----------------------------------------------------------------------------
# MAIN DASHBOARD
# -----------------------------------------------------------------------------

# Key Metrics Row
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Sponsor IRR",
        f"{base_results['sponsor'].irr:.1%}",
        help="Annualized IRR for sponsor (C-piece + fees)",
    )

with col2:
    st.metric(
        "Sponsor MOIC",
        f"{base_results['sponsor'].moic:.2f}x",
        help="Multiple on Invested Capital",
    )

with col3:
    st.metric(
        "Total Profit",
        f"${base_results['sponsor'].total_profit:,.0f}",
        help="Total dollar profit to sponsor",
    )

with col4:
    blended_cost = deal.get_blended_cost_of_capital(current_sofr)
    spread_capture = borrower_rate - blended_cost
    st.metric(
        "Spread Capture",
        f"{spread_capture:.2%}",
        help="Borrower rate minus blended cost of capital",
    )

st.divider()

# -----------------------------------------------------------------------------
# TABS
# -----------------------------------------------------------------------------
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "📖 How It Works",
    "📊 Capital Stack",
    "💰 Cashflows",
    "📈 Scenarios",
    "🎯 Borrower View",
])

# TAB 0: Business Model Explainer
with tab0:
    st.subheader("The Business Model")

    st.markdown("""
    ### The Problem We Solve

    **Skilled Nursing Facility (SNF) owners** need financing to buy or refinance properties.
    The best long-term option is a **HUD loan** (government-backed, low rates), but these take
    **6-12+ months to close**. Owners can't wait that long.

    **We provide bridge financing** — short-term loans that "bridge" the gap until HUD closes.
    """)

    st.divider()

    st.markdown("### How We Make Money")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 1. Interest Spread")
        st.markdown(f"""
        The borrower pays us **{borrower_rate:.2%}** interest.

        We fund the loan using cheaper capital:
        - A-Piece (bank): **{current_sofr + a_spread:.2%}**
        - B-Piece (investors): **{current_sofr + b_spread:.2%}**
        - C-Piece (us): **{c_target:.2%}**

        **Blended cost: {deal.get_blended_cost_of_capital(current_sofr):.2%}**

        The difference (**{spread_capture:.2%}**) is profit.
        """)

        annual_spread = loan_amount * spread_capture
        st.metric("Annual Spread Income", f"${annual_spread:,.0f}")

    with col2:
        st.markdown("#### 2. Fee Income")

        orig_income = deal.fees.calculate_origination(loan_amount)
        exit_income = deal.fees.calculate_exit(loan_amount)
        ext_income = deal.fees.calculate_extension(loan_amount)

        st.markdown(f"""
        | Fee | Rate | Amount |
        |-----|------|--------|
        | **Origination** (upfront) | {origination_fee:.2%} | ${orig_income:,.0f} |
        | **Exit** (at HUD payoff) | {exit_fee:.2%} | ${exit_income:,.0f} |
        | **Extension** (if delayed) | {extension_fee:.2%} | ${ext_income:,.0f} |
        """)

        st.metric("Total Fee Income", f"${orig_income + exit_income:,.0f}")

    st.divider()

    st.markdown("### The Capital Stack (A/B/C Tranches)")

    st.markdown("""
    We don't fund the whole loan ourselves. We split it into **risk layers**:
    """)

    # Visual capital stack
    c_amt = deal.get_tranche_amount(deal.tranches[2])
    b_amt = deal.get_tranche_amount(deal.tranches[1])
    a_amt = deal.get_tranche_amount(deal.tranches[0])

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=["Capital Stack"],
        y=[c_amt],
        name=f"C-Piece (Sponsor) - ${c_amt/1e6:.0f}M",
        marker_color="#ef553b",
        text=[f"C: {c_pct:.0%}<br>${c_amt/1e6:.0f}M<br>Highest Risk<br>Paid Last"],
        textposition="inside",
    ))
    fig.add_trace(go.Bar(
        x=["Capital Stack"],
        y=[b_amt],
        name=f"B-Piece (Investors) - ${b_amt/1e6:.0f}M",
        marker_color="#ffa15a",
        text=[f"B: {b_pct:.0%}<br>${b_amt/1e6:.0f}M<br>Medium Risk"],
        textposition="inside",
    ))
    fig.add_trace(go.Bar(
        x=["Capital Stack"],
        y=[a_amt],
        name=f"A-Piece (Bank) - ${a_amt/1e6:.0f}M",
        marker_color="#00cc96",
        text=[f"A: {a_pct:.0%}<br>${a_amt/1e6:.0f}M<br>Lowest Risk<br>Paid First"],
        textposition="inside",
    ))

    fig.update_layout(
        barmode="stack",
        height=400,
        showlegend=True,
        yaxis_title="Amount ($)",
        yaxis_tickformat="$,.0f",
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        **A-Piece (Senior)**
        - Funded by banks/credit lines
        - Lowest rate (SOFR + 2%)
        - Paid **first** — lowest risk
        - If deal goes bad, they recover first
        """)

    with col2:
        st.markdown("""
        **B-Piece (Mezzanine)**
        - Funded by yield investors
        - Higher rate (SOFR + 6%)
        - Paid after A-Piece
        - Takes losses after A is made whole
        """)

    with col3:
        st.markdown("""
        **C-Piece (Equity/Sponsor)**
        - Funded by **us**
        - Highest return target (12%+)
        - Paid **last** — highest risk
        - BUT: we also get **all the fees**
        """)

    st.divider()

    st.markdown("### Why Sponsor Returns Are So High")

    st.markdown(f"""
    With this deal structure:

    | Your Investment | ${c_amt:,.0f} |
    |-----------------|---------------|
    | Origination Fee (Day 1) | +${orig_income:,.0f} |
    | Monthly Spread + Interest | +${(annual_spread + c_amt * c_target) / 12:,.0f}/mo |
    | Exit Fee (at HUD) | +${exit_income:,.0f} |

    **Key insight:** Fees are calculated on the **full loan** (${loan_amount:,.0f}),
    but you only invest the **C-Piece** (${c_amt:,.0f}).

    That's why sponsor IRR is **{base_results['sponsor'].irr:.1%}** — you get fees on ~{loan_amount/c_amt:.0f}x your capital.
    """)

    st.divider()

    st.markdown("### Why Borrowers Choose Us")

    st.info(f"""
    **Our headline rate: {borrower_rate:.2%}**

    Traditional bridge lenders charge SOFR + 5-6%. We charge SOFR + {borrower_spread:.2%}.

    We can offer lower rates because:
    1. We make money on **fees**, not just spread
    2. Our capital stack is **efficient** (cheap A-piece from banks)
    3. We're optimizing for **volume**, not margin

    Lower monthly payments = more borrowers = more deals = more fee income.
    """)

# TAB 1: Capital Stack
with tab1:
    st.subheader("Capital Stack Structure")

    col1, col2 = st.columns([1, 2])

    with col1:
        # Tranche table
        tranche_data = []
        for t in deal.tranches:
            amount = deal.get_tranche_amount(t)
            rate = t.get_rate(current_sofr)
            tranche_data.append({
                "Tranche": t.name,
                "% of Loan": f"{t.percentage:.0%}",
                "Amount": f"${amount:,.0f}",
                "Rate Type": t.rate_type.value.title(),
                "Current Rate": f"{rate:.2%}",
                "IRR": f"{base_results[t.tranche_type.value].irr:.1%}",
            })

        st.dataframe(
            pd.DataFrame(tranche_data),
            hide_index=True,
            use_container_width=True,
        )

        # Fee summary
        st.markdown("**Fee Income**")
        orig_income = deal.fees.calculate_origination(loan_amount)
        exit_income = deal.fees.calculate_exit(loan_amount)
        st.markdown(f"- Origination: **${orig_income:,.0f}**")
        st.markdown(f"- Exit: **${exit_income:,.0f}**")
        st.markdown(f"- **Total: ${orig_income + exit_income:,.0f}**")

    with col2:
        # Waterfall chart
        fig = go.Figure(go.Waterfall(
            name="Capital Stack",
            orientation="v",
            x=["Property Value", "LTV Haircut", "Loan Amount", "A-Piece", "B-Piece", "C-Piece"],
            y=[
                property_value,
                -(property_value - loan_amount),
                0,
                -deal.get_tranche_amount(deal.tranches[0]),
                -deal.get_tranche_amount(deal.tranches[1]),
                -deal.get_tranche_amount(deal.tranches[2]),
            ],
            measure=["absolute", "relative", "total", "relative", "relative", "relative"],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#ef553b"}},
            increasing={"marker": {"color": "#00cc96"}},
            totals={"marker": {"color": "#636efa"}},
        ))
        fig.update_layout(
            title="Deal Structure Waterfall",
            showlegend=False,
            height=400,
        )
        st.plotly_chart(fig, use_container_width=True)

# TAB 2: Cashflows
with tab2:
    st.subheader("Monthly Cashflows")

    view_option = st.radio(
        "View",
        ["Sponsor", "A-Piece", "B-Piece", "C-Piece"],
        horizontal=True,
    )

    view_key = view_option.replace("-Piece", "").replace("Sponsor", "sponsor")
    cf_data = base_results[view_key]

    # Cashflow chart
    df_cf = pd.DataFrame({
        "Month": cf_data.months,
        "Principal": cf_data.principal_flows,
        "Interest": cf_data.interest_flows,
        "Fees": cf_data.fee_flows,
        "Net": cf_data.total_flows,
    })

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_cf["Month"], y=df_cf["Principal"], name="Principal", marker_color="#636efa"))
    fig.add_trace(go.Bar(x=df_cf["Month"], y=df_cf["Interest"], name="Interest", marker_color="#00cc96"))
    fig.add_trace(go.Bar(x=df_cf["Month"], y=df_cf["Fees"], name="Fees", marker_color="#ffa15a"))
    fig.add_trace(go.Scatter(x=df_cf["Month"], y=df_cf["Net"], name="Net CF", mode="lines+markers", line=dict(color="white", width=2)))

    fig.update_layout(
        barmode="relative",
        title=f"{view_option} Monthly Cashflows",
        xaxis_title="Month",
        yaxis_title="Cashflow ($)",
        height=450,
        yaxis_tickformat="$,.0f",
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("IRR", f"{cf_data.irr:.1%}")
    with col2:
        st.metric("MOIC", f"{cf_data.moic:.2f}x")
    with col3:
        st.metric("Total Profit", f"${cf_data.total_profit:,.0f}")

# TAB 3: Scenarios
with tab3:
    st.subheader("Scenario Analysis")

    scenario_type = st.radio(
        "Scenario Type",
        ["HUD Timing", "Rate Shocks"],
        horizontal=True,
    )

    if scenario_type == "HUD Timing":
        scenarios = get_standard_scenarios(deal)
    else:
        scenarios = get_rate_scenarios(current_sofr)

    results = run_scenarios(deal, scenarios, sofr_curve)

    # Results table
    scenario_df = pd.DataFrame([
        {
            "Scenario": r.scenario.name,
            "Sponsor IRR": f"{r.sponsor_irr:.1%}",
            "Sponsor MOIC": f"{r.sponsor_moic:.2f}x",
            "Profit": f"${r.sponsor_profit:,.0f}",
            "A IRR": f"{r.a_irr:.1%}",
            "B IRR": f"{r.b_irr:.1%}",
            "C IRR": f"{r.c_irr:.1%}",
        }
        for r in results
    ])

    st.dataframe(scenario_df, hide_index=True, use_container_width=True)

    # IRR comparison chart
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[r.scenario.name for r in results],
        y=[r.sponsor_irr * 100 for r in results],
        name="Sponsor IRR",
        marker_color="#636efa",
    ))
    fig.add_trace(go.Bar(
        x=[r.scenario.name for r in results],
        y=[r.a_irr * 100 for r in results],
        name="A-Piece IRR",
        marker_color="#00cc96",
    ))
    fig.add_trace(go.Bar(
        x=[r.scenario.name for r in results],
        y=[r.b_irr * 100 for r in results],
        name="B-Piece IRR",
        marker_color="#ffa15a",
    ))

    fig.update_layout(
        barmode="group",
        title="IRR by Scenario",
        yaxis_title="IRR (%)",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

# TAB 4: Borrower View
with tab4:
    st.subheader("Borrower Economics")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Rate Comparison")

        # Build comparison data
        comparison = [
            {"Item": "Base Rate (SOFR)", "Rate": f"{current_sofr:.2%}"},
            {"Item": "Our Spread", "Rate": f"+{borrower_spread:.2%}"},
            {"Item": "**Borrower Rate**", "Rate": f"**{borrower_rate:.2%}**"},
            {"Item": "---", "Rate": "---"},
            {"Item": "Origination Fee", "Rate": f"{origination_fee:.2%}"},
            {"Item": "Exit Fee", "Rate": f"{exit_fee:.2%}"},
        ]
        st.table(pd.DataFrame(comparison))

        # Effective all-in cost estimate
        total_fee_pct = origination_fee + exit_fee
        # Annualize fees over expected term
        annualized_fees = total_fee_pct * 12 / expected_hud_month
        all_in_cost = borrower_rate + annualized_fees

        st.metric(
            "Estimated All-In Cost (Annualized)",
            f"{all_in_cost:.2%}",
            help="Borrower rate + annualized fees",
        )

    with col2:
        st.markdown("### Competitive Positioning")

        # Market comparison (illustrative)
        market_data = pd.DataFrame({
            "Lender": ["Traditional Bridge", "Bank", "Our Platform"],
            "Rate": [current_sofr + 0.055, current_sofr + 0.045, borrower_rate],
            "Orig Fee": [0.02, 0.015, origination_fee],
            "Exit Fee": [0.01, 0.005, exit_fee],
        })

        # Calculate all-in for each
        market_data["All-In"] = market_data["Rate"] + (market_data["Orig Fee"] + market_data["Exit Fee"]) * 12 / expected_hud_month

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=market_data["Lender"],
            y=market_data["All-In"] * 100,
            marker_color=["#ef553b", "#ffa15a", "#00cc96"],
        ))
        fig.update_layout(
            title="All-In Cost Comparison",
            yaxis_title="All-In Cost (%)",
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

        savings = (market_data["All-In"].iloc[0] - market_data["All-In"].iloc[2]) * loan_amount / 100
        st.success(f"Borrower saves ~${savings:,.0f} annually vs traditional bridge")

# Footer
st.divider()
st.caption("SNF Bridge Lending Platform | Built for investor analysis")
