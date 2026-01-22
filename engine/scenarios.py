"""
Scenario Engine for SNF Bridge Lending
"""
from dataclasses import dataclass
from typing import Literal, Optional
from .deal import Deal
from .cashflows import generate_cashflows, generate_fund_cashflows, CashflowResult


@dataclass
class Scenario:
    """Defines a scenario to run"""
    name: str
    exit_month: int
    has_extension: bool
    sofr_shift: float = 0  # Parallel shift to SOFR curve


@dataclass
class AggregatorEconomics:
    """Aggregator economics for a scenario"""
    fee_allocation: float
    b_fund_aum: float
    c_fund_aum: float
    total_aum: float
    b_fund_promote: float
    c_fund_promote: float
    total_promote: float
    coinvest_returns: float
    grand_total: float


@dataclass
class ScenarioResult:
    """Results from a scenario run"""
    scenario: Scenario
    # Sponsor/Aggregator
    sponsor_irr: float
    sponsor_moic: float
    sponsor_profit: float
    # Gross tranche returns
    a_irr: float
    b_irr: float
    c_irr: float
    # LP Net returns (after AUM and promote)
    b_lp_irr: float = 0.0
    b_lp_moic: float = 1.0
    c_lp_irr: float = 0.0
    c_lp_moic: float = 1.0
    # Aggregator economics breakdown
    aggregator: Optional[AggregatorEconomics] = None
    # Borrower
    borrower_all_in_cost: float = 0.0


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
    sponsor_is_principal: bool = True,
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
        sponsor_is_principal=sponsor_is_principal,
    )

    # Generate fund-level cashflows for LP returns and aggregator economics
    fund_results = generate_fund_cashflows(
        deal=deal,
        sofr_curve=sofr_curve,
        exit_month=scenario.exit_month,
        has_extension=scenario.has_extension,
    )

    # Extract LP net returns
    b_fund = fund_results.get('B_fund')
    c_fund = fund_results.get('C_fund')
    aggregator_summary = fund_results.get('aggregator')

    b_lp_irr = b_fund.lp_cashflows.irr if b_fund else 0.0
    b_lp_moic = b_fund.lp_cashflows.moic if b_fund else 1.0
    c_lp_irr = c_fund.lp_cashflows.irr if c_fund else 0.0
    c_lp_moic = c_fund.lp_cashflows.moic if c_fund else 1.0

    # Build aggregator economics
    agg_econ = None
    if aggregator_summary:
        agg_econ = AggregatorEconomics(
            fee_allocation=aggregator_summary.aggregator_direct_fee_allocation,
            b_fund_aum=aggregator_summary.b_fund_aum_fees,
            c_fund_aum=aggregator_summary.c_fund_aum_fees,
            total_aum=aggregator_summary.total_aum_fees,
            b_fund_promote=aggregator_summary.b_fund_promote,
            c_fund_promote=aggregator_summary.c_fund_promote,
            total_promote=aggregator_summary.total_promote,
            coinvest_returns=aggregator_summary.c_fund_coinvest_returns,
            grand_total=aggregator_summary.grand_total,
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
        b_lp_irr=b_lp_irr,
        b_lp_moic=b_lp_moic,
        c_lp_irr=c_lp_irr,
        c_lp_moic=c_lp_moic,
        aggregator=agg_econ,
        borrower_all_in_cost=all_in_cost,
    )


def run_scenarios(
    deal: Deal,
    scenarios: list[Scenario],
    base_sofr_curve: list[float],
    sponsor_is_principal: bool = True,
) -> list[ScenarioResult]:
    """Run multiple scenarios"""
    return [run_scenario(deal, s, base_sofr_curve, sponsor_is_principal) for s in scenarios]
