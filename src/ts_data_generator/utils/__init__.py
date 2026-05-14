"""Dimension and trend generators for time series data.

Exports:
    Dimension functions: constant, random_choice, random_int, random_float,
        ordered_choice, auto_generate_name.
    Trend classes: Trends (ABC), SinusoidalTrend, LinearTrend, WeekendTrend,
        StockTrend.
"""

from ts_data_generator.utils.functions import (
    auto_generate_name,
    constant,
    ordered_choice,
    random_choice,
    random_float,
    random_int,
)
from ts_data_generator.utils.trends import (
    LinearTrend,
    SinusoidalTrend,
    StockTrend,
    Trends,
    WeekendTrend,
)

__all__ = [
    "auto_generate_name",
    "constant",
    "LinearTrend",
    "ordered_choice",
    "random_choice",
    "random_float",
    "random_int",
    "SinusoidalTrend",
    "StockTrend",
    "Trends",
    "WeekendTrend",
]
