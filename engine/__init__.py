"""
HUD Financing Engine Package
Core calculation modules for the investment analysis platform
"""

# Deal and structure classes
from .deal import (
    Deal,
    Tranche,
    TrancheType,
    RateType,
    FeeStructure,
    ExtensionTerms,
    DSCRInputs,
    PrepaymentSchedule,
    ReserveStructure,
    create_default_deal,
)

# Cashflow generation
from .cashflows import (
    generate_cashflows,
    CashflowResult,
    calculate_irr,
    calculate_moic,
)

# Scenario analysis
from .scenarios import (
    Scenario,
    ScenarioResult,
    get_standard_scenarios,
    get_rate_scenarios,
    run_scenario,
    run_scenarios,
)

# Live SOFR data
from .sofr import (
    get_live_sofr,
    get_sofr_with_manual_override,
    generate_sofr_curve,
    format_sofr_display,
    SOFRData,
)

# DSCR calculations
from .dscr import (
    calculate_dscr,
    calculate_dscr_from_deal,
    DSCRResult,
    DSCRStatus,
    get_dscr_status,
    calculate_breakeven_noi,
    calculate_max_loan_for_dscr,
)

# Reserve modeling
from .reserves import (
    ReserveAccount,
    ReserveManager,
    ReserveType,
    create_reserve_manager_from_deal,
    simulate_reserves_over_time,
)

# Prepayment penalties
from .prepayment import (
    PrepaymentType,
    PrepaymentResult,
    calculate_declining_penalty,
    calculate_yield_maintenance,
    generate_prepayment_schedule,
)

# Default and loss modeling
from .defaults import (
    DefaultScenario,
    DefaultSeverity,
    LossAllocation,
    WaterfallResult,
    get_standard_default_scenarios,
    run_loss_waterfall,
    analyze_multiple_scenarios,
    calculate_expected_loss,
)

# Sensitivity analysis
from .sensitivity import (
    SensitivityResult,
    SensitivityTable,
    run_1way_sensitivity,
    run_2way_sensitivity,
    calculate_breakeven,
    generate_tornado_chart_data,
)

# Monte Carlo simulation
from .monte_carlo import (
    MonteCarloConfig,
    MonteCarloResult,
    VasicekParams,
    SimulationPath,
    run_monte_carlo,
    get_irr_distribution,
    get_sofr_fan_chart_data,
    calculate_probability_metrics,
)

# Excel export
from .export import (
    create_excel_workbook,
    export_cashflows_to_csv,
    export_all_cashflows_to_csv,
)

__all__ = [
    # Deal
    "Deal",
    "Tranche",
    "TrancheType",
    "RateType",
    "FeeStructure",
    "ExtensionTerms",
    "DSCRInputs",
    "PrepaymentSchedule",
    "ReserveStructure",
    "create_default_deal",
    # Cashflows
    "generate_cashflows",
    "CashflowResult",
    "calculate_irr",
    "calculate_moic",
    # Scenarios
    "Scenario",
    "ScenarioResult",
    "get_standard_scenarios",
    "get_rate_scenarios",
    "run_scenario",
    "run_scenarios",
    # SOFR
    "get_live_sofr",
    "get_sofr_with_manual_override",
    "generate_sofr_curve",
    "format_sofr_display",
    "SOFRData",
    # DSCR
    "calculate_dscr",
    "calculate_dscr_from_deal",
    "DSCRResult",
    "DSCRStatus",
    # Reserves
    "ReserveAccount",
    "ReserveManager",
    "ReserveType",
    # Prepayment
    "PrepaymentType",
    "PrepaymentResult",
    # Defaults
    "DefaultScenario",
    "WaterfallResult",
    "run_loss_waterfall",
    # Sensitivity
    "SensitivityResult",
    "SensitivityTable",
    "run_1way_sensitivity",
    "run_2way_sensitivity",
    # Monte Carlo
    "MonteCarloConfig",
    "MonteCarloResult",
    "VasicekParams",
    "run_monte_carlo",
    # Export
    "create_excel_workbook",
    "export_cashflows_to_csv",
]
