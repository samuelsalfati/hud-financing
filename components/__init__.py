"""
Components package for HUD Financing Platform
"""
from .styles import (
    get_page_css,
    get_plotly_theme,
    apply_plotly_theme,
    metric_card,
    status_badge,
    section_divider,
    page_header,
    CYAN_PRIMARY,
    MINT_ACCENT,
    WARNING_ORANGE,
    ERROR_RED,
    SUCCESS_GREEN,
    CHART_COLORS,
    TRANCHE_COLORS,
)

from .auth import check_password, logout, require_auth

from .sidebar import (
    render_logo,
    render_sofr_indicator,
    render_section_header,
    render_deal_summary,
    render_logout_button,
    create_deal_inputs,
)

from .gauges import (
    create_irr_gauge,
    create_dscr_gauge,
    create_ltv_gauge,
    create_moic_gauge,
    create_probability_gauge,
)

from .waterfalls import (
    create_capital_stack_waterfall,
    create_stacked_capital_bar,
    create_loss_waterfall,
    create_fee_breakdown_waterfall,
)

from .charts import (
    apply_ascendra_theme,
    create_line_chart,
    create_multi_line_chart,
    create_bar_chart,
    create_grouped_bar_chart,
    create_stacked_bar_chart,
    create_histogram,
    create_heatmap,
    create_fan_chart,
    create_tornado_chart,
    create_cashflow_chart,
)
