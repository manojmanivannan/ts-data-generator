"""Plotting utilities for time-series DataFrames.

Provides :func:`plot_time_series` which wraps matplotlib's plot for
time-indexed DataFrames with sensible defaults (excluding the ``epoch``
column, auto-selecting numeric columns).
"""

from __future__ import annotations

import importlib.util

from ts_data_generator.exceptions import ValidationError


def plot_time_series(
    data,
    *,
    exclude: list[str] | None = None,
    include: list[str] | None = None,
    **matplotlib_kwargs,
) -> None:
    """Plot numeric columns from a time-indexed DataFrame.

    Args:
        data: A time-indexed DataFrame (``pd.DataFrame``).
        exclude: Column names to exclude from the plot.
        include: Column names to include.  If both ``exclude`` and ``include``
            are omitted, all numeric columns (except ``epoch``) are plotted.
        matplotlib_kwargs: Additional keyword arguments forwarded to
            matplotlib's ``plot`` function.

    Raises:
        ValidationError: If both ``exclude`` and ``include`` are provided,
            or if no numeric columns are available.
        ImportError: If matplotlib is not installed.
    """
    if exclude and include:
        raise ValidationError(
            "Only one of 'exclude' or 'include' should be provided, not both."
        )

    exclude = exclude or []
    include = include or []

    numeric_cols = data.select_dtypes(include=["number"]).columns.tolist()
    if "epoch" in numeric_cols:
        numeric_cols.remove("epoch")

    if exclude:
        plot_cols = [c for c in numeric_cols if c not in exclude]
    elif include:
        plot_cols = [c for c in numeric_cols if c in include]
    else:
        plot_cols = numeric_cols

    if not plot_cols:
        raise ValidationError("No numeric columns available for plotting.")

    if importlib.util.find_spec("matplotlib") is None:
        raise ImportError(
            "The 'matplotlib' library is required for plotting. "
            "Install with: uv add 'ts-data-generator[plotting]'"
        )

    data.plot(y=plot_cols, **matplotlib_kwargs)
