"""
Cashflow generation and IRR calculations for SNF Bridge Loans
"""
import numpy as np
import numpy_financial as npf
from dataclasses import dataclass, field
from typing import Optional
from .deal import Deal, Tranche, TrancheType, FundTerms


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


@dataclass
class FundCashflowResult:
    """Fund-level results including LP returns and aggregator economics"""
    # LP perspective (what limited partners receive)
    lp_cashflows: CashflowResult
    # Aggregator economics from this fund
    aum_fees_collected: list[float]  # Monthly AUM fee collections
    promote_at_exit: float  # Carried interest earned at exit
    fee_allocation_income: list[float]  # Share of origination/exit/extension fees
    # Totals
    total_aum_fees: float
    total_fee_allocation: float
    aggregator_total_income: float  # AUM + promote + fee allocation


@dataclass
class AggregatorSummary:
    """Complete aggregator economics across all funds"""
    # B-Fund economics
    b_fund_aum_fees: float
    b_fund_promote: float
    b_fund_fee_allocation: float
    b_fund_total: float
    # C-Fund economics
    c_fund_aum_fees: float
    c_fund_promote: float
    c_fund_fee_allocation: float
    c_fund_coinvest_returns: float  # Returns from aggregator co-invest (fee-free)
    c_fund_total: float
    # Aggregator's own fee allocation (not from fund management)
    aggregator_direct_fee_allocation: float
    # Grand totals
    total_aum_fees: float
    total_promote: float
    total_fee_allocation: float
    total_coinvest_returns: float
    grand_total: float
    # Aggregator co-invest details
    coinvest_amount: float
    coinvest_irr: float
    coinvest_moic: float


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

    # Find C-piece tranche (use .value comparison for robustness with Streamlit module reloading)
    c_tranche = None
    for t in deal.tranches:
        if t.tranche_type.value == "C":
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
                    for t in deal.tranches if t.tranche_type.value != "C"
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
                    for t in deal.tranches if t.tranche_type.value != "C"
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


def generate_fund_cashflows(
    deal: Deal,
    sofr_curve: list[float],
    exit_month: int,
    has_extension: bool = False,
) -> dict:
    """
    Generate detailed fund-level cashflows including LP returns and aggregator economics.

    Returns dict with keys:
    - 'A': CashflowResult for A-piece (bank, no fund economics)
    - 'B_fund': FundCashflowResult for B-piece fund
    - 'C_fund': FundCashflowResult for C-piece fund
    - 'aggregator': AggregatorSummary with all aggregator economics
    - 'borrower': CashflowResult for borrower perspective
    """
    results = {}

    # Pad SOFR curve if needed
    total_months = exit_month + 1
    if len(sofr_curve) < total_months:
        sofr_curve = sofr_curve + [sofr_curve[-1]] * (total_months - len(sofr_curve))

    # Calculate borrower flows (unchanged)
    results['borrower'] = _calc_borrower_flows(deal, sofr_curve, exit_month, has_extension)

    # Calculate A-piece (bank) - no fund economics, just raw returns
    a_tranche = next((t for t in deal.tranches if t.tranche_type.value == "A"), None)
    if a_tranche:
        a_result = _calc_tranche_flows(deal, a_tranche, sofr_curve, exit_month, has_extension)
        # Add fee allocation to A-piece
        a_fee_alloc = _calc_fee_allocation_flows(deal, a_tranche, exit_month, has_extension)
        a_result.fee_flows = [a_result.fee_flows[i] + a_fee_alloc[i] for i in range(len(a_result.fee_flows))]
        a_result.total_flows = [p + i + f for p, i, f in zip(
            a_result.principal_flows, a_result.interest_flows, a_result.fee_flows)]
        a_result.irr = _calc_irr(a_result.total_flows)
        a_result.total_profit = sum(a_result.total_flows)
        results['A'] = a_result

    # Calculate B-fund with LP returns and aggregator economics
    b_tranche = next((t for t in deal.tranches if t.tranche_type.value == "B"), None)
    if b_tranche:
        results['B_fund'] = _calc_fund_flows(
            deal, b_tranche, deal.b_fund_terms, sofr_curve, exit_month, has_extension, 0.0
        )

    # Calculate C-fund with LP returns, aggregator economics, and co-invest
    c_tranche = next((t for t in deal.tranches if t.tranche_type.value == "C"), None)
    if c_tranche:
        results['C_fund'] = _calc_fund_flows(
            deal, c_tranche, deal.c_fund_terms, sofr_curve, exit_month, has_extension,
            deal.aggregator_coinvest_pct
        )

    # Calculate aggregator summary
    results['aggregator'] = _calc_aggregator_summary(deal, results, sofr_curve, exit_month, has_extension)

    return results


def _calc_fee_allocation_flows(
    deal: Deal,
    tranche: Tranche,
    exit_month: int,
    has_extension: bool,
) -> list[float]:
    """Calculate fee allocation flows for a tranche"""
    months = list(range(exit_month + 1))
    fee_flows = []

    for m in months:
        if m == 0:
            # Origination fee allocation
            orig_fee = deal.fees.calculate_origination(deal.loan_amount)
            fee_flows.append(orig_fee * tranche.fee_allocation_pct)
        elif m == exit_month:
            # Exit fee allocation (and extension if applicable)
            exit_fee = deal.fees.calculate_exit(deal.loan_amount)
            ext_fee = deal.fees.calculate_extension(deal.loan_amount) if has_extension else 0
            fee_flows.append((exit_fee + ext_fee) * tranche.fee_allocation_pct)
        else:
            fee_flows.append(0)

    return fee_flows


def _calc_fund_flows(
    deal: Deal,
    tranche: Tranche,
    fund_terms: FundTerms,
    sofr_curve: list[float],
    exit_month: int,
    has_extension: bool,
    aggregator_coinvest_pct: float,  # Only for C-piece
) -> FundCashflowResult:
    """
    Calculate fund-level cashflows including:
    - LP returns (after AUM fees)
    - Aggregator AUM fees
    - Aggregator promote at exit
    - Fee allocation
    """
    months = list(range(exit_month + 1))
    tranche_amount = deal.get_tranche_amount(tranche)

    # Split between LP capital and aggregator co-invest (for C-piece only)
    coinvest_amount = tranche_amount * aggregator_coinvest_pct
    lp_capital = tranche_amount - coinvest_amount

    # Track flows
    lp_principal_flows = []
    lp_interest_flows = []
    lp_fee_flows = []  # Negative = fees paid to aggregator

    aum_fees_collected = []
    fee_allocation_flows = _calc_fee_allocation_flows(deal, tranche, exit_month, has_extension)

    cumulative_lp_return = 0  # Track LP returns for promote calc

    for m in months:
        if m == 0:
            # LP invests capital
            lp_principal_flows.append(-lp_capital)
            lp_interest_flows.append(0)
            lp_fee_flows.append(0)  # No AUM fee month 0
            aum_fees_collected.append(0)
        elif m == exit_month:
            # Exit: principal back + final interest - AUM fee
            sofr = sofr_curve[m]
            rate = tranche.get_rate(sofr)

            # LP gets their share of interest (proportional to capital)
            lp_share = lp_capital / tranche_amount if tranche_amount > 0 else 0
            full_interest = tranche_amount * rate / 12
            lp_interest = full_interest * lp_share

            # Monthly AUM fee (on LP capital only)
            monthly_aum = fund_terms.calculate_monthly_aum_fee(lp_capital)

            lp_principal_flows.append(lp_capital)
            lp_interest_flows.append(lp_interest)
            lp_fee_flows.append(-monthly_aum)  # LP pays AUM fee
            aum_fees_collected.append(monthly_aum)

            cumulative_lp_return += lp_interest
        else:
            # Monthly: interest - AUM fee
            sofr = sofr_curve[m]
            rate = tranche.get_rate(sofr)

            lp_share = lp_capital / tranche_amount if tranche_amount > 0 else 0
            full_interest = tranche_amount * rate / 12
            lp_interest = full_interest * lp_share

            # Monthly AUM fee
            monthly_aum = fund_terms.calculate_monthly_aum_fee(lp_capital)

            lp_principal_flows.append(0)
            lp_interest_flows.append(lp_interest if tranche.is_current_pay else 0)
            lp_fee_flows.append(-monthly_aum)
            aum_fees_collected.append(monthly_aum)

            if tranche.is_current_pay:
                cumulative_lp_return += lp_interest

    # Calculate LP total flows
    lp_total_flows = [p + i + f for p, i, f in zip(
        lp_principal_flows, lp_interest_flows, lp_fee_flows)]

    # Calculate promote at exit
    total_lp_return = lp_capital + cumulative_lp_return  # Principal + interest received
    promote_at_exit = fund_terms.calculate_promote(lp_capital, total_lp_return, exit_month)

    # Deduct promote from LP's final flow
    if promote_at_exit > 0:
        lp_total_flows[-1] -= promote_at_exit

    lp_result = CashflowResult(
        months=months,
        principal_flows=lp_principal_flows,
        interest_flows=lp_interest_flows,
        fee_flows=lp_fee_flows,
        total_flows=lp_total_flows,
        irr=_calc_irr(lp_total_flows),
        moic=calculate_moic(lp_total_flows),
        total_profit=sum(lp_total_flows),
    )

    total_aum = sum(aum_fees_collected)
    total_fee_alloc = sum(fee_allocation_flows)

    return FundCashflowResult(
        lp_cashflows=lp_result,
        aum_fees_collected=aum_fees_collected,
        promote_at_exit=promote_at_exit,
        fee_allocation_income=fee_allocation_flows,
        total_aum_fees=total_aum,
        total_fee_allocation=total_fee_alloc,
        aggregator_total_income=total_aum + promote_at_exit + total_fee_alloc,
    )


def _calc_aggregator_coinvest_flows(
    deal: Deal,
    c_tranche: Tranche,
    sofr_curve: list[float],
    exit_month: int,
) -> CashflowResult:
    """Calculate aggregator co-invest returns (fee-free)"""
    months = list(range(exit_month + 1))
    tranche_amount = deal.get_tranche_amount(c_tranche)
    coinvest_amount = tranche_amount * deal.aggregator_coinvest_pct

    if coinvest_amount == 0:
        return CashflowResult(
            months=months,
            principal_flows=[0] * len(months),
            interest_flows=[0] * len(months),
            fee_flows=[0] * len(months),
            total_flows=[0] * len(months),
            irr=0, moic=0, total_profit=0
        )

    principal_flows = []
    interest_flows = []

    for m in months:
        if m == 0:
            principal_flows.append(-coinvest_amount)
            interest_flows.append(0)
        elif m == exit_month:
            sofr = sofr_curve[m]
            rate = c_tranche.get_rate(sofr)
            coinvest_share = deal.aggregator_coinvest_pct
            full_interest = tranche_amount * rate / 12
            coinvest_interest = full_interest * coinvest_share
            principal_flows.append(coinvest_amount)
            interest_flows.append(coinvest_interest)
        else:
            sofr = sofr_curve[m]
            rate = c_tranche.get_rate(sofr)
            coinvest_share = deal.aggregator_coinvest_pct
            full_interest = tranche_amount * rate / 12
            coinvest_interest = full_interest * coinvest_share
            principal_flows.append(0)
            interest_flows.append(coinvest_interest if c_tranche.is_current_pay else 0)

    fee_flows = [0] * len(months)  # No fees on co-invest
    total_flows = [p + i for p, i in zip(principal_flows, interest_flows)]

    return CashflowResult(
        months=months,
        principal_flows=principal_flows,
        interest_flows=interest_flows,
        fee_flows=fee_flows,
        total_flows=total_flows,
        irr=_calc_irr(total_flows),
        moic=calculate_moic(total_flows),
        total_profit=sum(total_flows),
    )


def _calc_aggregator_summary(
    deal: Deal,
    fund_results: dict,
    sofr_curve: list[float],
    exit_month: int,
    has_extension: bool,
) -> AggregatorSummary:
    """Calculate complete aggregator economics"""

    # B-Fund economics
    b_fund = fund_results.get('B_fund')
    b_aum = b_fund.total_aum_fees if b_fund else 0
    b_promote = b_fund.promote_at_exit if b_fund else 0
    b_fee_alloc = b_fund.total_fee_allocation if b_fund else 0
    b_total = b_aum + b_promote + b_fee_alloc

    # C-Fund economics
    c_fund = fund_results.get('C_fund')
    c_aum = c_fund.total_aum_fees if c_fund else 0
    c_promote = c_fund.promote_at_exit if c_fund else 0
    c_fee_alloc = c_fund.total_fee_allocation if c_fund else 0

    # C-fund co-invest returns
    c_tranche = next((t for t in deal.tranches if t.tranche_type.value == "C"), None)
    coinvest_result = _calc_aggregator_coinvest_flows(
        deal, c_tranche, sofr_curve, exit_month
    ) if c_tranche else None

    coinvest_returns = coinvest_result.total_profit if coinvest_result else 0
    coinvest_amount = deal.get_tranche_amount(c_tranche) * deal.aggregator_coinvest_pct if c_tranche else 0
    coinvest_irr = coinvest_result.irr if coinvest_result else 0
    coinvest_moic = coinvest_result.moic if coinvest_result else 0

    c_total = c_aum + c_promote + c_fee_alloc + coinvest_returns

    # Aggregator's direct fee allocation (the portion not allocated to tranches)
    total_tranche_fee_alloc = sum(t.fee_allocation_pct for t in deal.tranches)
    aggregator_fee_alloc_pct = max(0, 1.0 - total_tranche_fee_alloc)

    total_fees = (
        deal.fees.calculate_origination(deal.loan_amount) +
        deal.fees.calculate_exit(deal.loan_amount) +
        (deal.fees.calculate_extension(deal.loan_amount) if has_extension else 0)
    )
    aggregator_direct_fee = total_fees * aggregator_fee_alloc_pct

    # Grand totals
    total_aum = b_aum + c_aum
    total_promote = b_promote + c_promote
    total_fee_alloc = b_fee_alloc + c_fee_alloc + aggregator_direct_fee
    grand_total = b_total + c_total + aggregator_direct_fee

    return AggregatorSummary(
        b_fund_aum_fees=b_aum,
        b_fund_promote=b_promote,
        b_fund_fee_allocation=b_fee_alloc,
        b_fund_total=b_total,
        c_fund_aum_fees=c_aum,
        c_fund_promote=c_promote,
        c_fund_fee_allocation=c_fee_alloc,
        c_fund_coinvest_returns=coinvest_returns,
        c_fund_total=c_total,
        aggregator_direct_fee_allocation=aggregator_direct_fee,
        total_aum_fees=total_aum,
        total_promote=total_promote,
        total_fee_allocation=total_fee_alloc,
        total_coinvest_returns=coinvest_returns,
        grand_total=grand_total,
        coinvest_amount=coinvest_amount,
        coinvest_irr=coinvest_irr,
        coinvest_moic=coinvest_moic,
    )
