"""
Interest Rate Hedging: Swaps and Caps
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class InterestRateSwap:
    """
    Interest rate swap to convert floating to fixed.
    We pay fixed, receive floating (SOFR).
    """
    notional: float
    fixed_rate: float  # Rate we pay
    term_months: int

    def monthly_pnl(self, sofr: float) -> float:
        """
        Calculate monthly P&L from swap.
        Positive = we benefit (SOFR > fixed rate)
        Negative = we lose (SOFR < fixed rate)
        """
        floating_receipt = self.notional * sofr / 12
        fixed_payment = self.notional * self.fixed_rate / 12
        return floating_receipt - fixed_payment

    def total_pnl(self, sofr_curve: list[float]) -> float:
        """Calculate total P&L over the swap term"""
        months = min(self.term_months, len(sofr_curve))
        return sum(self.monthly_pnl(sofr_curve[i]) for i in range(months))


@dataclass
class InterestRateCap:
    """
    Interest rate cap - limits maximum SOFR exposure.
    If SOFR exceeds strike, cap pays the difference.
    """
    notional: float
    strike_rate: float  # Cap strike
    premium: float  # Upfront cost
    term_months: int

    def monthly_payout(self, sofr: float) -> float:
        """
        Calculate monthly payout from cap.
        Only pays if SOFR > strike.
        """
        if sofr > self.strike_rate:
            return self.notional * (sofr - self.strike_rate) / 12
        return 0

    def total_pnl(self, sofr_curve: list[float]) -> float:
        """Calculate total P&L (payouts minus premium)"""
        months = min(self.term_months, len(sofr_curve))
        total_payout = sum(self.monthly_payout(sofr_curve[i]) for i in range(months))
        return total_payout - self.premium


def calculate_hedged_rate(
    base_sofr: float,
    spread: float,
    swap: Optional[InterestRateSwap] = None,
    cap: Optional[InterestRateCap] = None,
) -> float:
    """
    Calculate effective rate after hedging.
    """
    effective_sofr = base_sofr

    if swap:
        # Swap converts floating to fixed
        effective_sofr = swap.fixed_rate
    elif cap:
        # Cap limits upside
        effective_sofr = min(base_sofr, cap.strike_rate)

    return effective_sofr + spread
