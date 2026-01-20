"""
Reserve account modeling for HUD Financing Platform
Tracks interest reserves, capex reserves, and operating reserves
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum


class ReserveType(Enum):
    """Types of reserve accounts"""
    INTEREST = "interest"
    CAPEX = "capex"
    OPERATING = "operating"
    REPLACEMENT = "replacement"
    TAX_INSURANCE = "tax_insurance"


@dataclass
class ReserveAccount:
    """Individual reserve account with balance tracking"""
    reserve_type: ReserveType
    initial_balance: float
    monthly_contribution: float = 0
    monthly_release: float = 0
    min_balance: float = 0

    # Track balance over time
    balance_history: List[float] = field(default_factory=list)

    @property
    def current_balance(self) -> float:
        """Get current balance"""
        if self.balance_history:
            return self.balance_history[-1]
        return self.initial_balance

    def process_month(
        self,
        contribution: Optional[float] = None,
        release: Optional[float] = None,
    ) -> float:
        """
        Process monthly reserve activity

        Args:
            contribution: Override monthly contribution
            release: Override monthly release

        Returns:
            Ending balance for the month
        """
        starting_balance = self.current_balance

        # Apply contribution
        contrib = contribution if contribution is not None else self.monthly_contribution
        starting_balance += contrib

        # Apply release
        rel = release if release is not None else self.monthly_release
        ending_balance = max(starting_balance - rel, self.min_balance)

        self.balance_history.append(ending_balance)
        return ending_balance

    def reset(self):
        """Reset balance history"""
        self.balance_history = [self.initial_balance]


@dataclass
class ReserveManager:
    """Manages all reserve accounts for a deal"""
    accounts: Dict[ReserveType, ReserveAccount] = field(default_factory=dict)

    def add_account(self, account: ReserveAccount):
        """Add a reserve account"""
        self.accounts[account.reserve_type] = account

    def get_account(self, reserve_type: ReserveType) -> Optional[ReserveAccount]:
        """Get specific reserve account"""
        return self.accounts.get(reserve_type)

    def get_total_reserves(self) -> float:
        """Get total current reserves across all accounts"""
        return sum(acct.current_balance for acct in self.accounts.values())

    def get_initial_funding(self) -> float:
        """Get total initial reserve funding required"""
        return sum(acct.initial_balance for acct in self.accounts.values())

    def process_month(self) -> Dict[ReserveType, float]:
        """Process monthly activity for all accounts"""
        return {
            rtype: acct.process_month()
            for rtype, acct in self.accounts.items()
        }

    def get_balances_summary(self) -> Dict[str, float]:
        """Get summary of all reserve balances"""
        return {
            rtype.value: acct.current_balance
            for rtype, acct in self.accounts.items()
        }


def create_reserve_manager_from_deal(
    loan_amount: float,
    borrower_rate: float,
    interest_reserve_months: int = 6,
    capex_reserve_pct: float = 0.01,
    operating_reserve_pct: float = 0.005,
    monthly_capex_escrow: float = 0,
) -> ReserveManager:
    """
    Create reserve manager with standard accounts from deal parameters

    Args:
        loan_amount: Total loan amount
        borrower_rate: Annual borrower rate
        interest_reserve_months: Months of interest to escrow
        capex_reserve_pct: Capex reserve as % of loan
        operating_reserve_pct: Operating reserve as % of loan
        monthly_capex_escrow: Monthly capex escrow amount

    Returns:
        Configured ReserveManager
    """
    manager = ReserveManager()

    # Interest Reserve - funded upfront, released monthly
    monthly_interest = loan_amount * borrower_rate / 12
    interest_reserve = ReserveAccount(
        reserve_type=ReserveType.INTEREST,
        initial_balance=monthly_interest * interest_reserve_months,
        monthly_contribution=0,
        monthly_release=monthly_interest,
        min_balance=0,
    )
    interest_reserve.balance_history = [interest_reserve.initial_balance]
    manager.add_account(interest_reserve)

    # Capex Reserve - funded upfront, may have monthly additions
    capex_reserve = ReserveAccount(
        reserve_type=ReserveType.CAPEX,
        initial_balance=loan_amount * capex_reserve_pct,
        monthly_contribution=monthly_capex_escrow,
        monthly_release=0,  # Released as needed
        min_balance=0,
    )
    capex_reserve.balance_history = [capex_reserve.initial_balance]
    manager.add_account(capex_reserve)

    # Operating Reserve - funded upfront
    operating_reserve = ReserveAccount(
        reserve_type=ReserveType.OPERATING,
        initial_balance=loan_amount * operating_reserve_pct,
        monthly_contribution=0,
        monthly_release=0,
        min_balance=loan_amount * operating_reserve_pct * 0.5,  # 50% min
    )
    operating_reserve.balance_history = [operating_reserve.initial_balance]
    manager.add_account(operating_reserve)

    return manager


def simulate_reserves_over_time(
    reserve_manager: ReserveManager,
    months: int,
    interest_rate_curve: Optional[List[float]] = None,
    loan_amount: float = 0,
    custom_releases: Optional[Dict[int, Dict[ReserveType, float]]] = None,
) -> Dict[ReserveType, List[float]]:
    """
    Simulate reserve balances over time

    Args:
        reserve_manager: Configured ReserveManager
        months: Number of months to simulate
        interest_rate_curve: Optional varying interest rates
        loan_amount: Loan amount for rate-dependent calculations
        custom_releases: Dict of month -> {ReserveType -> release amount}

    Returns:
        Dict mapping ReserveType to list of monthly balances
    """
    # Reset all accounts
    for acct in reserve_manager.accounts.values():
        acct.reset()

    # Run simulation
    for month in range(months):
        for rtype, acct in reserve_manager.accounts.items():
            # Check for custom release
            release = None
            if custom_releases and month in custom_releases:
                if rtype in custom_releases[month]:
                    release = custom_releases[month][rtype]

            # Adjust interest reserve release if rate changes
            if rtype == ReserveType.INTEREST and interest_rate_curve and loan_amount:
                if month < len(interest_rate_curve):
                    release = loan_amount * interest_rate_curve[month] / 12

            acct.process_month(release=release)

    # Collect results
    return {
        rtype: acct.balance_history
        for rtype, acct in reserve_manager.accounts.items()
    }


def calculate_effective_proceeds(
    loan_amount: float,
    origination_fee: float,
    initial_reserves: float,
) -> float:
    """
    Calculate net proceeds to borrower after fees and reserves

    Args:
        loan_amount: Gross loan amount
        origination_fee: Origination fee amount
        initial_reserves: Total initial reserve funding

    Returns:
        Net proceeds to borrower
    """
    return loan_amount - origination_fee - initial_reserves


def calculate_reserve_release_schedule(
    interest_reserve_balance: float,
    months_remaining: int,
    release_type: str = "straight_line",
) -> List[float]:
    """
    Calculate interest reserve release schedule

    Args:
        interest_reserve_balance: Current interest reserve balance
        months_remaining: Months until expected payoff
        release_type: "straight_line" or "front_loaded"

    Returns:
        List of monthly release amounts
    """
    if months_remaining <= 0:
        return []

    if release_type == "straight_line":
        monthly_release = interest_reserve_balance / months_remaining
        return [monthly_release] * months_remaining

    elif release_type == "front_loaded":
        # Release more in earlier months
        releases = []
        remaining = interest_reserve_balance
        for m in range(months_remaining):
            # Release proportionally more in early months
            weight = (months_remaining - m) / sum(range(1, months_remaining + 1))
            release = interest_reserve_balance * weight
            releases.append(release)
            remaining -= release
        return releases

    return [interest_reserve_balance / months_remaining] * months_remaining
