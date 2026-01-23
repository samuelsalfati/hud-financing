"""
Live SOFR data fetching from FRED API
Includes 15-minute cache and fallback to manual entry
"""
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple
import os

# FRED API endpoint for SOFR
FRED_SOFR_SERIES = "SOFR"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"

# Cache settings
CACHE_DURATION_MINUTES = 15

# Default SOFR for fallback (30-day avg, updated Jan 2025)
DEFAULT_SOFR = 0.0370  # 3.70% (30-day average)

# Module-level cache
_sofr_cache: dict = {
    "value": None,
    "timestamp": None,
    "source": None,
}


@dataclass
class SOFRData:
    """SOFR data with metadata"""
    rate: float  # As decimal (0.05 = 5%)
    timestamp: datetime
    source: str  # "live", "cached", "manual"
    observation_date: Optional[str] = None  # Date of FRED observation


def get_fred_api_key() -> Optional[str]:
    """Get FRED API key from environment or .env file"""
    # Try environment variable first
    api_key = os.environ.get("FRED_API_KEY")
    if api_key:
        return api_key

    # Try loading from .env file
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith("FRED_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"\'')

    return None


def fetch_sofr_from_nyfed(use_30day_avg: bool = True) -> Tuple[Optional[float], Optional[str]]:
    """
    Fetch SOFR rate from NY Fed API (no API key required)

    Args:
        use_30day_avg: If True, calculate 30-day average; otherwise use daily rate

    Returns:
        Tuple of (rate as decimal, observation date range) or (None, None) on failure
    """
    # Fetch last 30 days to calculate average
    days_to_fetch = 30 if use_30day_avg else 1
    NYFED_SOFR_URL = f"https://markets.newyorkfed.org/api/rates/secured/sofr/last/{days_to_fetch}.json"

    try:
        response = requests.get(NYFED_SOFR_URL, timeout=10)
        response.raise_for_status()

        data = response.json()
        rates = data.get("refRates", [])

        if rates:
            if use_30day_avg and len(rates) > 1:
                # Calculate 30-day average
                avg_rate = sum(r["percentRate"] for r in rates) / len(rates)
                rate_decimal = avg_rate / 100
                # Date range for display
                date = f"30-day avg (as of {rates[0].get('effectiveDate', '')})"
            else:
                # Single day rate
                latest = rates[0]
                rate_pct = float(latest.get("percentRate", 0))
                rate_decimal = rate_pct / 100
                date = latest.get("effectiveDate", "")
            return rate_decimal, date

    except Exception as e:
        print(f"NY Fed API error: {e}")

    return None, None


def fetch_sofr_from_fred(api_key: Optional[str] = None) -> Tuple[Optional[float], Optional[str]]:
    """
    Fetch latest SOFR rate from FRED API

    Returns:
        Tuple of (rate as decimal, observation date) or (None, None) on failure
    """
    if not api_key:
        api_key = get_fred_api_key()

    if not api_key:
        return None, None

    try:
        params = {
            "series_id": FRED_SOFR_SERIES,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": 1,
        }

        response = requests.get(FRED_API_URL, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        observations = data.get("observations", [])

        if observations:
            latest = observations[0]
            # FRED returns rate as percentage (e.g., 5.35 for 5.35%)
            rate_pct = float(latest["value"])
            rate_decimal = rate_pct / 100
            date = latest["date"]
            return rate_decimal, date

    except Exception as e:
        print(f"FRED API error: {e}")

    return None, None


def get_live_sofr(force_refresh: bool = False) -> SOFRData:
    """
    Get live SOFR rate with caching

    Args:
        force_refresh: If True, bypass cache and fetch fresh data

    Returns:
        SOFRData with rate and metadata
    """
    global _sofr_cache

    now = datetime.now()

    # Check cache validity
    if not force_refresh and _sofr_cache["value"] is not None:
        cache_age = now - _sofr_cache["timestamp"]
        if cache_age < timedelta(minutes=CACHE_DURATION_MINUTES):
            return SOFRData(
                rate=_sofr_cache["value"],
                timestamp=_sofr_cache["timestamp"],
                source="cached",
                observation_date=_sofr_cache.get("observation_date"),
            )

    # Try to fetch from NY Fed first (no API key required)
    rate, obs_date = fetch_sofr_from_nyfed()

    # If NY Fed fails, try FRED (requires API key)
    if rate is None:
        rate, obs_date = fetch_sofr_from_fred()

    if rate is not None:
        # Update cache
        _sofr_cache = {
            "value": rate,
            "timestamp": now,
            "source": "live",
            "observation_date": obs_date,
        }
        return SOFRData(
            rate=rate,
            timestamp=now,
            source="live",
            observation_date=obs_date,
        )

    # Return cached value if available (even if stale)
    if _sofr_cache["value"] is not None:
        return SOFRData(
            rate=_sofr_cache["value"],
            timestamp=_sofr_cache["timestamp"],
            source="cached (stale)",
            observation_date=_sofr_cache.get("observation_date"),
        )

    # Fallback to default
    return SOFRData(
        rate=DEFAULT_SOFR,
        timestamp=now,
        source="fallback",
        observation_date=None,
    )


def get_sofr_with_manual_override(manual_rate: Optional[float] = None) -> SOFRData:
    """
    Get SOFR rate, with option for manual override

    Args:
        manual_rate: If provided, use this rate instead of live data

    Returns:
        SOFRData with rate and metadata
    """
    if manual_rate is not None:
        return SOFRData(
            rate=manual_rate,
            timestamp=datetime.now(),
            source="manual",
            observation_date=None,
        )

    return get_live_sofr()


def generate_sofr_curve(
    current_sofr: float,
    months: int,
    scenario: str = "flat",
    volatility: float = 0.005,
) -> list[float]:
    """
    Generate a projected SOFR curve for cashflow modeling

    Args:
        current_sofr: Starting SOFR rate
        months: Number of months to project
        scenario: One of "flat", "rising", "falling", "volatile"
        volatility: Monthly volatility for volatile scenario

    Returns:
        List of monthly SOFR rates
    """
    import numpy as np

    curve = [current_sofr]

    if scenario == "flat":
        curve = [current_sofr] * months

    elif scenario == "rising":
        # Gradual rise of ~100bps over 24 months
        monthly_increase = 0.01 / 24
        for m in range(1, months):
            next_rate = curve[-1] + monthly_increase
            curve.append(min(next_rate, current_sofr + 0.02))  # Cap at +200bps

    elif scenario == "falling":
        # Gradual fall of ~100bps over 24 months
        monthly_decrease = 0.01 / 24
        for m in range(1, months):
            next_rate = curve[-1] - monthly_decrease
            curve.append(max(next_rate, 0.001))  # Floor at 0.1%

    elif scenario == "volatile":
        # Random walk with mean reversion
        np.random.seed(42)  # For reproducibility
        for m in range(1, months):
            shock = np.random.normal(0, volatility)
            # Mean reversion towards starting rate
            reversion = 0.1 * (current_sofr - curve[-1])
            next_rate = curve[-1] + shock + reversion
            curve.append(max(next_rate, 0.001))

    return curve


def format_sofr_display(sofr_data: SOFRData) -> dict:
    """
    Format SOFR data for display in UI

    Returns:
        Dict with formatted strings for display
    """
    return {
        "rate": f"{sofr_data.rate:.2%}",
        "rate_bps": f"{sofr_data.rate * 10000:.0f} bps",
        "source": sofr_data.source,
        "timestamp": sofr_data.timestamp.strftime("%Y-%m-%d %H:%M"),
        "observation_date": sofr_data.observation_date or "N/A",
        "is_live": sofr_data.source == "live",
        "is_stale": "stale" in sofr_data.source,
    }
