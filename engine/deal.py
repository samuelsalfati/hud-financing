"""
Deal and Tranche classes for SNF Bridge Lending Platform
"""
from dataclasses import dataclass, field
from typing import Literal, Optional
from enum import Enum


class TrancheType(Enum):
    A = "A"  # Senior
    B = "B"  # Subordinate
    C = "C"  # Sponsor/Equity


class RateType(Enum):
    FIXED = "fixed"
    FLOATING = "floating"


@dataclass
class Tranche:
    """Represents a single tranche in the capital stack"""
    tranche_type: TrancheType
    percentage: float  # % of total loan (0-1)
    rate_type: RateType
    spread: float  # Spread over SOFR (for floating) or fixed rate
    is_current_pay: bool = True  # True = paid monthly, False = accrued

    @property
    def name(self) -> str:
        return f"{self.tranche_type.value}-Piece"

    def get_rate(self, sofr: float) -> float:
        """Calculate the rate for this tranche given current SOFR"""
        if self.rate_type == RateType.FLOATING:
            return sofr + self.spread
        return self.spread  # Fixed rate


@dataclass
class FeeStructure:
    """All fees associated with the loan"""
    origination_fee: float = 0.01  # 1% upfront
    exit_fee: float = 0.005  # 0.5% at payoff
    monthly_asset_mgmt_fee: float = 0.0  # Monthly fee as % of loan
    extension_fee: float = 0.005  # 0.5% per extension

    def calculate_origination(self, loan_amount: float) -> float:
        return loan_amount * self.origination_fee

    def calculate_exit(self, loan_amount: float) -> float:
        return loan_amount * self.exit_fee

    def calculate_monthly_mgmt(self, loan_amount: float) -> float:
        return loan_amount * self.monthly_asset_mgmt_fee

    def calculate_extension(self, loan_amount: float) -> float:
        return loan_amount * self.extension_fee


@dataclass
class Deal:
    """Represents a complete SNF bridge loan deal"""
    # Property & Loan Basics
    property_value: float
    loan_amount: float
    term_months: int = 36  # Base term
    extension_months: int = 12  # Optional extension

    # Tranches
    tranches: list[Tranche] = field(default_factory=list)

    # Fees
    fees: FeeStructure = field(default_factory=FeeStructure)

    # Borrower Rate
    borrower_spread: float = 0.04  # Spread over SOFR for borrower
    borrower_rate_type: RateType = RateType.FLOATING
    borrower_fixed_rate: Optional[float] = None  # If fixed

    # HUD Takeout Assumptions
    expected_hud_month: int = 24  # When HUD refinance expected

    @property
    def ltv(self) -> float:
        """Loan-to-Value ratio"""
        return self.loan_amount / self.property_value

    def get_borrower_rate(self, sofr: float) -> float:
        """Calculate borrower's interest rate"""
        if self.borrower_rate_type == RateType.FLOATING:
            return sofr + self.borrower_spread
        return self.borrower_fixed_rate or self.borrower_spread

    def get_tranche_amount(self, tranche: Tranche) -> float:
        """Calculate dollar amount for a tranche"""
        return self.loan_amount * tranche.percentage

    def get_blended_cost_of_capital(self, sofr: float) -> float:
        """Calculate weighted average cost of capital across tranches"""
        total_cost = 0
        for tranche in self.tranches:
            weight = tranche.percentage
            rate = tranche.get_rate(sofr)
            total_cost += weight * rate
        return total_cost

    def get_spread_profit(self, sofr: float) -> float:
        """Calculate interest spread profit (borrower rate - blended cost)"""
        borrower_rate = self.get_borrower_rate(sofr)
        cost_of_capital = self.get_blended_cost_of_capital(sofr)
        return borrower_rate - cost_of_capital

    def validate(self) -> bool:
        """Validate deal structure"""
        total_percentage = sum(t.percentage for t in self.tranches)
        if abs(total_percentage - 1.0) > 0.001:
            raise ValueError(f"Tranche percentages must sum to 100%, got {total_percentage*100}%")
        return True


def create_default_deal(
    property_value: float = 120_000_000,
    ltv: float = 0.85,
    a_piece_pct: float = 0.70,
    b_piece_pct: float = 0.20,
    c_piece_pct: float = 0.10,
    a_spread: float = 0.02,  # SOFR + 2%
    b_spread: float = 0.06,  # SOFR + 6%
    c_spread: float = 0.12,  # 12% fixed target
    borrower_spread: float = 0.04,
    origination_fee: float = 0.01,
    exit_fee: float = 0.005,
    term_months: int = 36,
    expected_hud_month: int = 24,
) -> Deal:
    """Factory function to create a deal with common defaults"""

    loan_amount = property_value * ltv

    tranches = [
        Tranche(
            tranche_type=TrancheType.A,
            percentage=a_piece_pct,
            rate_type=RateType.FLOATING,
            spread=a_spread,
        ),
        Tranche(
            tranche_type=TrancheType.B,
            percentage=b_piece_pct,
            rate_type=RateType.FLOATING,
            spread=b_spread,
        ),
        Tranche(
            tranche_type=TrancheType.C,
            percentage=c_piece_pct,
            rate_type=RateType.FIXED,
            spread=c_spread,
        ),
    ]

    fees = FeeStructure(
        origination_fee=origination_fee,
        exit_fee=exit_fee,
    )

    deal = Deal(
        property_value=property_value,
        loan_amount=loan_amount,
        term_months=term_months,
        tranches=tranches,
        fees=fees,
        borrower_spread=borrower_spread,
        expected_hud_month=expected_hud_month,
    )

    deal.validate()
    return deal
