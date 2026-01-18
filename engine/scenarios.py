"""
Scenario Engine for SNF Bridge Lending
"""
from dataclasses import dataclass
from typing import Literal
from .deal import Deal
from .cashflows import generate_cashflows, CashflowResult


@dataclass
class Scenario:
    """Defines a scenario to run"""
    name: str
    exit_month: int
    has_extension: bool
    sofr_shift: float = 0  # Parallel shift to SOFR curve


@dataclass
class ScenarioResult:
    """Results from a scenario run"""
    scenario: Scenario
    sponsor_irr: float
    sponsor_moic: float
    sponsor_profit: float
    a_irr: float
    b_irr: float
    c_irr: float
    borrower_all_in_cost: float


def get_standard_scenarios(deal: Deal) -> list[Scenario]:
    """Generate standard scenarios for analysis"""
    return [
        Scenario(
            name="Early HUD (18 mo)",
            exit_month=18,
            has_extension=False,
        ),
        Scenario(
            name="Base Case (24 mo)",
            exit_month=24,
            has_extension=False,
        ),
        Scenario(
            name="Delayed (36 mo)",
            exit_month=36,
            has_extension=False,
        ),
        Scenario(
            name="Extended (48 mo)",
            exit_month=48,
            has_extension=True,
        ),
    ]


def get_rate_scenarios(base_sofr: float) -> list[Scenario]:
    """Generate rate shock scenarios"""
    return [
        Scenario(
            name="Rates -100bps",
            exit_month=24,
            has_extension=False,
            sofr_shift=-0.01,
        ),
        Scenario(
            name="Base Rates",
            exit_month=24,
            has_extension=False,
            sofr_shift=0,
        ),
        Scenario(
            name="Rates +100bps",
            exit_month=24,
            has_extension=False,
            sofr_shift=0.01,
        ),
        Scenario(
            name="Rates +200bps",
            exit_month=24,
            has_extension=False,
            sofr_shift=0.02,
        ),
    ]


def run_scenario(
    deal: Deal,
    scenario: Scenario,
    base_sofr_curve: list[float],
) -> ScenarioResult:
    """Run a single scenario and return results"""

    # Apply SOFR shift
    sofr_curve = [max(0, s + scenario.sofr_shift) for s in base_sofr_curve]

    # Generate cashflows
    results = generate_cashflows(
        deal=deal,
        sofr_curve=sofr_curve,
        exit_month=scenario.exit_month,
        has_extension=scenario.has_extension,
    )

    # Calculate borrower all-in cost
    borrower = results['borrower']
    total_paid = abs(sum(f for f in borrower.total_flows if f < 0))
    loan_received = deal.loan_amount - deal.fees.calculate_origination(deal.loan_amount)
    months = scenario.exit_month
    # Simplified annualized cost
    all_in_cost = ((total_paid / loan_received) - 1) * (12 / months) if months > 0 else 0

    return ScenarioResult(
        scenario=scenario,
        sponsor_irr=results['sponsor'].irr,
        sponsor_moic=results['sponsor'].moic,
        sponsor_profit=results['sponsor'].total_profit,
        a_irr=results.get('A', CashflowResult([], [], [], [], [], 0, 0, 0)).irr,
        b_irr=results.get('B', CashflowResult([], [], [], [], [], 0, 0, 0)).irr,
        c_irr=results.get('C', CashflowResult([], [], [], [], [], 0, 0, 0)).irr,
        borrower_all_in_cost=all_in_cost,
    )


def run_scenarios(
    deal: Deal,
    scenarios: list[Scenario],
    base_sofr_curve: list[float],
) -> list[ScenarioResult]:
    """Run multiple scenarios"""
    return [run_scenario(deal, s, base_sofr_curve) for s in scenarios]
