"""
HUD Financing Platform - Ascendra-Styled Investment Analysis Dashboard
Main entry point for the multi-page Streamlit application
"""
import streamlit as st
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from components.styles import get_page_css, page_header, CYAN_PRIMARY, MINT_ACCENT
from components.auth import check_password
from components.sidebar import render_logo, render_sofr_indicator, render_section_header

# Page config - must be first Streamlit command
st.set_page_config(
    page_title="HUD Financing Platform",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Auth check
if not check_password():
    st.stop()

# Apply Ascendra styling
st.markdown(get_page_css(), unsafe_allow_html=True)

# Sidebar - SOFR first, then logo
render_sofr_indicator()
render_logo()

# Main content
st.markdown(page_header(
    "HUD Financing Platform",
    "Professional Investment Analysis for SNF Bridge Lending"
), unsafe_allow_html=True)

# Welcome section
st.markdown("""<div style="background: linear-gradient(145deg, #1a2332, rgba(26, 35, 50, 0.9)); border: 1px solid rgba(76, 201, 240, 0.3); border-radius: 16px; padding: 2rem; margin: 2rem 0;">
<h3 style="color: #4cc9f0; margin-bottom: 1rem;">Welcome to the Platform</h3>
<p style="color: #b0bec5; line-height: 1.6;">This comprehensive investment analysis platform provides sophisticated tools for analyzing HUD bridge financing opportunities in the skilled nursing facility sector.</p>
<p style="color: #b0bec5; line-height: 1.6;">Use the <strong style="color: #4cc9f0;">sidebar navigation</strong> to access different analysis modules, or select a page from the menu on the left.</p>
</div>""", unsafe_allow_html=True)

# Feature highlights
st.subheader("Platform Features")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""<div style="background: rgba(76, 201, 240, 0.1); border: 1px solid rgba(76, 201, 240, 0.2); border-radius: 12px; padding: 1.5rem; height: 200px;">
<h4 style="color: {CYAN_PRIMARY};">Live Market Data</h4>
<p style="color: #b0bec5; font-size: 0.9rem;">Real-time SOFR rates from FRED API with 15-minute caching. Always know current market conditions.</p>
</div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""<div style="background: rgba(6, 255, 165, 0.1); border: 1px solid rgba(6, 255, 165, 0.2); border-radius: 12px; padding: 1.5rem; height: 200px;">
<h4 style="color: {MINT_ACCENT};">Advanced Analytics</h4>
<p style="color: #b0bec5; font-size: 0.9rem;">Monte Carlo simulation, sensitivity analysis, and loss waterfall modeling for comprehensive risk assessment.</p>
</div>""", unsafe_allow_html=True)

with col3:
    st.markdown("""<div style="background: rgba(255, 161, 90, 0.1); border: 1px solid rgba(255, 161, 90, 0.2); border-radius: 12px; padding: 1.5rem; height: 200px;">
<h4 style="color: #ffa15a;">Export & Reporting</h4>
<p style="color: #b0bec5; font-size: 0.9rem;">Generate Excel workbooks, CSV exports, and deal summaries. Save and compare multiple deals.</p>
</div>""", unsafe_allow_html=True)

st.divider()

# Quick start
st.subheader("Quick Start")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### New Deal Analysis
    1. Navigate to **Executive Summary**
    2. Configure deal parameters using the tabs
    3. Review key metrics and recommendation
    4. Explore detailed analysis in other pages
    """)

with col2:
    st.markdown("""
    ### Load Existing Deal
    1. Go to **Export Center**
    2. Select from saved deals
    3. Or load a deal template
    4. Modify parameters as needed
    """)

st.divider()

# How it works section
st.subheader("How the Business Model Works")

st.markdown("""<div style="background: linear-gradient(145deg, #1a2332, rgba(26, 35, 50, 0.9)); border: 1px solid rgba(76, 201, 240, 0.2); border-radius: 12px; padding: 1.5rem; margin: 1rem 0;">
<h4 style="color: #4cc9f0;">The Problem We Solve</h4>
<p style="color: #b0bec5;">SNF owners need financing to acquire or refinance properties. HUD loans offer the best terms but take 6-12+ months to close. We provide <strong style="color: #4cc9f0;">bridge financing</strong> that "bridges" the gap until HUD closes.</p>
<h4 style="color: #06ffa5; margin-top: 1.5rem;">How We Make Money</h4>
<p style="color: #b0bec5;"><strong>1. Interest Spread:</strong> We charge borrowers SOFR + spread, but fund with cheaper capital from our A/B/C tranche structure.<br><strong>2. Fee Income:</strong> Origination, exit, and extension fees calculated on the full loan but only require C-piece capital investment.</p>
</div>""", unsafe_allow_html=True)

# Footer
st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.caption("HUD Financing Platform v2.0")

with col2:
    st.caption("Ascendra Investment Analytics")

with col3:
    st.caption("Built with Streamlit")
