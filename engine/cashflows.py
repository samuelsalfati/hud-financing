"""
Cashflow generation and IRR calculations for SNF Bridge Loans
"""
import numpy as np
import numpy_financial as npf
from dataclasses import dataclass
from typing import Optional
from .deal import Deal, Tranche, TrancheType


@dataclass
class CashflowResult:
    """Results from cashflow analysis"""
    months: list[int]
    principal_flows: list[float]
    interest_flows: list[float]
    fee_flows: list[float]
    total_flows: list[float]
    irr: float
    moic: float
    total_profit: float


def generate_cashflows(
    deal: Deal,
    sofr_curve: list[float],  # Monthly SOFR values
    exit_month: int,  # When HUD takeout happens
    has_extension: bool = False,
    sponsor_is_principal: bool = True,  # True = keeps C-piece, False = aggregator mode
) -> dict[str, CashflowResult]:
    """
    Generate cashflows for all tranches and sponsor economics.

    Returns dict with keys: 'A', 'B', 'C', 'sponsor', 'borrower'

    sponsor_is_principal:
        True = Principal mode - sponsor invests C-piece, earns C returns + fees + spread
        False = Aggregator mode - sponsor earns fees + spread only, no capital at risk
    """
    results = {}

    # Pad SOFR curve if needed
    total_months = exit_month + 1
    if len(sofr_curve) < total_months:
        sofr_curve = sofr_curve + [sofr_curve[-1]] * (total_months - len(sofr_curve))

    # Calculate borrower total payments (for reference)
    borrower_flows = _calc_borrower_flows(deal, sofr_curve, exit_month, has_extension)
    results['borrower'] = borrower_flows

    # Calculate each tranche
    for tranche in deal.tranches:
        tranche_result = _calc_tranche_flows(deal, tranche, sofr_curve, exit_month, has_extension)
        results[tranche.tranche_type.value] = tranche_result

    # Calculate sponsor economics (fees + C-piece if principal)
    sponsor_result = _calc_sponsor_flows(deal, sofr_curve, exit_month, has_extension, sponsor_is_principal)
    results['sponsor'] = sponsor_result

    return results


def _calc_borrower_flows(
    deal: Deal,
    sofr_curve: list[float],
    exit_month: int,
    has_extension: bool,
) -> CashflowResult:
    """Calculate borrower's perspective (what they pay)"""
    months = list(range(exit_month + 1))
    principal_flows = []
    interest_flows = []
    fee_flows = []

    for m in months:
        if m == 0:
            # Borrower receives loan minus origination fee
            principal_flows.append(deal.loan_amount)
            interest_flows.append(0)
            fee_flows.append(-deal.fees.calculate_origination(deal.loan_amount))
        elif m == exit_month:
            # Final month: repay principal + last interest + exit fee
            sofr = sofr_curve[m]
            monthly_interest = deal.loan_amount * deal.get_borrower_rate(sofr) / 12
            principal_flows.append(-deal.loan_amount)
            interest_flows.append(-monthly_interest)
            fee_flows.append(-deal.fees.calculate_exit(deal.loan_amount))
            if has_extension and m > deal.term_months:
                fee_flows[-1] -= deal.fees.calculate_extension(deal.loan_amount)
        else:
            # Regular month: pay interest
            sofr = sofr_curve[m]
            monthly_interest = deal.loan_amount * deal.get_borrower_rate(sofr) / 12
            principal_flows.append(0)
            interest_flows.append(-monthly_interest)
            fee_flows.append(-deal.fees.calculate_monthly_mgmt(deal.loan_amount))

    total_flows = [p + i + f for p, i, f in zip(principal_flows, interest_flows, fee_flows)]

    # Borrower metrics (from borrower's view, inflows are positive)
    total_out = sum(f for f in total_flows if f < 0)
    total_in = sum(f for f in total_flows if f > 0)

    return CashflowResult(
        months=months,
        principal_flows=principal_flows,
        interest_flows=interest_flows,
        fee_flows=fee_flows,
        total_flows=total_flows,
        irr=0,  # Not meaningful for borrower
        moic=abs(total_out) / total_in if total_in else 0,
        total_profit=0,
    )


def _calc_tranche_flows(
    deal: Deal,
    tranche: Tranche,
    sofr_curve: list[float],
    exit_month: int,
    has_extension: bool,
) -> CashflowResult:
    """Calculate cashflows for a specific tranche"""
    months = list(range(exit_month + 1))
    tranche_amount = deal.get_tranche_amount(tranche)

    principal_flows = []
    interest_flows = []
    fee_flows = []

    for m in months:
        if m == 0:
            # Fund the tranche
            principal_flows.append(-tranche_amount)
            interest_flows.append(0)
            fee_flows.append(0)
        elif m == exit_month:
            # Get principal back + final interest
            sofr = sofr_curve[m]
            rate = tranche.get_rate(sofr)
            monthly_interest = tranche_amount * rate / 12
            principal_flows.append(tranche_amount)
            interest_flows.append(monthly_interest)
            fee_flows.append(0)
        else:
            # Collect interest
            sofr = sofr_curve[m]
            rate = tranche.get_rate(sofr)
            monthly_interest = tranche_amount * rate / 12
            principal_flows.append(0)
            interest_flows.append(monthly_interest if tranche.is_current_pay else 0)
            fee_flows.append(0)

    total_flows = [p + i + f for p, i, f in zip(principal_flows, interest_flows, fee_flows)]

    # Calculate metrics
    irr = _calc_irr(total_flows)
    total_invested = abs(total_flows[0])
    total_returned = sum(total_flows[1:])
    moic = total_returned / total_invested if total_invested else 0
    profit = total_returned - total_invested

    return CashflowResult(
        months=months,
        principal_flows=principal_flows,
        interest_flows=interest_flows,
        fee_flows=fee_flows,
        total_flows=total_flows,
        irr=irr,
        moic=moic,
        total_profit=profit,
    )


def _calc_sponsor_flows(
    deal: Deal,
    sofr_curve: list[float],
    exit_month: int,
    has_extension: bool,
    is_principal: bool = True,
) -> CashflowResult:
    """
    Calculate sponsor economics:
    - If Principal: C-piece returns + fees + spread
    - If Aggregator: fees + spread only (no capital invested)
    """
    months = list(range(exit_month + 1))

    # Find C-piece tranche
    c_tranche = None
    for t in deal.tranches:
        if t.tranche_type == TrancheType.C:
            c_tranche = t
            break

    # Only include C-piece if sponsor is principal
    c_amount = deal.get_tranche_amount(c_tranche) if (c_tranche and is_principal) else 0

    principal_flows = []
    interest_flows = []
    fee_flows = []

    for m in months:
        if m == 0:
            # Principal mode: fund C-piece. Aggregator mode: no investment.
            # Both receive origination fee
            principal_flows.append(-c_amount)
            interest_flows.append(0)
            fee_flows.append(deal.fees.calculate_origination(deal.loan_amount))
        elif m == exit_month:
            sofr = sofr_curve[m]

            # C-piece interest (only if principal)
            c_interest = c_amount * (c_tranche.get_rate(sofr) if c_tranche else 0) / 12 if is_principal else 0

            # Spread income: borrower pays - (A + B + C cost)
            # In aggregator mode, C-piece cost goes to C investor, not us
            borrower_interest = deal.loan_amount * deal.get_borrower_rate(sofr) / 12

            # Cost to pay all tranches (A, B, and C if aggregator)
            if is_principal:
                # We keep C, so only pay A + B
                tranche_cost = sum(
                    deal.get_tranche_amount(t) * t.get_rate(sofr) / 12
                    for t in deal.tranches if t.tranche_type != TrancheType.C
                )
                spread_income = borrower_interest - tranche_cost - c_interest
            else:
                # Aggregator: pay all tranches including C investor
                tranche_cost = sum(
                    deal.get_tranche_amount(t) * t.get_rate(sofr) / 12
                    for t in deal.tranches
                )
                spread_income = borrower_interest - tranche_cost

            principal_flows.append(c_amount)  # Get C back if principal, 0 if aggregator
            interest_flows.append(c_interest + spread_income)

            exit_fee = deal.fees.calculate_exit(deal.loan_amount)
            ext_fee = deal.fees.calculate_extension(deal.loan_amount) if has_extension else 0
            fee_flows.append(exit_fee + ext_fee)
        else:
            # Monthly: C interest (if principal) + spread + mgmt fees
            sofr = sofr_curve[m]

            c_interest = c_amount * (c_tranche.get_rate(sofr) if c_tranche else 0) / 12 if is_principal else 0

            borrower_interest = deal.loan_amount * deal.get_borrower_rate(sofr) / 12

            if is_principal:
                tranche_cost = sum(
                    deal.get_tranche_amount(t) * t.get_rate(sofr) / 12
                    for t in deal.tranches if t.tranche_type != TrancheType.C
                )
                spread_income = borrower_interest - tranche_cost - c_interest
            else:
                tranche_cost = sum(
                    deal.get_tranche_amount(t) * t.get_rate(sofr) / 12
                    for t in deal.tranches
                )
                spread_income = borrower_interest - tranche_cost

            principal_flows.append(0)
            interest_flows.append(c_interest + spread_income)
            fee_flows.append(deal.fees.calculate_monthly_mgmt(deal.loan_amount))

    total_flows = [p + i + f for p, i, f in zip(principal_flows, interest_flows, fee_flows)]

    irr = _calc_irr(total_flows)
    total_invested = abs(total_flows[0]) if total_flows[0] < 0 else 0
    total_returned = sum(f for f in total_flows if f > 0)

    # For aggregator mode with no investment, calculate ROI differently
    if total_invested > 0:
        moic = total_returned / total_invested
    else:
        # No investment - MOIC is infinite, show total profit instead
        moic = float('inf')

    profit = sum(total_flows)

    return CashflowResult(
        months=months,
        principal_flows=principal_flows,
        interest_flows=interest_flows,
        fee_flows=fee_flows,
        total_flows=total_flows,
        irr=irr,
        moic=moic,
        total_profit=profit,
    )


def _calc_irr(cashflows: list[float]) -> float:
    """Calculate IRR from monthly cashflows, return annualized"""
    try:
        monthly_irr = npf.irr(cashflows)
        if np.isnan(monthly_irr):
            return 0
        # Annualize
        return (1 + monthly_irr) ** 12 - 1
    except:
        return 0


def calculate_irr(cashflows: list[float]) -> float:
    """Public IRR function"""
    return _calc_irr(cashflows)


def calculate_moic(cashflows: list[float]) -> float:
    """Calculate Multiple on Invested Capital"""
    invested = abs(sum(f for f in cashflows if f < 0))
    returned = sum(f for f in cashflows if f > 0)
    return returned / invested if invested else 0
