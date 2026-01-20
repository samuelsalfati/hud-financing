"""
DSCR (Debt Service Coverage Ratio) calculations for HUD Financing Platform
"""
from dataclasses import dataclass
from typing import Optional, List, Tuple
from enum import Enum


class DSCRStatus(Enum):
    """DSCR health status levels"""
    EXCELLENT = "excellent"  # >= 1.40
    STRONG = "strong"  # >= 1.25
    ADEQUATE = "adequate"  # >= 1.15
    WEAK = "weak"  # >= 1.00
    CRITICAL = "critical"  # < 1.00


@dataclass
class DSCRResult:
    """Result of DSCR calculation"""
    dscr: float
    status: DSCRStatus
    noi: float
    debt_service: float
    coverage_cushion: float  # $ amount above breakeven
    breakeven_noi: float  # NOI needed for 1.0x DSCR


def get_dscr_status(dscr: float) -> DSCRStatus:
    """Determine DSCR status based on ratio"""
    if dscr >= 1.40:
        return DSCRStatus.EXCELLENT
    elif dscr >= 1.25:
        return DSCRStatus.STRONG
    elif dscr >= 1.15:
        return DSCRStatus.ADEQUATE
    elif dscr >= 1.00:
        return DSCRStatus.WEAK
    else:
        return DSCRStatus.CRITICAL


def get_status_color(status: DSCRStatus) -> str:
    """Get display color for DSCR status"""
    colors = {
        DSCRStatus.EXCELLENT: "#06ffa5",  # Mint green
        DSCRStatus.STRONG: "#00cc96",  # Teal
        DSCRStatus.ADEQUATE: "#ffa15a",  # Orange
        DSCRStatus.WEAK: "#ef553b",  # Red
        DSCRStatus.CRITICAL: "#ff0000",  # Bright red
    }
    return colors.get(status, "#ffffff")


def calculate_dscr(
    noi_annual: float,
    debt_service_annual: float,
    capex_reserve: float = 0,
    management_fee: float = 0,
) -> DSCRResult:
    """
    Calculate DSCR with full breakdown

    Args:
        noi_annual: Annual Net Operating Income
        debt_service_annual: Annual debt service (interest only for bridge)
        capex_reserve: Annual capex reserve deduction
        management_fee: Annual management fee deduction

    Returns:
        DSCRResult with full calculation details
    """
    # Adjusted NOI after deductions
    adjusted_noi = noi_annual - capex_reserve - management_fee

    # Avoid division by zero
    if debt_service_annual <= 0:
        return DSCRResult(
            dscr=float('inf'),
            status=DSCRStatus.EXCELLENT,
            noi=adjusted_noi,
            debt_service=debt_service_annual,
            coverage_cushion=adjusted_noi,
            breakeven_noi=0,
        )

    dscr = adjusted_noi / debt_service_annual
    status = get_dscr_status(dscr)

    # Calculate cushion and breakeven
    breakeven_noi = debt_service_annual
    coverage_cushion = adjusted_noi - breakeven_noi

    return DSCRResult(
        dscr=dscr,
        status=status,
        noi=adjusted_noi,
        debt_service=debt_service_annual,
        coverage_cushion=coverage_cushion,
        breakeven_noi=breakeven_noi,
    )


def calculate_dscr_from_deal(
    loan_amount: float,
    borrower_rate: float,
    noi_annual: float,
    capex_reserve_annual: float = 0,
) -> DSCRResult:
    """
    Calculate DSCR from deal parameters

    Args:
        loan_amount: Total loan amount
        borrower_rate: Annual borrower interest rate (decimal)
        noi_annual: Annual NOI
        capex_reserve_annual: Annual capex reserve

    Returns:
        DSCRResult
    """
    # For bridge loans, debt service is interest only
    annual_debt_service = loan_amount * borrower_rate

    return calculate_dscr(
        noi_annual=noi_annual,
        debt_service_annual=annual_debt_service,
        capex_reserve=capex_reserve_annual,
    )


def project_dscr_over_time(
    loan_amount: float,
    sofr_curve: List[float],
    borrower_spread: float,
    noi_annual: float,
    noi_growth_rate: float = 0.02,  # 2% annual growth
) -> List[Tuple[int, float, DSCRStatus]]:
    """
    Project DSCR over the loan term

    Args:
        loan_amount: Total loan amount
        sofr_curve: Monthly SOFR rates
        borrower_spread: Spread over SOFR
        noi_annual: Starting annual NOI
        noi_growth_rate: Annual NOI growth rate

    Returns:
        List of (month, dscr, status) tuples
    """
    results = []
    current_noi = noi_annual

    for month, sofr in enumerate(sofr_curve):
        # Grow NOI annually
        if month > 0 and month % 12 == 0:
            current_noi *= (1 + noi_growth_rate)

        # Calculate debt service
        borrower_rate = sofr + borrower_spread
        annual_debt_service = loan_amount * borrower_rate

        # Calculate DSCR
        if annual_debt_service > 0:
            dscr = current_noi / annual_debt_service
        else:
            dscr = float('inf')

        status = get_dscr_status(dscr)
        results.append((month, dscr, status))

    return results


def calculate_rate_sensitivity(
    loan_amount: float,
    base_sofr: float,
    borrower_spread: float,
    noi_annual: float,
    rate_shocks: List[float] = None,
) -> List[Tuple[float, float, DSCRStatus]]:
    """
    Calculate DSCR sensitivity to rate changes

    Args:
        loan_amount: Total loan amount
        base_sofr: Current SOFR rate
        borrower_spread: Spread over SOFR
        noi_annual: Annual NOI
        rate_shocks: List of rate changes to test (e.g., [-0.01, 0, 0.01, 0.02])

    Returns:
        List of (rate_change, dscr, status) tuples
    """
    if rate_shocks is None:
        rate_shocks = [-0.02, -0.01, 0, 0.01, 0.02, 0.03]

    results = []

    for shock in rate_shocks:
        new_sofr = max(0, base_sofr + shock)
        borrower_rate = new_sofr + borrower_spread
        annual_debt_service = loan_amount * borrower_rate

        if annual_debt_service > 0:
            dscr = noi_annual / annual_debt_service
        else:
            dscr = float('inf')

        status = get_dscr_status(dscr)
        results.append((shock, dscr, status))

    return results


def calculate_breakeven_noi(
    loan_amount: float,
    borrower_rate: float,
    target_dscr: float = 1.0,
) -> float:
    """
    Calculate the NOI needed to achieve target DSCR

    Args:
        loan_amount: Total loan amount
        borrower_rate: Annual borrower rate
        target_dscr: Target DSCR (default 1.0 for breakeven)

    Returns:
        Required annual NOI
    """
    annual_debt_service = loan_amount * borrower_rate
    return annual_debt_service * target_dscr


def calculate_max_loan_for_dscr(
    noi_annual: float,
    borrower_rate: float,
    target_dscr: float = 1.20,
) -> float:
    """
    Calculate maximum loan amount for a given DSCR constraint

    Args:
        noi_annual: Annual NOI
        borrower_rate: Annual borrower rate
        target_dscr: Minimum required DSCR

    Returns:
        Maximum loan amount
    """
    if borrower_rate <= 0 or target_dscr <= 0:
        return float('inf')

    max_debt_service = noi_annual / target_dscr
    return max_debt_service / borrower_rate
