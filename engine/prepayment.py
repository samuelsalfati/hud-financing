"""
Prepayment penalty calculations for HUD Financing Platform
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import Enum
import numpy as np


class PrepaymentType(Enum):
    """Types of prepayment penalty structures"""
    NONE = "none"
    LOCKOUT_ONLY = "lockout_only"
    DECLINING = "declining"
    STEP_DOWN = "step_down"
    YIELD_MAINTENANCE = "yield_maintenance"
    DEFEASANCE = "defeasance"


@dataclass
class PrepaymentResult:
    """Result of prepayment penalty calculation"""
    penalty_amount: float
    penalty_rate: float
    can_prepay: bool
    lockout_remaining: int
    penalty_type: str
    total_payoff: float  # Principal + penalty


def get_default_penalty_schedules() -> dict:
    """Get common prepayment penalty schedules"""
    return {
        "5-4-3-2-1": [0.05, 0.04, 0.03, 0.02, 0.01],
        "3-2-1": [0.03, 0.02, 0.01],
        "2-1": [0.02, 0.01],
        "flat_3": [0.03, 0.03, 0.03],
        "flat_2": [0.02, 0.02],
        "aggressive": [0.05, 0.05, 0.04, 0.03, 0.02, 0.01],
    }


def calculate_declining_penalty(
    loan_amount: float,
    month: int,
    lockout_months: int,
    penalty_schedule: List[float],
    period_months: int = 12,  # Months per penalty period
) -> PrepaymentResult:
    """
    Calculate declining prepayment penalty

    Args:
        loan_amount: Current loan balance
        month: Month of prepayment
        lockout_months: Initial lockout period
        penalty_schedule: List of penalty rates for each period
        period_months: Duration of each penalty period

    Returns:
        PrepaymentResult with penalty details
    """
    # Check lockout
    if month <= lockout_months:
        return PrepaymentResult(
            penalty_amount=float('inf'),
            penalty_rate=1.0,
            can_prepay=False,
            lockout_remaining=lockout_months - month,
            penalty_type="lockout",
            total_payoff=float('inf'),
        )

    # Calculate which penalty period we're in
    months_after_lockout = month - lockout_months
    period_index = min(
        months_after_lockout // period_months,
        len(penalty_schedule) - 1
    )

    # Check if past all penalty periods
    if months_after_lockout >= len(penalty_schedule) * period_months:
        return PrepaymentResult(
            penalty_amount=0,
            penalty_rate=0,
            can_prepay=True,
            lockout_remaining=0,
            penalty_type="open",
            total_payoff=loan_amount,
        )

    penalty_rate = penalty_schedule[period_index]
    penalty_amount = loan_amount * penalty_rate

    return PrepaymentResult(
        penalty_amount=penalty_amount,
        penalty_rate=penalty_rate,
        can_prepay=True,
        lockout_remaining=0,
        penalty_type="declining",
        total_payoff=loan_amount + penalty_amount,
    )


def calculate_yield_maintenance(
    loan_amount: float,
    current_rate: float,
    treasury_rate: float,
    remaining_months: int,
    spread_floor: float = 0.005,  # 50 bps minimum
    discount_rate: Optional[float] = None,
) -> PrepaymentResult:
    """
    Calculate yield maintenance prepayment penalty

    The penalty equals the present value of the difference between
    the loan rate and the treasury rate over the remaining term.

    Args:
        loan_amount: Current loan balance
        current_rate: Current loan interest rate
        treasury_rate: Comparable treasury rate
        remaining_months: Months remaining on loan
        spread_floor: Minimum spread for calculation
        discount_rate: Discount rate for PV (defaults to treasury)

    Returns:
        PrepaymentResult with penalty details
    """
    if discount_rate is None:
        discount_rate = treasury_rate

    # Calculate rate differential
    rate_diff = max(current_rate - treasury_rate, spread_floor)
    monthly_rate_diff = rate_diff / 12

    # Calculate monthly payment differential
    monthly_diff_payment = loan_amount * monthly_rate_diff

    # Calculate present value of differential payments
    if discount_rate > 0:
        monthly_discount = discount_rate / 12
        # PV of annuity formula
        pv_factor = (1 - (1 + monthly_discount) ** -remaining_months) / monthly_discount
        penalty_amount = monthly_diff_payment * pv_factor
    else:
        penalty_amount = monthly_diff_payment * remaining_months

    # Apply minimum (often 1% of loan amount)
    min_penalty = loan_amount * 0.01
    penalty_amount = max(penalty_amount, min_penalty)

    penalty_rate = penalty_amount / loan_amount

    return PrepaymentResult(
        penalty_amount=penalty_amount,
        penalty_rate=penalty_rate,
        can_prepay=True,
        lockout_remaining=0,
        penalty_type="yield_maintenance",
        total_payoff=loan_amount + penalty_amount,
    )


def calculate_defeasance_cost(
    loan_amount: float,
    current_rate: float,
    treasury_rate: float,
    remaining_months: int,
    admin_fee: float = 75000,  # Typical defeasance admin cost
) -> PrepaymentResult:
    """
    Estimate defeasance cost (simplified)

    Defeasance involves purchasing treasuries to match loan payments.
    Cost depends on rate differential.

    Args:
        loan_amount: Current loan balance
        current_rate: Current loan rate
        treasury_rate: Treasury rate for matching securities
        remaining_months: Months remaining
        admin_fee: Administrative and legal fees

    Returns:
        PrepaymentResult with estimated defeasance cost
    """
    # Calculate monthly loan payment (interest only for bridge)
    monthly_interest = loan_amount * current_rate / 12

    # Calculate cost of treasuries to fund payments
    # If treasuries yield less, need more principal
    if treasury_rate > 0:
        # Simplified: PV of payments at treasury rate
        monthly_treasury = treasury_rate / 12
        pv_factor = (1 - (1 + monthly_treasury) ** -remaining_months) / monthly_treasury
        treasury_cost = monthly_interest * pv_factor + loan_amount / ((1 + monthly_treasury) ** remaining_months)
    else:
        treasury_cost = monthly_interest * remaining_months + loan_amount

    # Defeasance cost is treasury cost - loan payoff + admin
    penalty_amount = max(treasury_cost - loan_amount, 0) + admin_fee
    penalty_rate = penalty_amount / loan_amount

    return PrepaymentResult(
        penalty_amount=penalty_amount,
        penalty_rate=penalty_rate,
        can_prepay=True,
        lockout_remaining=0,
        penalty_type="defeasance",
        total_payoff=loan_amount + penalty_amount,
    )


def generate_prepayment_schedule(
    loan_amount: float,
    term_months: int,
    lockout_months: int,
    penalty_type: PrepaymentType,
    penalty_schedule: List[float] = None,
    current_rate: float = None,
    treasury_curve: List[float] = None,
) -> List[Tuple[int, float, float, bool]]:
    """
    Generate full prepayment penalty schedule over loan term

    Args:
        loan_amount: Loan amount
        term_months: Total loan term
        lockout_months: Lockout period
        penalty_type: Type of prepayment penalty
        penalty_schedule: For declining penalties
        current_rate: For yield maintenance
        treasury_curve: Monthly treasury rates

    Returns:
        List of (month, penalty_rate, penalty_amount, can_prepay) tuples
    """
    schedule = []

    if penalty_schedule is None:
        penalty_schedule = [0.05, 0.04, 0.03, 0.02, 0.01]

    if treasury_curve is None:
        treasury_curve = [0.04] * term_months  # Flat 4%

    for month in range(1, term_months + 1):
        if penalty_type == PrepaymentType.NONE:
            result = PrepaymentResult(0, 0, True, 0, "none", loan_amount)

        elif penalty_type == PrepaymentType.LOCKOUT_ONLY:
            if month <= lockout_months:
                result = PrepaymentResult(
                    float('inf'), 1.0, False, lockout_months - month, "lockout", float('inf')
                )
            else:
                result = PrepaymentResult(0, 0, True, 0, "open", loan_amount)

        elif penalty_type in [PrepaymentType.DECLINING, PrepaymentType.STEP_DOWN]:
            result = calculate_declining_penalty(
                loan_amount, month, lockout_months, penalty_schedule
            )

        elif penalty_type == PrepaymentType.YIELD_MAINTENANCE:
            if month <= lockout_months:
                result = PrepaymentResult(
                    float('inf'), 1.0, False, lockout_months - month, "lockout", float('inf')
                )
            else:
                treasury_rate = treasury_curve[min(month - 1, len(treasury_curve) - 1)]
                result = calculate_yield_maintenance(
                    loan_amount, current_rate or 0.08, treasury_rate, term_months - month
                )

        else:
            result = PrepaymentResult(0, 0, True, 0, "unknown", loan_amount)

        schedule.append((
            month,
            result.penalty_rate if result.can_prepay else float('inf'),
            result.penalty_amount if result.can_prepay else float('inf'),
            result.can_prepay,
        ))

    return schedule


def find_optimal_prepay_window(
    prepayment_schedule: List[Tuple[int, float, float, bool]],
    max_penalty_rate: float = 0.02,
) -> Optional[Tuple[int, int]]:
    """
    Find the earliest window where prepayment penalty is acceptable

    Args:
        prepayment_schedule: Output from generate_prepayment_schedule
        max_penalty_rate: Maximum acceptable penalty rate

    Returns:
        Tuple of (start_month, end_month) or None if no acceptable window
    """
    start_month = None
    end_month = None

    for month, penalty_rate, _, can_prepay in prepayment_schedule:
        if can_prepay and penalty_rate <= max_penalty_rate:
            if start_month is None:
                start_month = month
            end_month = month

    if start_month is not None:
        return (start_month, end_month)
    return None
