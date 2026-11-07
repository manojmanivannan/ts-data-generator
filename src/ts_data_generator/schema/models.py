"""Data model classes for time series generation.

Defines the enums and entity classes used to configure and execute
synthetic time series data generation.
"""

from __future__ import annotations

import logging
from collections.abc import Generator, Sequence
from enum import Enum, StrEnum
from typing import TYPE_CHECKING, Any, NamedTuple, TypeAlias

import numpy as np
import pandas as pd

from ts_data_generator.exceptions import MetricError
from ts_data_generator.functions import auto_generate_name
from ts_data_generator.random import RNGProtocol
from ts_data_generator.trends import Trend

if TYPE_CHECKING:
    from ts_data_generator.anomalies.base import Anomaly

logger = logging.getLogger(__name__)


DimensionFunction: TypeAlias = int | str | float | Generator
"""A value source for a ``Dimension`` or ``MultiItem`` column.

A scalar (``int | str | float``) is a constant value emitted at every
timestamp; a ``Generator`` (the ``functions`` carrier helpers all return
``DimensionCarrier[T]``, a ``Generator`` subclass) produces a fresh value per
timestamp via ``next()``.
"""


class MetricResult(NamedTuple):
    """Result of ``Metric.generate()``.

    Attributes:
        signal: DataFrame with anomalies applied (trends + anomalies).
        baseline: DataFrame with trends only (no anomalies).
        labels: DataFrame with a single boolean ``<name>_anomaly`` column
            marking each point where the signal deviates from the clean
            baseline. Empty when the metric has no anomalies.

    """

    signal: pd.DataFrame
    baseline: pd.DataFrame
    labels: pd.DataFrame


class Granularity(StrEnum):
    """Time granularity for generated data intervals."""

    SECOND = "s"
    MINUTE = "min"
    FIVE_MINUTE = "5min"
    HOUR = "h"
    DAY = "D"
    WEEK = "W"
    MONTH = "ME"
    YEAR = "Y"

    def order(self) -> int:
        """Return the rank of this granularity (lower = finer, higher = coarser).

        Ranks: s=0, min=1, 5min=2, h=3, D=4, W=5, ME=6, Y=7.
        """
        _ranks = {"s": 0, "min": 1, "5min": 2, "h": 3, "D": 4, "W": 5, "ME": 6, "Y": 7}
        return _ranks[self.value]

    def coarser_than(self, other: Granularity) -> bool:
        """Return True if this granularity is coarser (fewer data points) than *other*."""
        return self.order() > other.order()

    def finer_than(self, other: Granularity) -> bool:
        """Return True if this granularity is finer (more data points) than *other*."""
        return self.order() < other.order()

    def resample_alias(self) -> str:
        """Return the pandas resample alias for this granularity (e.g. ``"Y"`` -> ``"YE"``)."""
        _aliases = {"Y": "YE"}
        return _aliases.get(self.value, self.value)


class AggregationType(Enum):
    """Aggregation method used when resampling data to a coarser granularity."""

    AVG = "mean"
    SUM = "sum"
    MAX = "max"
    MIN = "min"


def _normalize_trends(
    trends: Trend | Sequence[Trend] | set[Trend] | None,
) -> list[Trend]:
    """Normalize a single Trend, sequence, or set of Trends into a validated list."""
    if trends is None:
        return []
    if isinstance(trends, Trend):
        return [trends]
    if isinstance(trends, set) or not isinstance(trends, Sequence):
        trend_list = sorted(
            trends,
            key=lambda t: (type(t).__qualname__, str(vars(t)), repr(t)),
        )
    else:
        trend_list = list(trends)
    if len(trend_list) != len(set(trend_list)):
        raise MetricError("Duplicate trends are present.")
    return trend_list


class Metric:
    """A metric combines one or more trends additively to produce a numeric column.

    Args:
        name: Unique name for this metric. Defaults to an auto-generated name.
        trends: A Trend instance or collection of Trend instances summed to produce the metric.
        aggregation_type: Aggregation method when resampling.

    Example:
        >>> trend = SinusoidalTrend(amplitude=5, freq=24)
        >>> metric = Metric(name="temperature", trends=[trend])

    """

    def __init__(
        self,
        name: str | None = "default",
        trends: Trend | Sequence[Trend] | set[Trend] | None = None,
        aggregation_type: AggregationType = AggregationType.AVG,
        anomalies: list[Anomaly] | None = None,
    ) -> None:
        self._name = (
            next(auto_generate_name(category="metric"))
            if name == "default" or name is None
            else name
        )
        self._trends: list[Trend] = _normalize_trends(trends)
        self._aggregation_type = aggregation_type
        self._anomalies: list[Anomaly] = anomalies or []

    @property
    def name(self) -> str:
        """The unique name of this metric."""
        return self._name

    @property
    def trends(self) -> list[Trend]:
        """The list of trends that compose this metric."""
        return self._trends

    @property
    def aggregation_type(self) -> AggregationType:
        """The aggregation method for resampling."""
        return self._aggregation_type

    @property
    def anomalies(self) -> list[Anomaly]:
        """The ordered list of anomaly injectors applied after trends."""
        return self._anomalies

    def generate(
        self,
        timestamps: pd.DatetimeIndex,
        rng: RNGProtocol,
        scale: float = 1.0,
    ) -> MetricResult:
        """Generate metric values for the given timestamps.

        Args:
            timestamps: DatetimeIndex of time points.
            rng: RNG instance passed through to each trend and anomaly.
            scale: Scale multiplier applied to clean baseline trends.

        Returns:
            MetricResult with .signal (trends + anomalies), .baseline (trends
            only), and .labels (boolean ``<name>_anomaly`` ground truth, empty
            when this metric has no anomalies).

        """
        data = np.zeros(len(timestamps))
        for trend in self._trends:
            data += trend.generate(timestamps, rng=rng)
        data = data * scale
        baseline_df = pd.DataFrame(data.copy(), columns=[self._name], index=timestamps)
        for anomaly in self._anomalies:
            data = anomaly.intervene(data, timestamps, rng=rng)
        signal_df = pd.DataFrame(data, columns=[self._name], index=timestamps)
        self._data = signal_df

        labels_df = self._build_anomaly_labels(baseline_df, signal_df, timestamps)
        return MetricResult(signal=signal_df, baseline=baseline_df, labels=labels_df)

    def _build_anomaly_labels(
        self,
        baseline_df: pd.DataFrame,
        signal_df: pd.DataFrame,
        timestamps: pd.DatetimeIndex,
    ) -> pd.DataFrame:
        """Build the boolean ``<name>_anomaly`` ground-truth label column.

        A point is labeled ``True`` when the signal deviates from the clean
        baseline. The comparison is NaN-aware (``equal_nan=False``) so points
        injected with ``NaN`` by ``MissingData`` are flagged, while clean points
        are not. The column is only produced when this metric has anomalies;
        otherwise an empty DataFrame is returned so no label column is emitted.

        The label is stored as ``bool`` dtype, which keeps it out of the
        normalizer and the plotter (both select ``number`` columns only).
        """
        if not self._anomalies:
            return pd.DataFrame(index=timestamps)
        baseline = baseline_df[self._name].to_numpy()
        signal = signal_df[self._name].to_numpy()
        mask = ~np.isclose(signal, baseline, equal_nan=False, atol=1e-9, rtol=1e-9)
        return pd.DataFrame(
            mask.astype(bool),
            columns=[f"{self._name}_anomaly"],
            index=timestamps,
        )

    def __repr__(self) -> str:
        return str(self.to_json())

    def to_json(self) -> dict[str, Any]:
        """Serialize the metric to a JSON-compatible dict."""
        return {
            "name": self._name,
            "trends": [t.name for t in self._trends],
            "aggregation_type": self._aggregation_type.value,
        }


class Dimension:
    """A dimension generates categorical or continuous values for each timestamp.

    Args:
        name: Name of the dimension column.
        function: An infinite generator that produces values for each time step.
        expand: Per-dimension expansion override for ``expand_dimensions``.
        weights: Optional mapping of dimension values to scale multipliers.

    Example:
        >>> d = Dimension(
        ...     name="region",
        ...     function=random_choice(["US", "EU"]),
        ...     weights={"US": 5.0, "EU": 2.0},
        ... )

    """

    def __init__(
        self,
        name: str | list[str],
        function: DimensionFunction,
        expand: bool | None = None,
        weights: dict[Any, float] | None = None,
    ) -> None:
        self._name = name
        self._function = function
        self._expand = expand
        self._weights = weights
        self._data: pd.DataFrame | None = None

    @property
    def data(self) -> pd.DataFrame | None:
        """The generated dimension values, or ``None`` before ``generate`` runs.

        Returns:
            A ``pd.DataFrame`` indexed by the generation timestamps with one
            column per name (a single column when ``name`` is a string),
            holding the per-timestamp dimension values; ``None`` until
            ``generate`` has been called.

        """
        return self._data

    @property
    def name(self) -> str | list[str]:
        """The column name, or names, of this dimension."""
        return self._name

    @property
    def expand(self) -> bool | None:
        """Per-dimension expansion override for ``expand_dimensions``.

        ``None`` (default) inherits the global ``expand_dimensions`` flag;
        ``True`` forces this dimension into the Cartesian product even when the
        global flag is off; ``False`` opts it out of the product (it regenerates
        one-value-per-timestamp within each series instead). See decision #52.
        """
        return self._expand

    @expand.setter
    def expand(self, value: bool | None) -> None:
        if value is not None and not isinstance(value, bool):
            raise ValueError("expand must be a bool or None")
        self._expand = value

    @property
    def weights(self) -> dict[Any, float] | None:
        """Per-value scale weights for multivariate dimension expansion."""
        return self._weights

    @weights.setter
    def weights(self, value: dict[Any, float] | None) -> None:
        if value is not None and not isinstance(value, dict):
            raise ValueError("weights must be a dict or None")
        self._weights = value

    @property
    def function(self) -> DimensionFunction:
        """The value source producing dimension values (see ``DimensionFunction``).

        Assigning a non-scalar, non-``Generator`` value raises ``ValueError``;
        a plain ``list`` is rejected (``next()`` on a list is not callable), so
        the type stays ``DimensionFunction`` and is not widened to accept lists.
        """
        return self._function

    @function.setter
    def function(self, value: DimensionFunction) -> None:
        if not isinstance(value, (int, str, float, Generator)):
            raise ValueError("function must be a generator object or int, str, or float")
        self._function = value

    def generate(
        self, timestamps: pd.DatetimeIndex, rng: RNGProtocol | None = None
    ) -> pd.DataFrame:
        """Generate dimension values for the given timestamps.

        Args:
            timestamps: DatetimeIndex of time points.
            rng: Unused; accepted for API consistency with other generate() methods.

        Returns:
            DataFrame with one column (or multiple if name is a list of names).

        """
        data = [
            (list(next(self._function)) if isinstance(self._name, list) else [next(self._function)])
            for _ in timestamps
        ]
        columns = self._name if isinstance(self._name, list) else [self._name]
        self._data = pd.DataFrame(data, columns=columns, index=timestamps)
        return self._data

    def __repr__(self) -> str:
        return str(self.to_json())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dimension):
            return NotImplemented
        return self._name == other.name

    def __hash__(self) -> int:
        return hash(self._name if isinstance(self._name, str) else tuple(self._name))

    def to_json(self) -> dict[str, Any]:
        """Serialize the dimension to a JSON-compatible dict."""
        return {
            "name": self.name,
            "function": self.function.__repr__().split(" at ")[0],
            "expand": self.expand,
            "weights": self.weights,
        }


class MultiItem:
    """A group of linked columns generated simultaneously from one function.

    Useful when columns have dependencies (e.g., ``col3 = col1 + col2``).

    Args:
        names: List of column names for this multi-item group.
        function: Generator that yields tuples of values matching len(names).
        aggregation_type: Optional list of aggregation methods for resampling.
            If provided, the items are treated as metrics during aggregation.
        expand: Per-dimension expansion override for ``expand_dimensions``.
        weights: Optional mapping of linked tuple values to scale multipliers.

    Example:
        >>> def linked_gen():
        ...     while True:
        ...         yield (1, 2, 3)
        >>> mi = MultiItem(names=["a", "b", "c"], function=linked_gen())

    """

    def __init__(
        self,
        names: list[str],
        function: DimensionFunction,
        aggregation_type: list[AggregationType | str] | None = None,
        expand: bool | None = None,
        weights: dict[tuple[Any, ...] | Any, float] | None = None,
    ) -> None:
        self._names = names
        self._function = function
        self._data: pd.DataFrame | None = None
        self._aggregation_type = aggregation_type
        self._expand = expand
        self._weights = weights

    @property
    def data(self) -> pd.DataFrame | None:
        """The generated linked values, or ``None`` before ``generate`` runs.

        Returns:
            A ``pd.DataFrame`` indexed by the generation timestamps with one
            column per name in the group, holding the per-timestamp linked
            values; ``None`` until ``generate`` has been called.

        """
        return self._data

    @property
    def names(self) -> list[str]:
        """The column names in this multi-item group."""
        return self._names

    @property
    def expand(self) -> bool | None:
        """Per-dimension expansion override for ``expand_dimensions``."""
        return self._expand

    @expand.setter
    def expand(self, value: bool | None) -> None:
        if value is not None and not isinstance(value, bool):
            raise ValueError("expand must be a bool or None")
        self._expand = value

    @property
    def weights(self) -> dict[tuple[Any, ...] | Any, float] | None:
        """Per-tuple scale weights for multivariate dimension expansion."""
        return self._weights

    @weights.setter
    def weights(self, value: dict[tuple[Any, ...] | Any, float] | None) -> None:
        if value is not None and not isinstance(value, dict):
            raise ValueError("weights must be a dict or None")
        self._weights = value

    @property
    def function(self) -> DimensionFunction:
        """The value source producing linked values (see ``DimensionFunction``).

        Assigning a non-scalar, non-``Generator`` value raises ``ValueError``;
        a plain ``list`` is rejected (``next()`` on a list is not callable), so
        the type stays ``DimensionFunction`` and is not widened to accept lists.
        """
        return self._function

    @property
    def aggregation_type(self) -> list[AggregationType | str] | None:
        """Aggregation methods for resampling, or None if treated as dimensions."""
        return self._aggregation_type

    @function.setter
    def function(self, value: DimensionFunction) -> None:
        if not isinstance(value, (int, str, float, Generator)):
            raise ValueError("function must be a generator object or int, str, or float")
        self._function = value

    def generate(
        self, timestamps: pd.DatetimeIndex, rng: RNGProtocol | None = None
    ) -> pd.DataFrame:
        """Generate linked values for all names at each timestamp.

        Args:
            timestamps: DatetimeIndex of time points.
            rng: Unused; accepted for API consistency with other generate() methods.

        Returns:
            DataFrame with one column per name in the multi-item group.

        """
        data = [list(next(self._function)) for _ in timestamps]
        self._data = pd.DataFrame(data, columns=self._names, index=timestamps)
        return self._data

    def __repr__(self) -> str:
        return str(self.to_json())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MultiItem):
            return NotImplemented
        return self._names == other.names

    def __hash__(self) -> int:
        return hash(tuple(self._names))

    def to_json(self) -> dict[str, Any]:
        """Serialize the multi-item to a JSON-compatible dict."""
        return {
            "names": self.names,
            "function": self.function.__repr__().split(" at ")[0],
            "aggregation_type": self.aggregation_type,
            "expand": self.expand,
            "weights": self.weights,
        }
