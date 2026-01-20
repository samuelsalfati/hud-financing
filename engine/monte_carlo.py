"""
Monte Carlo simulation engine for HUD Financing Platform
Uses Vasicek model for SOFR path simulation
"""
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import numpy as np
from scipy import stats
from .cashflows import generate_cashflows, CashflowResult
from .deal import Deal


@dataclass
class VasicekParams:
    """Parameters for Vasicek interest rate model"""
    kappa: float = 0.3  # Speed of mean reversion
    theta: float = 0.04  # Long-run mean
    sigma: float = 0.015  # Volatility
    r0: float = 0.043  # Initial rate


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulation"""
    num_simulations: int = 1000
    random_seed: Optional[int] = 42
    include_default: bool = False
    default_probability: float = 0.02  # Annual PD
    recovery_rate_mean: float = 0.70
    recovery_rate_std: float = 0.15


@dataclass
class SimulationPath:
    """Single simulation path results"""
    path_id: int
    sofr_path: List[float]
    irr: float
    moic: float
    profit: float
    defaulted: bool = False
    default_month: Optional[int] = None


@dataclass
class MonteCarloResult:
    """Complete Monte Carlo simulation results"""
    config: MonteCarloConfig
    paths: List[SimulationPath]

    # Statistics
    irr_mean: float
    irr_std: float
    irr_median: float
    irr_5th: float
    irr_25th: float
    irr_75th: float
    irr_95th: float

    moic_mean: float
    moic_std: float

    profit_mean: float
    profit_std: float

    # Risk metrics
    var_95: float  # 95% Value at Risk (IRR)
    var_99: float  # 99% Value at Risk (IRR)
    expected_shortfall_95: float  # Conditional VaR

    # Default metrics (if simulated)
    default_rate: float
    loss_given_default: float


def generate_vasicek_path(
    params: VasicekParams,
    months: int,
    dt: float = 1/12,  # Monthly time step
    random_state: np.random.RandomState = None,
) -> List[float]:
    """
    Generate interest rate path using Vasicek model

    dS = kappa * (theta - S) * dt + sigma * dW

    Args:
        params: Vasicek model parameters
        months: Number of months to simulate
        dt: Time step (1/12 for monthly)
        random_state: NumPy random state for reproducibility

    Returns:
        List of monthly rates
    """
    if random_state is None:
        random_state = np.random.RandomState()

    rates = [params.r0]
    current_rate = params.r0

    for _ in range(months - 1):
        # Standard Wiener process increment
        dW = random_state.normal(0, np.sqrt(dt))

        # Vasicek SDE
        drift = params.kappa * (params.theta - current_rate) * dt
        diffusion = params.sigma * dW

        current_rate = current_rate + drift + diffusion

        # Floor at 0 (rates can't go negative in practice)
        current_rate = max(current_rate, 0.0001)

        rates.append(current_rate)

    return rates


def generate_multiple_paths(
    params: VasicekParams,
    months: int,
    num_paths: int,
    seed: Optional[int] = None,
) -> List[List[float]]:
    """
    Generate multiple interest rate paths

    Args:
        params: Vasicek parameters
        months: Months per path
        num_paths: Number of paths to generate
        seed: Random seed

    Returns:
        List of rate paths
    """
    if seed is not None:
        np.random.seed(seed)

    paths = []
    for _ in range(num_paths):
        path = generate_vasicek_path(params, months)
        paths.append(path)

    return paths


def simulate_default(
    annual_pd: float,
    months: int,
    random_state: np.random.RandomState,
) -> Tuple[bool, Optional[int]]:
    """
    Simulate whether default occurs and when

    Args:
        annual_pd: Annual probability of default
        months: Number of months
        random_state: Random state

    Returns:
        Tuple of (defaulted, default_month)
    """
    # Convert annual PD to monthly
    monthly_pd = 1 - (1 - annual_pd) ** (1/12)

    for month in range(1, months + 1):
        if random_state.random() < monthly_pd:
            return True, month

    return False, None


def run_monte_carlo(
    deal: Deal,
    exit_month: int,
    config: MonteCarloConfig = None,
    vasicek_params: VasicekParams = None,
    sponsor_is_principal: bool = True,
) -> MonteCarloResult:
    """
    Run Monte Carlo simulation for deal

    Args:
        deal: Deal to analyze
        exit_month: Expected exit month
        config: Monte Carlo configuration
        vasicek_params: Vasicek model parameters
        sponsor_is_principal: True = keeps C-piece, False = aggregator mode

    Returns:
        MonteCarloResult with statistics
    """
    if config is None:
        config = MonteCarloConfig()

    if vasicek_params is None:
        vasicek_params = VasicekParams()

    # Set random seed
    if config.random_seed is not None:
        np.random.seed(config.random_seed)

    random_state = np.random.RandomState(config.random_seed)

    # Generate SOFR paths
    sofr_paths = generate_multiple_paths(
        vasicek_params,
        exit_month + 12,  # Extra buffer
        config.num_simulations,
        config.random_seed,
    )

    # Run simulations
    paths = []
    irrs = []
    moics = []
    profits = []
    defaults = 0

    for i, sofr_path in enumerate(sofr_paths):
        # Check for default
        defaulted = False
        default_month = None

        if config.include_default:
            defaulted, default_month = simulate_default(
                config.default_probability,
                exit_month,
                random_state,
            )

        if defaulted and default_month:
            # Calculate loss scenario
            recovery_rate = max(0, min(1,
                random_state.normal(
                    config.recovery_rate_mean,
                    config.recovery_rate_std
                )
            ))

            # Simplified loss calculation
            loss = deal.loan_amount * (1 - recovery_rate)

            # C-piece takes first loss
            c_amount = deal.loan_amount * deal.tranches[2].percentage
            c_loss = min(loss, c_amount)

            # Calculate loss-adjusted metrics
            irr = -1.0 if c_loss >= c_amount else -c_loss / c_amount
            moic = (c_amount - c_loss) / c_amount
            profit = -c_loss
            defaults += 1

        else:
            # Normal scenario
            try:
                results = generate_cashflows(
                    deal, sofr_path, exit_month,
                    sponsor_is_principal=sponsor_is_principal
                )
                sponsor = results.get("sponsor", CashflowResult([], [], [], [], [], 0, 0, 0))
                irr = sponsor.irr
                moic = sponsor.moic
                profit = sponsor.total_profit
            except Exception:
                irr = 0
                moic = 1
                profit = 0

        paths.append(SimulationPath(
            path_id=i,
            sofr_path=sofr_path,
            irr=irr,
            moic=moic,
            profit=profit,
            defaulted=defaulted,
            default_month=default_month,
        ))

        irrs.append(irr)
        moics.append(moic)
        profits.append(profit)

    # Convert to numpy for statistics
    irrs = np.array(irrs)
    moics = np.array(moics)
    profits = np.array(profits)

    # Calculate statistics
    irr_percentiles = np.percentile(irrs, [5, 25, 50, 75, 95])

    # Value at Risk (worst case IRRs)
    var_95 = np.percentile(irrs, 5)  # 5th percentile is 95% VaR
    var_99 = np.percentile(irrs, 1)

    # Expected Shortfall (average of worst 5%)
    worst_5_pct = irrs[irrs <= var_95]
    expected_shortfall = worst_5_pct.mean() if len(worst_5_pct) > 0 else var_95

    return MonteCarloResult(
        config=config,
        paths=paths,
        irr_mean=irrs.mean(),
        irr_std=irrs.std(),
        irr_median=irr_percentiles[2],
        irr_5th=irr_percentiles[0],
        irr_25th=irr_percentiles[1],
        irr_75th=irr_percentiles[3],
        irr_95th=irr_percentiles[4],
        moic_mean=moics.mean(),
        moic_std=moics.std(),
        profit_mean=profits.mean(),
        profit_std=profits.std(),
        var_95=var_95,
        var_99=var_99,
        expected_shortfall_95=expected_shortfall,
        default_rate=defaults / config.num_simulations,
        loss_given_default=1 - config.recovery_rate_mean,
    )


def get_irr_distribution(result: MonteCarloResult) -> Dict:
    """
    Get IRR distribution data for plotting

    Args:
        result: MonteCarloResult

    Returns:
        Dict with histogram data
    """
    irrs = [p.irr for p in result.paths]

    # Create histogram
    hist, bin_edges = np.histogram(irrs, bins=50)

    return {
        "values": irrs,
        "hist_counts": hist.tolist(),
        "bin_edges": bin_edges.tolist(),
        "mean": result.irr_mean,
        "std": result.irr_std,
        "median": result.irr_median,
        "percentiles": {
            "5th": result.irr_5th,
            "25th": result.irr_25th,
            "50th": result.irr_median,
            "75th": result.irr_75th,
            "95th": result.irr_95th,
        },
    }


def get_sofr_fan_chart_data(
    result: MonteCarloResult,
    percentiles: List[float] = None,
) -> Dict:
    """
    Get SOFR path data for fan chart visualization

    Args:
        result: MonteCarloResult
        percentiles: Percentiles to show

    Returns:
        Dict with fan chart data
    """
    if percentiles is None:
        percentiles = [5, 25, 50, 75, 95]

    # Get all SOFR paths
    all_paths = np.array([p.sofr_path for p in result.paths])

    months = all_paths.shape[1]
    month_range = list(range(months))

    # Calculate percentiles for each month
    percentile_data = {}
    for pct in percentiles:
        percentile_data[f"p{pct}"] = np.percentile(all_paths, pct, axis=0).tolist()

    return {
        "months": month_range,
        "percentiles": percentile_data,
        "mean": all_paths.mean(axis=0).tolist(),
    }


def run_stress_test(
    deal: Deal,
    exit_month: int,
    stress_scenarios: List[Dict] = None,
    num_simulations: int = 500,
    sponsor_is_principal: bool = True,
) -> Dict[str, MonteCarloResult]:
    """
    Run Monte Carlo under different stress scenarios

    Args:
        deal: Deal to analyze
        exit_month: Exit month
        stress_scenarios: List of scenario configs
        num_simulations: Simulations per scenario
        sponsor_is_principal: True = keeps C-piece, False = aggregator mode

    Returns:
        Dict of scenario name -> MonteCarloResult
    """
    if stress_scenarios is None:
        stress_scenarios = [
            {
                "name": "Base Case",
                "vasicek": VasicekParams(kappa=0.3, theta=0.04, sigma=0.015),
                "default_prob": 0.02,
            },
            {
                "name": "Rising Rates",
                "vasicek": VasicekParams(kappa=0.1, theta=0.06, sigma=0.02),
                "default_prob": 0.03,
            },
            {
                "name": "Volatile Rates",
                "vasicek": VasicekParams(kappa=0.5, theta=0.04, sigma=0.03),
                "default_prob": 0.03,
            },
            {
                "name": "Recession",
                "vasicek": VasicekParams(kappa=0.2, theta=0.02, sigma=0.025),
                "default_prob": 0.08,
            },
        ]

    results = {}

    for scenario in stress_scenarios:
        config = MonteCarloConfig(
            num_simulations=num_simulations,
            include_default=True,
            default_probability=scenario.get("default_prob", 0.02),
        )

        result = run_monte_carlo(
            deal,
            exit_month,
            config=config,
            vasicek_params=scenario.get("vasicek", VasicekParams()),
            sponsor_is_principal=sponsor_is_principal,
        )

        results[scenario["name"]] = result

    return results


def calculate_probability_metrics(result: MonteCarloResult) -> Dict:
    """
    Calculate probability-based metrics

    Args:
        result: MonteCarloResult

    Returns:
        Dict with probability metrics
    """
    irrs = np.array([p.irr for p in result.paths])

    return {
        "prob_positive_irr": (irrs > 0).mean(),
        "prob_irr_above_10": (irrs > 0.10).mean(),
        "prob_irr_above_15": (irrs > 0.15).mean(),
        "prob_irr_above_20": (irrs > 0.20).mean(),
        "prob_loss": (irrs < 0).mean(),
        "prob_total_loss": (irrs <= -0.5).mean(),
        "expected_irr_given_no_loss": irrs[irrs > 0].mean() if (irrs > 0).any() else 0,
        "expected_irr_given_loss": irrs[irrs < 0].mean() if (irrs < 0).any() else 0,
    }
