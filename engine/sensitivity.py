"""
Sensitivity analysis and 2-way tables for HUD Financing Platform
"""
from dataclasses import dataclass
from typing import List, Dict, Tuple, Callable, Optional
import numpy as np
from .cashflows import generate_cashflows, CashflowResult
from .deal import Deal, Tranche, TrancheType, RateType, FeeStructure


@dataclass
class SensitivityResult:
    """Result of a single sensitivity point"""
    param1_value: float
    param2_value: Optional[float]
    irr: float
    moic: float
    profit: float
    dscr: Optional[float] = None


@dataclass
class SensitivityTable:
    """2-way sensitivity table results"""
    param1_name: str
    param1_values: List[float]
    param2_name: str
    param2_values: List[float]
    results: np.ndarray  # 2D array of values
    metric: str  # "irr", "moic", "profit"
    base_case_value: float


def generate_sensitivity_range(
    base_value: float,
    num_points: int = 5,
    pct_range: float = 0.20,
    absolute_range: float = None,
) -> List[float]:
    """
    Generate sensitivity range around base value

    Args:
        base_value: Center value
        num_points: Number of points in range
        pct_range: Percentage range (+/- from base)
        absolute_range: Absolute range (overrides pct_range if provided)

    Returns:
        List of values for sensitivity analysis
    """
    if absolute_range is not None:
        low = base_value - absolute_range
        high = base_value + absolute_range
    else:
        low = base_value * (1 - pct_range)
        high = base_value * (1 + pct_range)

    return list(np.linspace(low, high, num_points))


def run_1way_sensitivity(
    deal: Deal,
    sofr_curve: List[float],
    exit_month: int,
    param_name: str,
    param_values: List[float],
    metric: str = "irr",
) -> List[SensitivityResult]:
    """
    Run 1-way sensitivity analysis

    Args:
        deal: Base deal
        sofr_curve: SOFR curve
        exit_month: Exit month
        param_name: Parameter to vary (e.g., "sofr", "exit_month", "ltv")
        param_values: Values to test
        metric: Which metric to track ("irr", "moic", "profit")

    Returns:
        List of SensitivityResult
    """
    results = []

    for value in param_values:
        # Create modified deal or curve based on parameter
        test_sofr = sofr_curve.copy()
        test_exit = exit_month
        test_deal = Deal(
            property_value=deal.property_value,
            loan_amount=deal.loan_amount,
            term_months=deal.term_months,
            tranches=deal.tranches.copy(),
            fees=deal.fees,
            borrower_spread=deal.borrower_spread,
            expected_hud_month=deal.expected_hud_month,
        )

        if param_name == "sofr":
            test_sofr = [value] * len(sofr_curve)
        elif param_name == "exit_month":
            test_exit = int(value)
        elif param_name == "ltv":
            test_deal.loan_amount = deal.property_value * value
        elif param_name == "a_spread":
            test_deal.tranches[0] = Tranche(
                TrancheType.A, deal.tranches[0].percentage,
                RateType.FLOATING, value
            )
        elif param_name == "b_spread":
            test_deal.tranches[1] = Tranche(
                TrancheType.B, deal.tranches[1].percentage,
                RateType.FLOATING, value
            )
        elif param_name == "borrower_spread":
            test_deal.borrower_spread = value

        # Generate cashflows
        cf_results = generate_cashflows(test_deal, test_sofr, test_exit)
        sponsor = cf_results.get("sponsor", CashflowResult([], [], [], [], [], 0, 0, 0))

        results.append(SensitivityResult(
            param1_value=value,
            param2_value=None,
            irr=sponsor.irr,
            moic=sponsor.moic,
            profit=sponsor.total_profit,
        ))

    return results


def run_2way_sensitivity(
    deal: Deal,
    sofr_curve: List[float],
    exit_month: int,
    param1_name: str,
    param1_values: List[float],
    param2_name: str,
    param2_values: List[float],
    metric: str = "irr",
) -> SensitivityTable:
    """
    Run 2-way sensitivity analysis

    Args:
        deal: Base deal
        sofr_curve: SOFR curve
        exit_month: Exit month
        param1_name: First parameter name
        param1_values: First parameter values
        param2_name: Second parameter name
        param2_values: Second parameter values
        metric: Metric to track

    Returns:
        SensitivityTable with 2D results
    """
    n1 = len(param1_values)
    n2 = len(param2_values)
    results = np.zeros((n1, n2))

    for i, v1 in enumerate(param1_values):
        for j, v2 in enumerate(param2_values):
            # Create test versions
            test_sofr = sofr_curve.copy()
            test_exit = exit_month
            test_deal = Deal(
                property_value=deal.property_value,
                loan_amount=deal.loan_amount,
                term_months=deal.term_months,
                tranches=[t for t in deal.tranches],
                fees=deal.fees,
                borrower_spread=deal.borrower_spread,
                expected_hud_month=deal.expected_hud_month,
            )

            # Apply param1
            _apply_param(test_deal, test_sofr, param1_name, v1, sofr_curve)
            if param1_name == "exit_month":
                test_exit = int(v1)
            elif param1_name == "sofr":
                test_sofr = [v1] * len(sofr_curve)

            # Apply param2
            _apply_param(test_deal, test_sofr, param2_name, v2, sofr_curve)
            if param2_name == "exit_month":
                test_exit = int(v2)
            elif param2_name == "sofr":
                test_sofr = [v2] * len(sofr_curve)

            # Generate cashflows
            try:
                cf_results = generate_cashflows(test_deal, test_sofr, test_exit)
                sponsor = cf_results.get("sponsor", CashflowResult([], [], [], [], [], 0, 0, 0))

                if metric == "irr":
                    results[i, j] = sponsor.irr
                elif metric == "moic":
                    results[i, j] = sponsor.moic
                else:
                    results[i, j] = sponsor.total_profit
            except Exception:
                results[i, j] = np.nan

    # Calculate base case
    base_cf = generate_cashflows(deal, sofr_curve, exit_month)
    base_sponsor = base_cf.get("sponsor", CashflowResult([], [], [], [], [], 0, 0, 0))

    if metric == "irr":
        base_value = base_sponsor.irr
    elif metric == "moic":
        base_value = base_sponsor.moic
    else:
        base_value = base_sponsor.total_profit

    return SensitivityTable(
        param1_name=param1_name,
        param1_values=param1_values,
        param2_name=param2_name,
        param2_values=param2_values,
        results=results,
        metric=metric,
        base_case_value=base_value,
    )


def _apply_param(
    deal: Deal,
    sofr_curve: List[float],
    param_name: str,
    value: float,
    original_sofr: List[float],
):
    """Apply a parameter change to deal or sofr curve"""
    if param_name == "ltv":
        deal.loan_amount = deal.property_value * value
    elif param_name == "a_spread":
        deal.tranches[0] = Tranche(
            TrancheType.A, deal.tranches[0].percentage,
            RateType.FLOATING, value
        )
    elif param_name == "b_spread":
        deal.tranches[1] = Tranche(
            TrancheType.B, deal.tranches[1].percentage,
            RateType.FLOATING, value
        )
    elif param_name == "borrower_spread":
        deal.borrower_spread = value
    elif param_name == "origination_fee":
        deal.fees.origination_fee = value
    elif param_name == "exit_fee":
        deal.fees.exit_fee = value


def calculate_breakeven(
    deal: Deal,
    sofr_curve: List[float],
    exit_month: int,
    param_name: str,
    target_irr: float = 0.0,
    search_range: Tuple[float, float] = None,
    tolerance: float = 0.0001,
) -> Optional[float]:
    """
    Find breakeven value for a parameter (where IRR = target)

    Args:
        deal: Base deal
        sofr_curve: SOFR curve
        exit_month: Exit month
        param_name: Parameter to find breakeven for
        target_irr: Target IRR (default 0 for true breakeven)
        search_range: (min, max) range to search
        tolerance: Convergence tolerance

    Returns:
        Breakeven value or None if not found
    """
    if search_range is None:
        # Default ranges by parameter
        ranges = {
            "sofr": (0.0, 0.15),
            "exit_month": (6, 60),
            "ltv": (0.5, 0.95),
            "borrower_spread": (0.01, 0.10),
        }
        search_range = ranges.get(param_name, (0, 1))

    # Binary search for breakeven
    low, high = search_range
    max_iterations = 50

    for _ in range(max_iterations):
        mid = (low + high) / 2

        # Run sensitivity for this point
        results = run_1way_sensitivity(
            deal, sofr_curve, exit_month,
            param_name, [mid]
        )

        if not results:
            return None

        irr = results[0].irr

        if abs(irr - target_irr) < tolerance:
            return mid

        if irr > target_irr:
            low = mid
        else:
            high = mid

    return (low + high) / 2


def generate_tornado_chart_data(
    deal: Deal,
    sofr_curve: List[float],
    exit_month: int,
    params: List[str] = None,
    pct_change: float = 0.10,
) -> List[Dict]:
    """
    Generate data for tornado sensitivity chart

    Args:
        deal: Base deal
        sofr_curve: SOFR curve
        exit_month: Exit month
        params: Parameters to include
        pct_change: Percentage change for sensitivity

    Returns:
        List of dicts with parameter sensitivities
    """
    if params is None:
        params = ["sofr", "exit_month", "borrower_spread", "ltv"]

    # Get base case
    base_cf = generate_cashflows(deal, sofr_curve, exit_month)
    base_irr = base_cf.get("sponsor", CashflowResult([], [], [], [], [], 0, 0, 0)).irr

    # Get base values
    base_values = {
        "sofr": sofr_curve[0] if sofr_curve else 0.043,
        "exit_month": exit_month,
        "borrower_spread": deal.borrower_spread,
        "ltv": deal.ltv,
        "origination_fee": deal.fees.origination_fee,
        "exit_fee": deal.fees.exit_fee,
    }

    tornado_data = []

    for param in params:
        base_val = base_values.get(param, 0)

        # Handle different param types
        if param == "exit_month":
            low_val = max(6, int(base_val * (1 - pct_change)))
            high_val = int(base_val * (1 + pct_change))
        else:
            low_val = base_val * (1 - pct_change)
            high_val = base_val * (1 + pct_change)

        # Run low scenario
        low_results = run_1way_sensitivity(
            deal, sofr_curve, exit_month, param, [low_val]
        )
        low_irr = low_results[0].irr if low_results else base_irr

        # Run high scenario
        high_results = run_1way_sensitivity(
            deal, sofr_curve, exit_month, param, [high_val]
        )
        high_irr = high_results[0].irr if high_results else base_irr

        tornado_data.append({
            "parameter": param,
            "base_value": base_val,
            "low_value": low_val,
            "high_value": high_val,
            "low_irr": low_irr,
            "high_irr": high_irr,
            "base_irr": base_irr,
            "spread": abs(high_irr - low_irr),
        })

    # Sort by spread (largest impact first)
    tornado_data.sort(key=lambda x: x["spread"], reverse=True)

    return tornado_data


def format_sensitivity_table_for_display(
    table: SensitivityTable,
    format_func: Callable[[float], str] = None,
) -> Dict:
    """
    Format sensitivity table for display

    Args:
        table: SensitivityTable
        format_func: Function to format values

    Returns:
        Dict with formatted data for display
    """
    if format_func is None:
        if table.metric == "irr":
            format_func = lambda x: f"{x:.1%}"
        elif table.metric == "moic":
            format_func = lambda x: f"{x:.2f}x"
        else:
            format_func = lambda x: f"${x:,.0f}"

    # Format column headers
    col_headers = [format_func(v) if table.metric != "irr" else f"{v:.2%}"
                   for v in table.param2_values]

    # Format row headers
    row_headers = [format_func(v) if table.metric != "irr" else f"{v:.2%}"
                   for v in table.param1_values]

    # Format values
    formatted_values = []
    for row in table.results:
        formatted_row = [format_func(v) for v in row]
        formatted_values.append(formatted_row)

    return {
        "col_headers": col_headers,
        "row_headers": row_headers,
        "values": formatted_values,
        "param1_name": table.param1_name,
        "param2_name": table.param2_name,
        "metric": table.metric,
        "base_case": format_func(table.base_case_value),
    }
