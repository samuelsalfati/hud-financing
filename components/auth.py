"""
Password protection component for HUD Financing Platform
"""
import streamlit as st
import hashlib
from typing import Optional

# Default password hash (password: "ascendra2024")
# In production, use environment variables or secrets management
DEFAULT_PASSWORD_HASH = hashlib.sha256("ascendra2024".encode()).hexdigest()


def get_password_hash() -> str:
    """Get password hash from secrets or use default"""
    try:
        # Try to get from Streamlit secrets
        if hasattr(st, 'secrets') and "PASSWORD_HASH" in st.secrets:
            return st.secrets["PASSWORD_HASH"]
    except:
        pass
    return DEFAULT_PASSWORD_HASH


def verify_password(password: str) -> bool:
    """Verify password against stored hash"""
    input_hash = hashlib.sha256(password.encode()).hexdigest()
    return input_hash == get_password_hash()


def check_password() -> bool:
    """
    Display password protection screen if not authenticated.

    Returns True if authenticated, False otherwise.
    Shows login form when not authenticated.
    """
    # Check if already authenticated
    if st.session_state.get("authenticated", False):
        return True

    # Get custom CSS for login page
    login_css = """
    <style>
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 2rem;
        background: linear-gradient(145deg, #1a2332, rgba(26, 35, 50, 0.9));
        border: 1px solid rgba(76, 201, 240, 0.3);
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }

    .login-header {
        text-align: center;
        margin-bottom: 2rem;
    }

    .login-title {
        font-size: 1.8rem;
        font-weight: 700;
        background: linear-gradient(90deg, #4cc9f0, #06ffa5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }

    .login-subtitle {
        color: #b0bec5;
        font-size: 0.9rem;
    }

    .login-logo {
        width: 120px;
        margin-bottom: 1rem;
        filter: drop-shadow(0 0 10px rgba(76, 201, 240, 0.3));
    }

    .stTextInput > div > div {
        background: rgba(10, 25, 41, 0.8) !important;
        border: 1px solid rgba(76, 201, 240, 0.3) !important;
        border-radius: 8px !important;
    }

    .stTextInput input {
        color: #ffffff !important;
    }

    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #4cc9f0, #3ab8df) !important;
        color: #0a1929 !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.75rem !important;
        margin-top: 1rem !important;
    }

    .stButton > button:hover {
        box-shadow: 0 4px 15px rgba(76, 201, 240, 0.4) !important;
    }

    .error-msg {
        color: #ef553b;
        text-align: center;
        margin-top: 1rem;
        font-size: 0.85rem;
    }
    </style>
    """

    st.markdown(login_css, unsafe_allow_html=True)

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("""
        <div class="login-header">
            <div class="login-title">HUD Financing Platform</div>
            <div class="login-subtitle">Investment Analysis Dashboard</div>
        </div>
        """, unsafe_allow_html=True)

        # Password input
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter password",
            key="password_input",
            label_visibility="collapsed",
        )

        # Login button
        if st.button("Login", key="login_button"):
            if verify_password(password):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.markdown(
                    '<p class="error-msg">Invalid password. Please try again.</p>',
                    unsafe_allow_html=True,
                )

        # Demo hint (remove in production)
        with st.expander("Demo Access"):
            st.caption("Default password: `ascendra2024`")

    return False


def logout():
    """Log out the current user"""
    st.session_state.authenticated = False
    st.rerun()


def require_auth(func):
    """Decorator to require authentication for a function"""
    def wrapper(*args, **kwargs):
        if not check_password():
            st.stop()
        return func(*args, **kwargs)
    return wrapper


def get_auth_header() -> Optional[str]:
    """Returns logout button HTML if authenticated"""
    if st.session_state.get("authenticated", False):
        return """
        <div style="position: fixed; top: 10px; right: 10px; z-index: 9999;">
            <button onclick="logout()" style="
                background: rgba(239, 85, 59, 0.2);
                color: #ef553b;
                border: 1px solid rgba(239, 85, 59, 0.3);
                border-radius: 6px;
                padding: 0.5rem 1rem;
                font-size: 0.8rem;
                cursor: pointer;
            ">Logout</button>
        </div>
        """
    return None
