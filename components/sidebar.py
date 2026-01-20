"""
Professional sidebar component with SOFR indicator for HUD Financing Platform
"""
import streamlit as st
from pathlib import Path
from typing import Optional, Callable
import sys
sys.path.append(str(Path(__file__).parent.parent))

from engine.sofr import get_live_sofr, format_sofr_display, SOFRData
from components.styles import (
    CYAN_PRIMARY, MINT_ACCENT, TEXT_SECONDARY, TEXT_MUTED,
    SUCCESS_GREEN, DARK_BG_SECONDARY,
)


def render_logo():
    """Render the logo in sidebar - aligned right"""
    logo_path = Path(__file__).parent.parent / "Assets" / "logo.png"
    if logo_path.exists():
        st.sidebar.markdown(
            f'<div style="text-align: right; padding: 0.5rem 0;"><img src="data:image/png;base64,{_get_base64_image(logo_path)}" width="140"></div>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            f"""<div style="text-align: right; padding: 0.5rem 0;">
<span style="font-size: 1.2rem; font-weight: 700; background: linear-gradient(90deg, {CYAN_PRIMARY}, {MINT_ACCENT}); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">Ascendra</span>
</div>""",
            unsafe_allow_html=True,
        )


def _get_base64_image(image_path: Path) -> str:
    """Convert image to base64 for inline HTML"""
    import base64
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def render_sofr_indicator(manual_override: Optional[float] = None) -> SOFRData:
    """
    Render live SOFR indicator in sidebar

    Args:
        manual_override: Optional manual SOFR rate to display

    Returns:
        SOFRData object with current rate
    """
    if manual_override is not None:
        sofr_data = SOFRData(
            rate=manual_override,
            timestamp=__import__("datetime").datetime.now(),
            source="manual",
            observation_date=None,
        )
    else:
        sofr_data = get_live_sofr()

    display = format_sofr_display(sofr_data)

    # Status indicator
    if display["is_live"]:
        status_html = f'<span class="live-dot"></span>LIVE'
        status_color = SUCCESS_GREEN
    elif display["is_stale"]:
        status_html = '<span style="color: #ffa15a;">CACHED (Stale)</span>'
        status_color = "#ffa15a"
    elif sofr_data.source == "manual":
        status_html = '<span style="color: #ab63fa;">MANUAL</span>'
        status_color = "#ab63fa"
    else:
        status_html = '<span style="color: #78909c;">FALLBACK</span>'
        status_color = TEXT_MUTED

    st.sidebar.markdown(
        f"""
        <style>
        .live-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            background: {SUCCESS_GREEN};
            border-radius: 50%;
            margin-right: 6px;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
        }}
        </style>
        <div style="
            background: linear-gradient(145deg, {DARK_BG_SECONDARY}, rgba(26, 35, 50, 0.9));
            border: 1px solid rgba(76, 201, 240, 0.3);
            border-radius: 10px;
            padding: 0.75rem 1rem;
            margin-bottom: 1rem;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.7rem; color: {TEXT_SECONDARY};
                    text-transform: uppercase; letter-spacing: 0.05em;">
                        Current SOFR
                    </div>
                    <div style="font-size: 1.5rem; font-weight: 700; color: {CYAN_PRIMARY};">
                        {display['rate']}
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 0.65rem; color: {status_color};">
                        {status_html}
                    </div>
                    <div style="font-size: 0.6rem; color: {TEXT_MUTED};">
                        {display['timestamp']}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    return sofr_data


def render_section_header(title: str):
    """Render a styled section header in sidebar"""
    st.sidebar.markdown(
        f"""
        <div style="
            margin: 1rem 0 0.5rem 0;
            padding-bottom: 0.3rem;
            border-bottom: 1px solid rgba(76, 201, 240, 0.2);
            font-size: 0.8rem;
            font-weight: 600;
            color: {CYAN_PRIMARY};
            text-transform: uppercase;
            letter-spacing: 0.1em;
        ">
            {title}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_deal_summary(
    property_value: float,
    loan_amount: float,
    ltv: float,
    sponsor_irr: Optional[float] = None,
):
    """Render deal summary card in sidebar"""
    irr_html = ""
    if sponsor_irr is not None:
        irr_html = f"""
        <div style="display: flex; justify-content: space-between; margin-top: 0.5rem;
        padding-top: 0.5rem; border-top: 1px solid rgba(76, 201, 240, 0.15);">
            <span style="color: {TEXT_SECONDARY}; font-size: 0.75rem;">Sponsor IRR</span>
            <span style="color: {MINT_ACCENT}; font-weight: 600;">{sponsor_irr:.1%}</span>
        </div>
        """

    st.sidebar.markdown(
        f"""
        <div style="
            background: rgba(76, 201, 240, 0.05);
            border: 1px solid rgba(76, 201, 240, 0.15);
            border-radius: 8px;
            padding: 0.75rem;
            margin: 0.5rem 0;
        ">
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <span style="color: {TEXT_SECONDARY}; font-size: 0.75rem;">Property</span>
                <span style="color: {TEXT_SECONDARY}; font-weight: 500;">${property_value/1e6:.1f}M</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <span style="color: {TEXT_SECONDARY}; font-size: 0.75rem;">Loan</span>
                <span style="color: {CYAN_PRIMARY}; font-weight: 600;">${loan_amount/1e6:.1f}M</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: {TEXT_SECONDARY}; font-size: 0.75rem;">LTV</span>
                <span style="color: {TEXT_SECONDARY}; font-weight: 500;">{ltv:.0%}</span>
            </div>
            {irr_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_logout_button():
    """Render logout button in sidebar"""
    st.sidebar.markdown("<div style='margin-top: 2rem;'></div>", unsafe_allow_html=True)
    if st.sidebar.button("Logout", key="sidebar_logout"):
        st.session_state.authenticated = False
        st.rerun()


def create_deal_inputs():
    """
    Create standard deal input widgets in sidebar.

    Returns:
        dict with all deal parameters
    """
    render_section_header("Property & Loan")

    property_value = st.sidebar.number_input(
        "Property Value ($)",
        min_value=1_000_000,
        max_value=500_000_000,
        value=120_000_000,
        step=1_000_000,
        format="%d",
        help="Appraised value of the skilled nursing facility",
    )

    ltv = st.sidebar.slider(
        "Loan-to-Value (LTV)",
        min_value=0.50,
        max_value=0.90,
        value=0.85,
        step=0.01,
        format="%.0f%%",
        help="Loan amount as percentage of property value",
    )

    loan_amount = property_value * ltv

    st.sidebar.markdown(
        f"<div style='color: {CYAN_PRIMARY}; font-weight: 600; margin: 0.5rem 0;'>"
        f"Loan Amount: ${loan_amount:,.0f}</div>",
        unsafe_allow_html=True,
    )

    term_months = st.sidebar.selectbox(
        "Base Term (months)",
        options=[24, 30, 36, 42, 48],
        index=2,
        help="Initial loan term before extensions",
    )

    expected_hud_month = st.sidebar.slider(
        "Expected HUD Takeout (month)",
        min_value=12,
        max_value=48,
        value=24,
        step=1,
        help="Month when HUD refinancing is expected",
    )

    # Interest Rates Section
    render_section_header("Interest Rates")

    use_manual_sofr = st.sidebar.checkbox(
        "Use Manual SOFR",
        value=False,
        help="Override live SOFR with manual entry",
    )

    if use_manual_sofr:
        current_sofr = st.sidebar.slider(
            "Manual SOFR Rate",
            min_value=0.01,
            max_value=0.08,
            value=0.043,
            step=0.001,
            format="%.2f%%",
        )
        sofr_data = render_sofr_indicator(manual_override=current_sofr)
    else:
        sofr_data = render_sofr_indicator()
        current_sofr = sofr_data.rate

    borrower_spread = st.sidebar.slider(
        "Borrower Spread over SOFR",
        min_value=0.02,
        max_value=0.08,
        value=0.04,
        step=0.005,
        format="%.2f%%",
        help="Interest rate spread charged to borrower",
    )

    borrower_rate = current_sofr + borrower_spread
    st.sidebar.markdown(
        f"<div style='color: {MINT_ACCENT}; font-weight: 600; margin: 0.5rem 0;'>"
        f"Borrower All-In Rate: {borrower_rate:.2%}</div>",
        unsafe_allow_html=True,
    )

    # Capital Stack Section
    render_section_header("Capital Stack")

    a_pct = st.sidebar.slider(
        "A-Piece %",
        min_value=0.50,
        max_value=0.85,
        value=0.70,
        step=0.05,
        format="%.0f%%",
        help="Senior tranche (bank funding)",
    )

    b_pct = st.sidebar.slider(
        "B-Piece %",
        min_value=0.05,
        max_value=0.40,
        value=0.20,
        step=0.05,
        format="%.0f%%",
        help="Mezzanine tranche (yield investors)",
    )

    c_pct = 1 - a_pct - b_pct
    if c_pct < 0:
        st.sidebar.error("A + B cannot exceed 100%")
        c_pct = 0
    else:
        st.sidebar.markdown(
            f"<div style='color: #ef553b; font-weight: 600;'>"
            f"C-Piece (Sponsor): {c_pct:.0%}</div>",
            unsafe_allow_html=True,
        )

    # Tranche Pricing
    render_section_header("Tranche Pricing")

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

    # Fee Structure
    render_section_header("Fee Structure")

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

    return {
        "property_value": property_value,
        "loan_amount": loan_amount,
        "ltv": ltv,
        "term_months": term_months,
        "expected_hud_month": expected_hud_month,
        "current_sofr": current_sofr,
        "sofr_data": sofr_data,
        "borrower_spread": borrower_spread,
        "borrower_rate": borrower_rate,
        "a_pct": a_pct,
        "b_pct": b_pct,
        "c_pct": c_pct,
        "a_spread": a_spread,
        "b_spread": b_spread,
        "c_target": c_target,
        "origination_fee": origination_fee,
        "exit_fee": exit_fee,
        "extension_fee": extension_fee,
    }
