"""
Deal and Tranche classes for SNF Bridge Lending Platform
Extended with reserves, extensions, prepayment, and DSCR support
"""
from dataclasses import dataclass, field
from typing import Literal, Optional, List
from enum import Enum
import json
from pathlib import Path


class TrancheType(Enum):
    A = "A"  # Senior
    B = "B"  # Subordinate
    C = "C"  # Sponsor/Equity


class RateType(Enum):
    FIXED = "fixed"
    FLOATING = "floating"


class PrepaymentType(Enum):
    NONE = "none"
    DECLINING = "declining"  # Declining penalty schedule
    YIELD_MAINTENANCE = "yield_maintenance"
    LOCKOUT_ONLY = "lockout_only"


# =============================================================================
# NEW DATA CLASSES
# =============================================================================

@dataclass
class ExtensionTerms:
    """Extension option terms for the loan"""
    num_extensions: int = 2  # Number of extension options
    extension_months_each: int = 6  # Duration of each extension
    extension_fee_per: float = 0.005  # Fee per extension (0.5%)
    min_dscr_required: float = 1.10  # Minimum DSCR to exercise extension

    @property
    def max_extension_months(self) -> int:
        """Total possible extension period"""
        return self.num_extensions * self.extension_months_each

    def calculate_total_extension_fees(self, loan_amount: float, extensions_used: int) -> float:
        """Calculate cumulative extension fees"""
        return loan_amount * self.extension_fee_per * extensions_used


@dataclass
class DSCRInputs:
    """Debt Service Coverage Ratio inputs"""
    noi_annual: float  # Net Operating Income
    capex_reserve_annual: float = 0  # Capital expenditure reserve
    management_fee_annual: float = 0  # Management fees

    @property
    def adjusted_noi(self) -> float:
        """NOI after reserves and fees"""
        return self.noi_annual - self.capex_reserve_annual - self.management_fee_annual


@dataclass
class PrepaymentSchedule:
    """Prepayment penalty structure"""
    prepayment_type: PrepaymentType = PrepaymentType.DECLINING
    lockout_months: int = 12  # No prepayment allowed
    penalty_schedule: List[float] = field(default_factory=lambda: [0.05, 0.04, 0.03, 0.02, 0.01])
    yield_maintenance_spread: float = 0.005  # For yield maintenance calc

    def get_penalty_rate(self, month: int) -> float:
        """Get prepayment penalty rate for a given month"""
        if self.prepayment_type == PrepaymentType.NONE:
            return 0.0

        if month <= self.lockout_months:
            return float('inf')  # Cannot prepay during lockout

        if self.prepayment_type == PrepaymentType.LOCKOUT_ONLY:
            return 0.0  # No penalty after lockout

        if self.prepayment_type == PrepaymentType.DECLINING:
            # Determine which penalty period we're in
            months_after_lockout = month - self.lockout_months
            # Each penalty period is roughly 12 months
            period_index = min(
                months_after_lockout // 12,
                len(self.penalty_schedule) - 1
            )
            return self.penalty_schedule[period_index]

        # Yield maintenance would be calculated separately
        return 0.0

    def calculate_penalty(
        self,
        loan_amount: float,
        month: int,
        current_rate: float = None,
        treasury_rate: float = None,
        remaining_months: int = None,
    ) -> float:
        """Calculate prepayment penalty amount"""
        penalty_rate = self.get_penalty_rate(month)

        if penalty_rate == float('inf'):
            return float('inf')  # Cannot prepay

        if self.prepayment_type == PrepaymentType.YIELD_MAINTENANCE:
            if current_rate and treasury_rate and remaining_months:
                # Simplified yield maintenance: PV of rate differential
                rate_diff = current_rate - treasury_rate + self.yield_maintenance_spread
                monthly_diff = loan_amount * rate_diff / 12
                # Simplified NPV (not discounting for simplicity)
                return max(monthly_diff * remaining_months, loan_amount * 0.01)

        return loan_amount * penalty_rate


@dataclass
class ReserveStructure:
    """Reserve account structure"""
    # Initial reserves (as % of loan)
    interest_reserve_months: int = 6  # Months of interest escrowed
    capex_reserve_pct: float = 0.01  # 1% of loan for capex
    operating_reserve_pct: float = 0.005  # 0.5% for operating

    # Ongoing requirements
    monthly_capex_escrow_pct: float = 0.0  # Monthly addition to capex
    min_operating_reserve: float = 0  # Minimum operating reserve

    def calculate_initial_reserves(
        self,
        loan_amount: float,
        borrower_rate: float,
    ) -> dict:
        """Calculate initial reserve requirements"""
        monthly_interest = loan_amount * borrower_rate / 12
        interest_reserve = monthly_interest * self.interest_reserve_months

        return {
            "interest_reserve": interest_reserve,
            "capex_reserve": loan_amount * self.capex_reserve_pct,
            "operating_reserve": loan_amount * self.operating_reserve_pct,
            "total": (
                interest_reserve +
                loan_amount * self.capex_reserve_pct +
                loan_amount * self.operating_reserve_pct
            ),
        }

    def calculate_monthly_escrow(self, loan_amount: float) -> float:
        """Calculate monthly escrow requirement"""
        return loan_amount * self.monthly_capex_escrow_pct


@dataclass
class FundTerms:
    """Fund economics for B-Piece and C-Piece funds"""
    aum_fee_pct: float = 0.015  # Annual AUM/management fee (1.5%)
    promote_pct: float = 0.20  # Carried interest / promote (20%)
    hurdle_rate: float = 0.08  # Preferred return / hurdle (8%)

    def calculate_annual_aum_fee(self, invested_capital: float) -> float:
        """Calculate annual AUM fee"""
        return invested_capital * self.aum_fee_pct

    def calculate_monthly_aum_fee(self, invested_capital: float) -> float:
        """Calculate monthly AUM fee"""
        return self.calculate_annual_aum_fee(invested_capital) / 12

    def calculate_promote(self, invested_capital: float, total_return: float, holding_months: int) -> float:
        """
        Calculate promote/carry at exit
        Returns the promote amount owed to GP/Aggregator
        """
        # Annualized hurdle
        annualized_hurdle = (1 + self.hurdle_rate) ** (holding_months / 12) - 1
        hurdle_amount = invested_capital * annualized_hurdle

        # Profit above hurdle
        profit = total_return - invested_capital
        excess_profit = max(0, profit - hurdle_amount)

        # Promote is % of excess
        return excess_profit * self.promote_pct


@dataclass
class Tranche:
    """Represents a single tranche in the capital stack"""
    tranche_type: TrancheType
    percentage: float  # % of total loan (0-1)
    rate_type: RateType
    spread: float  # Spread over SOFR (for floating) or fixed rate
    is_current_pay: bool = True  # True = paid monthly, False = accrued
    fee_allocation_pct: float = 0.0  # % of origination/exit fees allocated to this tranche

    @property
    def name(self) -> str:
        return f"{self.tranche_type.value}-Piece"

    def get_rate(self, sofr: float) -> float:
        """Calculate the rate for this tranche given current SOFR"""
        if self.rate_type == RateType.FLOATING:
            return sofr + self.spread
        return self.spread  # Fixed rate

    def get_ltv_contribution(self, total_ltv: float) -> float:
        """Calculate this tranche's LTV contribution on property"""
        return self.percentage * total_ltv


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
    extension_months: int = 12  # Optional extension (legacy field)

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

    # NEW: Extension Terms
    extension_terms: ExtensionTerms = field(default_factory=ExtensionTerms)

    # NEW: Reserve Structure
    reserves: ReserveStructure = field(default_factory=ReserveStructure)

    # NEW: Prepayment Schedule
    prepayment: PrepaymentSchedule = field(default_factory=PrepaymentSchedule)

    # NEW: DSCR Inputs (optional)
    dscr_inputs: Optional[DSCRInputs] = None

    # NEW: Fund Terms for B and C pieces
    b_fund_terms: FundTerms = field(default_factory=lambda: FundTerms(
        aum_fee_pct=0.015, promote_pct=0.20, hurdle_rate=0.08
    ))
    c_fund_terms: FundTerms = field(default_factory=lambda: FundTerms(
        aum_fee_pct=0.02, promote_pct=0.20, hurdle_rate=0.10
    ))

    # NEW: Aggregator co-invest in C-piece
    aggregator_coinvest_pct: float = 0.10  # 10% of C-piece

    # Deal metadata
    deal_name: str = "Untitled Deal"
    property_address: str = ""
    deal_date: str = ""

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

    # Fund and Aggregator methods

    def get_tranche_by_type(self, tranche_type: TrancheType) -> Optional[Tranche]:
        """Get tranche by type"""
        target_value = tranche_type.value if hasattr(tranche_type, 'value') else tranche_type
        for t in self.tranches:
            if t.tranche_type.value == target_value:
                return t
        return None

    def get_aggregator_fee_allocation(self) -> float:
        """Calculate aggregator's share of fees (100% - sum of tranche allocations)"""
        total_tranche_allocation = sum(t.fee_allocation_pct for t in self.tranches)
        return max(0, 1.0 - total_tranche_allocation)

    def get_aggregator_origination_fee(self) -> float:
        """Calculate aggregator's origination fee income"""
        total_fee = self.fees.calculate_origination(self.loan_amount)
        return total_fee * self.get_aggregator_fee_allocation()

    def get_aggregator_exit_fee(self) -> float:
        """Calculate aggregator's exit fee income"""
        total_fee = self.fees.calculate_exit(self.loan_amount)
        return total_fee * self.get_aggregator_fee_allocation()

    def get_b_piece_amount(self) -> float:
        """Get B-piece invested capital"""
        b_tranche = self.get_tranche_by_type(TrancheType.B)
        return self.loan_amount * b_tranche.percentage if b_tranche else 0

    def get_c_piece_amount(self) -> float:
        """Get C-piece invested capital"""
        c_tranche = self.get_tranche_by_type(TrancheType.C)
        return self.loan_amount * c_tranche.percentage if c_tranche else 0

    def get_aggregator_coinvest_amount(self) -> float:
        """Calculate aggregator's co-investment in C-piece"""
        return self.get_c_piece_amount() * self.aggregator_coinvest_pct

    def get_annual_b_aum_fee(self) -> float:
        """Calculate annual AUM fee from B-piece fund"""
        return self.b_fund_terms.calculate_annual_aum_fee(self.get_b_piece_amount())

    def get_annual_c_aum_fee(self) -> float:
        """Calculate annual AUM fee from C-piece fund"""
        # AUM fee on LP capital only (exclude aggregator co-invest)
        lp_capital = self.get_c_piece_amount() * (1 - self.aggregator_coinvest_pct)
        return self.c_fund_terms.calculate_annual_aum_fee(lp_capital)

    def get_total_annual_aum_fees(self) -> float:
        """Calculate total annual AUM fees"""
        return self.get_annual_b_aum_fee() + self.get_annual_c_aum_fee()

    # NEW METHODS

    def get_max_term_with_extensions(self) -> int:
        """Get maximum loan term including all extensions"""
        return self.term_months + self.extension_terms.max_extension_months

    def calculate_dscr(self, sofr: float) -> Optional[float]:
        """Calculate debt service coverage ratio"""
        if self.dscr_inputs is None:
            return None

        annual_debt_service = self.loan_amount * self.get_borrower_rate(sofr)
        if annual_debt_service == 0:
            return float('inf')

        return self.dscr_inputs.adjusted_noi / annual_debt_service

    def get_dscr_status(self, dscr: float) -> str:
        """Get DSCR status indicator"""
        if dscr >= 1.25:
            return "strong"
        elif dscr >= 1.10:
            return "adequate"
        elif dscr >= 1.0:
            return "weak"
        else:
            return "critical"

    def calculate_initial_reserves(self, sofr: float) -> dict:
        """Calculate initial reserve requirements"""
        return self.reserves.calculate_initial_reserves(
            self.loan_amount,
            self.get_borrower_rate(sofr),
        )

    def calculate_prepayment_penalty(
        self,
        month: int,
        sofr: float = None,
        treasury_rate: float = None,
    ) -> float:
        """Calculate prepayment penalty at given month"""
        remaining_months = self.term_months - month
        current_rate = self.get_borrower_rate(sofr) if sofr else None

        return self.prepayment.calculate_penalty(
            self.loan_amount,
            month,
            current_rate=current_rate,
            treasury_rate=treasury_rate,
            remaining_months=remaining_months,
        )

    def to_dict(self) -> dict:
        """Serialize deal to dictionary for JSON export"""
        return {
            "deal_name": self.deal_name,
            "property_value": self.property_value,
            "loan_amount": self.loan_amount,
            "term_months": self.term_months,
            "expected_hud_month": self.expected_hud_month,
            "borrower_spread": self.borrower_spread,
            "property_address": self.property_address,
            "deal_date": self.deal_date,
            "tranches": [
                {
                    "type": t.tranche_type.value,
                    "percentage": t.percentage,
                    "rate_type": t.rate_type.value,
                    "spread": t.spread,
                    "is_current_pay": t.is_current_pay,
                    "fee_allocation_pct": t.fee_allocation_pct,
                }
                for t in self.tranches
            ],
            "fees": {
                "origination_fee": self.fees.origination_fee,
                "exit_fee": self.fees.exit_fee,
                "extension_fee": self.fees.extension_fee,
                "monthly_asset_mgmt_fee": self.fees.monthly_asset_mgmt_fee,
            },
            "extension_terms": {
                "num_extensions": self.extension_terms.num_extensions,
                "extension_months_each": self.extension_terms.extension_months_each,
                "extension_fee_per": self.extension_terms.extension_fee_per,
            },
            "reserves": {
                "interest_reserve_months": self.reserves.interest_reserve_months,
                "capex_reserve_pct": self.reserves.capex_reserve_pct,
                "operating_reserve_pct": self.reserves.operating_reserve_pct,
            },
            "prepayment": {
                "prepayment_type": self.prepayment.prepayment_type.value,
                "lockout_months": self.prepayment.lockout_months,
                "penalty_schedule": self.prepayment.penalty_schedule,
            },
            "dscr_inputs": {
                "noi_annual": self.dscr_inputs.noi_annual,
                "capex_reserve_annual": self.dscr_inputs.capex_reserve_annual,
            } if self.dscr_inputs else None,
            "b_fund_terms": {
                "aum_fee_pct": self.b_fund_terms.aum_fee_pct,
                "promote_pct": self.b_fund_terms.promote_pct,
                "hurdle_rate": self.b_fund_terms.hurdle_rate,
            },
            "c_fund_terms": {
                "aum_fee_pct": self.c_fund_terms.aum_fee_pct,
                "promote_pct": self.c_fund_terms.promote_pct,
                "hurdle_rate": self.c_fund_terms.hurdle_rate,
            },
            "aggregator_coinvest_pct": self.aggregator_coinvest_pct,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Deal":
        """Create Deal from dictionary"""
        tranches = [
            Tranche(
                tranche_type=TrancheType(t["type"]),
                percentage=t["percentage"],
                rate_type=RateType(t["rate_type"]),
                spread=t["spread"],
                is_current_pay=t.get("is_current_pay", True),
                fee_allocation_pct=t.get("fee_allocation_pct", 0.0),
            )
            for t in data.get("tranches", [])
        ]

        fees_data = data.get("fees", {})
        fees = FeeStructure(
            origination_fee=fees_data.get("origination_fee", 0.01),
            exit_fee=fees_data.get("exit_fee", 0.005),
            extension_fee=fees_data.get("extension_fee", 0.005),
            monthly_asset_mgmt_fee=fees_data.get("monthly_asset_mgmt_fee", 0),
        )

        ext_data = data.get("extension_terms", {})
        extension_terms = ExtensionTerms(
            num_extensions=ext_data.get("num_extensions", 2),
            extension_months_each=ext_data.get("extension_months_each", 6),
            extension_fee_per=ext_data.get("extension_fee_per", 0.005),
        )

        res_data = data.get("reserves", {})
        reserves = ReserveStructure(
            interest_reserve_months=res_data.get("interest_reserve_months", 6),
            capex_reserve_pct=res_data.get("capex_reserve_pct", 0.01),
            operating_reserve_pct=res_data.get("operating_reserve_pct", 0.005),
        )

        prep_data = data.get("prepayment", {})
        prepayment = PrepaymentSchedule(
            prepayment_type=PrepaymentType(prep_data.get("prepayment_type", "declining")),
            lockout_months=prep_data.get("lockout_months", 12),
            penalty_schedule=prep_data.get("penalty_schedule", [0.05, 0.04, 0.03, 0.02, 0.01]),
        )

        dscr_data = data.get("dscr_inputs")
        dscr_inputs = None
        if dscr_data:
            dscr_inputs = DSCRInputs(
                noi_annual=dscr_data.get("noi_annual", 0),
                capex_reserve_annual=dscr_data.get("capex_reserve_annual", 0),
            )

        # Fund terms
        b_fund_data = data.get("b_fund_terms", {})
        b_fund_terms = FundTerms(
            aum_fee_pct=b_fund_data.get("aum_fee_pct", 0.015),
            promote_pct=b_fund_data.get("promote_pct", 0.20),
            hurdle_rate=b_fund_data.get("hurdle_rate", 0.08),
        )

        c_fund_data = data.get("c_fund_terms", {})
        c_fund_terms = FundTerms(
            aum_fee_pct=c_fund_data.get("aum_fee_pct", 0.02),
            promote_pct=c_fund_data.get("promote_pct", 0.20),
            hurdle_rate=c_fund_data.get("hurdle_rate", 0.10),
        )

        return cls(
            deal_name=data.get("deal_name", "Untitled Deal"),
            property_value=data.get("property_value", 0),
            loan_amount=data.get("loan_amount", 0),
            term_months=data.get("term_months", 36),
            expected_hud_month=data.get("expected_hud_month", 24),
            borrower_spread=data.get("borrower_spread", 0.04),
            property_address=data.get("property_address", ""),
            deal_date=data.get("deal_date", ""),
            tranches=tranches,
            fees=fees,
            extension_terms=extension_terms,
            reserves=reserves,
            prepayment=prepayment,
            dscr_inputs=dscr_inputs,
            b_fund_terms=b_fund_terms,
            c_fund_terms=c_fund_terms,
            aggregator_coinvest_pct=data.get("aggregator_coinvest_pct", 0.10),
        )

    def save_to_file(self, filepath: str):
        """Save deal to JSON file"""
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, filepath: str) -> "Deal":
        """Load deal from JSON file"""
        with open(filepath, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)


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
