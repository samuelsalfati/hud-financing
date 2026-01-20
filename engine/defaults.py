"""
Default and Loss Waterfall modeling for HUD Financing Platform
Models default scenarios and loss allocation across tranches
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import Enum
import numpy as np


class DefaultSeverity(Enum):
    """Default severity levels"""
    NONE = "none"
    MINOR = "minor"  # 10-20% loss
    MODERATE = "moderate"  # 20-40% loss
    SEVERE = "severe"  # 40-60% loss
    CATASTROPHIC = "catastrophic"  # 60%+ loss


@dataclass
class DefaultScenario:
    """Defines a default scenario"""
    name: str
    default_month: int
    recovery_rate: float  # 0-1, percentage of property value recovered
    months_to_recovery: int = 12  # Time to realize recovery
    legal_costs_pct: float = 0.05  # Legal costs as % of loan
    carrying_costs_pct: float = 0.03  # Carrying costs as % of loan
    description: str = ""

    @property
    def loss_given_default(self) -> float:
        """Loss given default (1 - recovery rate)"""
        return 1 - self.recovery_rate


@dataclass
class LossAllocation:
    """Loss allocation result for a single tranche"""
    tranche_name: str
    tranche_amount: float
    loss_amount: float
    recovery_amount: float
    loss_percentage: float
    is_wiped_out: bool
    remaining_principal: float


@dataclass
class WaterfallResult:
    """Complete loss waterfall result"""
    scenario: DefaultScenario
    total_loss: float
    total_recovery: float
    allocations: List[LossAllocation]
    senior_impaired: bool
    mezz_impaired: bool
    sponsor_loss_pct: float


def get_standard_default_scenarios(
    term_months: int = 36,
) -> List[DefaultScenario]:
    """Get standard default scenarios for analysis"""
    return [
        DefaultScenario(
            name="No Default",
            default_month=0,
            recovery_rate=1.0,
            description="Base case - no default",
        ),
        DefaultScenario(
            name="Early Default - High Recovery",
            default_month=6,
            recovery_rate=0.85,
            months_to_recovery=6,
            description="Default early, strong recovery",
        ),
        DefaultScenario(
            name="Mid-Term Default - Moderate Recovery",
            default_month=term_months // 2,
            recovery_rate=0.70,
            months_to_recovery=12,
            description="Default mid-term, moderate recovery",
        ),
        DefaultScenario(
            name="Late Default - Low Recovery",
            default_month=term_months - 6,
            recovery_rate=0.55,
            months_to_recovery=18,
            description="Late default with distressed sale",
        ),
        DefaultScenario(
            name="Severe Loss Scenario",
            default_month=12,
            recovery_rate=0.40,
            months_to_recovery=24,
            legal_costs_pct=0.08,
            description="Severe loss with extended workout",
        ),
    ]


def calculate_total_loss(
    loan_amount: float,
    property_value: float,
    scenario: DefaultScenario,
    accrued_interest: float = 0,
) -> Dict[str, float]:
    """
    Calculate total loss in a default scenario

    Args:
        loan_amount: Outstanding loan balance
        property_value: Current property value
        scenario: Default scenario
        accrued_interest: Accrued unpaid interest

    Returns:
        Dict with loss components
    """
    # Recovery proceeds
    recovery_proceeds = property_value * scenario.recovery_rate

    # Costs
    legal_costs = loan_amount * scenario.legal_costs_pct
    carrying_costs = loan_amount * scenario.carrying_costs_pct * (scenario.months_to_recovery / 12)

    # Net recovery
    net_recovery = recovery_proceeds - legal_costs - carrying_costs

    # Total claim
    total_claim = loan_amount + accrued_interest

    # Net loss
    net_loss = max(total_claim - net_recovery, 0)

    return {
        "recovery_proceeds": recovery_proceeds,
        "legal_costs": legal_costs,
        "carrying_costs": carrying_costs,
        "net_recovery": net_recovery,
        "total_claim": total_claim,
        "net_loss": net_loss,
        "loss_percentage": net_loss / loan_amount if loan_amount > 0 else 0,
    }


def allocate_losses_waterfall(
    total_loss: float,
    tranches: List[Dict],  # List of {"name": str, "amount": float, "seniority": int}
) -> List[LossAllocation]:
    """
    Allocate losses through the waterfall (junior to senior)

    Args:
        total_loss: Total loss amount to allocate
        tranches: List of tranche dicts, sorted by seniority (0=most junior)

    Returns:
        List of LossAllocation for each tranche
    """
    # Sort tranches by seniority (junior first for loss allocation)
    sorted_tranches = sorted(tranches, key=lambda t: t.get("seniority", 0))

    allocations = []
    remaining_loss = total_loss

    for tranche in sorted_tranches:
        tranche_amount = tranche["amount"]
        tranche_name = tranche["name"]

        # Allocate losses (up to tranche size)
        loss_to_tranche = min(remaining_loss, tranche_amount)
        remaining_loss -= loss_to_tranche

        recovery = tranche_amount - loss_to_tranche
        loss_pct = loss_to_tranche / tranche_amount if tranche_amount > 0 else 0
        wiped_out = loss_pct >= 0.999  # Effectively wiped out

        allocations.append(LossAllocation(
            tranche_name=tranche_name,
            tranche_amount=tranche_amount,
            loss_amount=loss_to_tranche,
            recovery_amount=recovery,
            loss_percentage=loss_pct,
            is_wiped_out=wiped_out,
            remaining_principal=recovery,
        ))

    return allocations


def run_loss_waterfall(
    loan_amount: float,
    property_value: float,
    a_pct: float,
    b_pct: float,
    c_pct: float,
    scenario: DefaultScenario,
    sofr: float = 0.043,
    borrower_spread: float = 0.04,
    accrued_months: int = 0,
) -> WaterfallResult:
    """
    Run complete loss waterfall analysis

    Args:
        loan_amount: Total loan amount
        property_value: Property value
        a_pct: A-piece percentage
        b_pct: B-piece percentage
        c_pct: C-piece percentage (sponsor)
        scenario: Default scenario
        sofr: Current SOFR
        borrower_spread: Borrower spread
        accrued_months: Months of accrued interest

    Returns:
        WaterfallResult with complete analysis
    """
    # Calculate accrued interest
    borrower_rate = sofr + borrower_spread
    accrued_interest = loan_amount * borrower_rate / 12 * accrued_months

    # Calculate total loss
    loss_calc = calculate_total_loss(
        loan_amount, property_value, scenario, accrued_interest
    )

    # Define tranches (seniority: 0=junior, higher=senior)
    tranches = [
        {"name": "C-Piece (Sponsor)", "amount": loan_amount * c_pct, "seniority": 0},
        {"name": "B-Piece (Mezz)", "amount": loan_amount * b_pct, "seniority": 1},
        {"name": "A-Piece (Senior)", "amount": loan_amount * a_pct, "seniority": 2},
    ]

    # Run waterfall
    allocations = allocate_losses_waterfall(loss_calc["net_loss"], tranches)

    # Determine impairments
    senior_alloc = next((a for a in allocations if "A-Piece" in a.tranche_name), None)
    mezz_alloc = next((a for a in allocations if "B-Piece" in a.tranche_name), None)
    sponsor_alloc = next((a for a in allocations if "C-Piece" in a.tranche_name), None)

    return WaterfallResult(
        scenario=scenario,
        total_loss=loss_calc["net_loss"],
        total_recovery=loss_calc["net_recovery"],
        allocations=allocations,
        senior_impaired=senior_alloc.loss_amount > 0 if senior_alloc else False,
        mezz_impaired=mezz_alloc.loss_amount > 0 if mezz_alloc else False,
        sponsor_loss_pct=sponsor_alloc.loss_percentage if sponsor_alloc else 0,
    )


def analyze_multiple_scenarios(
    loan_amount: float,
    property_value: float,
    a_pct: float,
    b_pct: float,
    c_pct: float,
    scenarios: Optional[List[DefaultScenario]] = None,
) -> List[WaterfallResult]:
    """
    Run waterfall analysis for multiple scenarios

    Args:
        loan_amount: Total loan amount
        property_value: Property value
        a_pct: A-piece percentage
        b_pct: B-piece percentage
        c_pct: C-piece percentage
        scenarios: List of scenarios (uses standard if None)

    Returns:
        List of WaterfallResult
    """
    if scenarios is None:
        scenarios = get_standard_default_scenarios()

    results = []
    for scenario in scenarios:
        if scenario.default_month == 0:
            # No default scenario
            results.append(WaterfallResult(
                scenario=scenario,
                total_loss=0,
                total_recovery=loan_amount,
                allocations=[
                    LossAllocation(
                        "C-Piece (Sponsor)", loan_amount * c_pct,
                        0, loan_amount * c_pct, 0, False, loan_amount * c_pct
                    ),
                    LossAllocation(
                        "B-Piece (Mezz)", loan_amount * b_pct,
                        0, loan_amount * b_pct, 0, False, loan_amount * b_pct
                    ),
                    LossAllocation(
                        "A-Piece (Senior)", loan_amount * a_pct,
                        0, loan_amount * a_pct, 0, False, loan_amount * a_pct
                    ),
                ],
                senior_impaired=False,
                mezz_impaired=False,
                sponsor_loss_pct=0,
            ))
        else:
            result = run_loss_waterfall(
                loan_amount, property_value,
                a_pct, b_pct, c_pct,
                scenario,
            )
            results.append(result)

    return results


def calculate_loss_probability_by_ltv(
    ltv: float,
    base_default_prob: float = 0.02,
) -> float:
    """
    Estimate default probability based on LTV

    Higher LTV = higher default probability

    Args:
        ltv: Loan-to-value ratio
        base_default_prob: Base annual default probability

    Returns:
        Adjusted default probability
    """
    # LTV adjustment factor
    if ltv <= 0.65:
        factor = 0.5
    elif ltv <= 0.75:
        factor = 1.0
    elif ltv <= 0.80:
        factor = 1.5
    elif ltv <= 0.85:
        factor = 2.0
    else:
        factor = 3.0

    return min(base_default_prob * factor, 0.15)  # Cap at 15%


def calculate_expected_loss(
    loan_amount: float,
    property_value: float,
    ltv: float,
    term_years: float,
    recovery_rate: float = 0.70,
) -> Dict[str, float]:
    """
    Calculate expected loss for the deal

    Args:
        loan_amount: Loan amount
        property_value: Property value
        ltv: LTV ratio
        term_years: Loan term in years
        recovery_rate: Expected recovery rate

    Returns:
        Dict with expected loss metrics
    """
    # Probability of default (annualized)
    annual_pd = calculate_loss_probability_by_ltv(ltv)

    # Cumulative PD over term
    cumulative_pd = 1 - (1 - annual_pd) ** term_years

    # Loss given default
    lgd = 1 - recovery_rate

    # Expected loss
    expected_loss = loan_amount * cumulative_pd * lgd

    return {
        "annual_pd": annual_pd,
        "cumulative_pd": cumulative_pd,
        "lgd": lgd,
        "expected_loss": expected_loss,
        "expected_loss_pct": expected_loss / loan_amount,
    }
