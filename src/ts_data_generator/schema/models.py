"""Data model classes for time series generation.

Defines the enums and entity classes used to configure and execute
synthetic time series data generation.
"""

import logging
from collections.abc import Generator
from enum import Enum

import numpy as np
import pandas as pd

from ts_data_generator.utils.functions import auto_generate_name
from ts_data_generator.utils.trends import Trends

logger = logging.getLogger(__name__)


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
    ) -> None:
        self._name = auto_generate_name(category="metric") if name == "default" else name
        self._trends: set[Trends] = trends or set()
        self._aggregation_type = aggregation_type

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

    def generate(self, timestamps: pd.DatetimeIndex) -> pd.DataFrame:
        """Generate metric values for the given timestamps.

        Args:
            timestamps: DatetimeIndex of time points.

        Returns:
            DataFrame with a single column named after this metric.
        """
        data = np.zeros(len(timestamps))
        for trend in self._trends:
            data += trend.generate(timestamps)
        self._data = pd.DataFrame(data, columns=[self._name], index=timestamps)
        return self._data

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

    Example:
        >>> d = Dimensions(name="region", function=random_choice(["US", "EU"]))
    """

    def __init__(
        self,
        name: str | list[str],
        function: int | str | float | Generator,
    ) -> None:
        self._name = name
        self._function = function
        self._data: pd.DataFrame | None = None

    @property
    def data(self) -> pd.Series | None:
        return self._data

    @property
    def name(self) -> str | list[str]:
        """The name(s) of this dimension."""
        return self._name

    @property
    def function(self) -> int | str | float | Generator:
        """The generator function producing dimension values."""
        return self._function

    @function.setter
    def function(self, value: int | str | float | Generator) -> None:
        if not isinstance(value, (int, str, float, Generator, list)):
            raise ValueError(
                "function must be a generator object or int, str, float, or list"
            )
        self._function = value

    def generate(self, timestamps: pd.DatetimeIndex) -> pd.DataFrame:
        """Generate dimension values for the given timestamps.

        Args:
            timestamps: DatetimeIndex of time points.

        Returns:
            DataFrame with one column (or multiple if name is a list of names).
        """
        data = [
            (
                list(next(self._function))
                if isinstance(self._name, list)
                else [next(self._function)]
            )
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
    ) -> None:
        self._names = names
        self._function = function
        self._data: pd.DataFrame | None = None
        self._aggregation_type = aggregation_type

    @property
    def data(self) -> pd.DataFrame | None:
        return self._data

    @property
    def names(self) -> list[str]:
        """The column names in this multi-item group."""
        return self._names

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
            raise ValueError(
                "function must be a generator object or int, str, float, or list"
            )
        self._function = value

    def generate(self, timestamps: pd.DatetimeIndex) -> pd.DataFrame:
        """Generate linked values for all names at each timestamp.

        Args:
            timestamps: DatetimeIndex of time points.

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
