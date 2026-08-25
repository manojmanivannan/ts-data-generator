"""Data model classes for time series generation.

Defines the enums and entity classes used to configure and execute
synthetic time series data generation.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from enum import Enum
from typing import TYPE_CHECKING, NamedTuple

import numpy as np
import pandas as pd

from ts_data_generator.random import RNGProtocol
from ts_data_generator.utils.functions import auto_generate_name
from ts_data_generator.utils.trends import Trends

if TYPE_CHECKING:
    from ts_data_generator.anomalies.base import Anomaly

logger = logging.getLogger(__name__)


class MetricResult(NamedTuple):
    """Result of ``Metrics.generate()``.

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


class Granularity(Enum):
    """Time granularity for generated data intervals."""

    ONE_SECOND = "s"
    ONE_MIN = "min"
    FIVE_MIN = "5min"
    HOURLY = "h"
    DAILY = "D"
    WEEKLY = "W"
    MONTHLY = "ME"
    YEARLY = "Y"

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
        """Return the pandas resample alias for this granularity (e.g. ``\"Y\"`` -> ``\"YE\"``)."""
        _aliases = {"Y": "YE"}
        return _aliases.get(self.value, self.value)


class AggregationType(Enum):
    """Aggregation method used when resampling data to a coarser granularity."""

    AVG = "mean"
    SUM = "sum"
    MAX = "max"
    MIN = "min"


class Metrics:
    """A metric combines one or more trends additively to produce a numeric column.

    Args:
        name: Unique name for this metric. Defaults to an auto-generated name.
        trends: Set of Trends instances that are summed to produce the metric.
        aggregation_type: Aggregation method when resampling.

    Example:
        >>> trend = SinusoidalTrend(amplitude=5, freq=24)
        >>> metric = Metrics(name="temperature", trends={trend})
    """

    def __init__(
        self,
        name: str = "default",
        trends: set[Trends] | None = None,
        aggregation_type: AggregationType = AggregationType.AVG,
        anomalies: list[Anomaly] | None = None,
    ) -> None:
        self._name = next(auto_generate_name(category="metric")) if name == "default" else name
        self._trends: set[Trends] = trends or set()
        self._aggregation_type = aggregation_type
        self._anomalies: list[Anomaly] = anomalies or []

    @property
    def name(self) -> str:
        """The unique name of this metric."""
        return self._name

    @property
    def trends(self) -> set[Trends]:
        """The set of trends that compose this metric."""
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

    def to_json(self) -> dict:
        """Serialize the metric to a JSON-compatible dict."""
        return {
            "name": self._name,
            "trends": [t.name for t in self._trends],
            "aggregation_type": self._aggregation_type.value,
        }


class Dimensions:
    """A dimension generates categorical or continuous values for each timestamp.

    Args:
        name: Name of the dimension column.
        function: An infinite generator that produces values for each time step.
        expand: Per-dimension expansion override for ``expand_dimensions``.
        weights: Optional mapping of dimension values to scale multipliers.

    Example:
        >>> d = Dimensions(name="region", function=random_choice(["US", "EU"]), weights={"US": 5.0, "EU": 2.0})
    """

    def __init__(
        self,
        name: str | list[str],
        function: int | str | float | Generator,
        expand: bool | None = None,
        weights: dict[Any, float] | None = None,
    ) -> None:
        self._name = name
        self._function = function
        self._expand = expand
        self._weights = weights
        self._data: pd.DataFrame | None = None

    @property
    def data(self) -> pd.Series | None:
        return self._data

    @property
    def name(self) -> str | list[str]:
        """The name(s) of this dimension."""
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

    @property
    def weights(self) -> dict[Any, float] | None:
        """Per-value scale weights for multivariate dimension expansion."""
        return self._weights

    @property
    def function(self) -> int | str | float | Generator:
        """The generator function producing dimension values."""
        return self._function

    @function.setter
    def function(self, value: int | str | float | Generator) -> None:
        if not isinstance(value, (int, str, float, Generator, list)):
            raise ValueError("function must be a generator object or int, str, float, or list")
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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Dimensions):
            return NotImplemented
        return self._name == other.name

    def __hash__(self) -> int:
        return hash(self._name if isinstance(self._name, str) else tuple(self._name))

    def to_json(self) -> dict:
        """Serialize the dimension to a JSON-compatible dict."""
        return {
            "name": self.name,
            "function": self.function.__repr__().split(" at ")[0],
        }


class MultiItems:
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
        >>> mi = MultiItems(names=["a", "b", "c"], function=linked_gen())
    """

    def __init__(
        self,
        names: list[str],
        function: int | str | float | Generator,
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
        return self._data

    @property
    def names(self) -> list[str]:
        """The column names in this multi-item group."""
        return self._names

    @property
    def expand(self) -> bool | None:
        """Per-dimension expansion override for ``expand_dimensions``."""
        return self._expand

    @property
    def weights(self) -> dict[tuple[Any, ...] | Any, float] | None:
        """Per-tuple scale weights for multivariate dimension expansion."""
        return self._weights

    @property
    def function(self) -> int | str | float | Generator:
        """The generator function producing linked values."""
        return self._function

    @property
    def aggregation_type(self) -> list[AggregationType | str] | None:
        """Aggregation methods for resampling, or None if treated as dimensions."""
        return self._aggregation_type

    @function.setter
    def function(self, value: int | str | float | Generator) -> None:
        if not isinstance(value, (int, str, float, Generator, list)):
            raise ValueError("function must be a generator object or int, str, float, or list")
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

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MultiItems):
            return NotImplemented
        return self._names == other.names

    def __hash__(self) -> int:
        return hash(tuple(self._names))

    def to_json(self) -> dict:
        """Serialize the multi-item to a JSON-compatible dict."""
        return {
            "names": self.names,
            "function": self.function.__repr__().split(" at ")[0],
        }
