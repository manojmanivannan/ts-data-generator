"""Core :class:`DataGen` engine for synthetic time series generation.

Orchestrates dimension, metric, and multi-item models to produce a
timestamp-indexed DataFrame.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from datetime import datetime
from itertools import cycle
from typing import TYPE_CHECKING, Any

import pandas as pd

from ts_data_generator.aggregator import aggregate_dataframe
from ts_data_generator.core.dataframe_builder import DataFrameBuilder
from ts_data_generator.exceptions import (
    DimensionError,
    MetricError,
    MultiItemError,
    ValidationError,
)
from ts_data_generator.plotting import plot_time_series
from ts_data_generator.random import DefaultRNG, RNGProtocol, SeedableRNG
from ts_data_generator.schema.models import (
    AggregationType,
    Dimensions,
    Granularity,
    Metrics,
    MultiItems,
)
from ts_data_generator.utils.trends import Trends

if TYPE_CHECKING:
    from ts_data_generator.anomalies.base import Anomaly
from ts_data_generator.transforms.normalizer import Normalizer, create_normalizer
from ts_data_generator.utils.functions import constant

logger = logging.getLogger(__name__)


class DataGen:
    """Generate synthetic time series data with dimensions, metrics, and trends.

    Args:
        dimensions: Initial list of :class:`Dimensions` instances.
        metrics: Initial list of :class:`Metrics` instances.
        multi_items: Initial list of :class:`MultiItems` instances.
        start_datetime: Start date/time string (ISO format: ``YYYY-MM-DD``).
        end_datetime: End date/time string (ISO format: ``YYYY-MM-DD``).
        granularity: Time granularity for the generated data.
        seed: Optional integer seed for deterministic generation.
            When set, all randomness flows through a PCG64-backed RNG.

    Example:
        >>> dg = DataGen(
        ...     start_datetime="2024-01-01",
        ...     end_datetime="2024-01-02",
        ...     granularity=Granularity.HOURLY,
        ...     seed=42,
        ... )
    """

    def __init__(
        self,
        dimensions: list[Dimensions] | None = None,
        metrics: list[Metrics] | None = None,
        multi_items: list[MultiItems] | None = None,
        start_datetime: str | None = None,
        end_datetime: str | None = None,
        granularity: Granularity = Granularity.FIVE_MIN,
        seed: int | None = None,
    ) -> None:
        self._dimensions: list[Dimensions] = dimensions or []
        self._metrics: list[Metrics] = metrics or []
        self._multi_items: list[MultiItems] = multi_items or []
        self._start_datetime: str | None = start_datetime
        self._end_datetime: str | None = end_datetime
        self._granularity: Granularity = granularity
        self._normalizer: Normalizer | None = None
        self._timestamps: pd.DatetimeIndex | None = None
        self._pending_regeneration = False
        self._rng: RNGProtocol = SeedableRNG(seed) if seed is not None else DefaultRNG()

        self.data: pd.DataFrame = pd.DataFrame()
        self._baselines: dict[str, pd.DataFrame] = {}

        if start_datetime and end_datetime:
            self._generate_data()

    def __repr__(self) -> str:
        lines = ["DataGen("]
        for d in self._dimensions:
            lines.append(f"    dimension={json.dumps(d.to_json())},")
        for m in self._metrics:
            lines.append(f"    metric={json.dumps(m.to_json())},")
        for mt in self._multi_items:
            lines.append(f"    multi_item={json.dumps(mt.to_json())},")
        lines.append(f"    start={self.start_datetime!r},")
        lines.append(f"    end={self.end_datetime!r},")
        gran_name = (
            Granularity(self._granularity).name
            if isinstance(self._granularity, Granularity)
            else self._granularity
        )
        lines.append(f"    granularity={gran_name},")
        lines.append(")")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self.data)

    def shape(self) -> tuple[int, int]:
        """Return the (rows, columns) shape of the generated data.

        Returns:
            Tuple of (row_count, column_count).
        """
        return self.data.shape

    def head(self, n: int = 5) -> pd.DataFrame:
        """Return the first *n* rows of generated data.

        Args:
            n: Number of rows to return.

        Returns:
            DataFrame with the first n rows.
        """
        return self.data.head(n=n)

    def tail(self, n: int = 5) -> pd.DataFrame:
        """Return the last *n* rows of generated data.

        Args:
            n: Number of rows to return.

        Returns:
            DataFrame with the last n rows.
        """
        return self.data.tail(n=n)

    # ------------------------------------------------------------------
    # Granularity
    # ------------------------------------------------------------------

    def to_granularity(self, granularity: Granularity | str) -> None:
        """Set the data granularity.

        Args:
            granularity: Granularity enum value or string (e.g. ``"5min"``).

        Raises:
            ValueError: If the granularity string is not recognized.
        """
        self.granularity = Granularity(granularity)

    @property
    def granularity(self) -> str:
        if isinstance(self._granularity, Granularity):
            return self._granularity.value
        return self._granularity

    @granularity.setter
    def granularity(self, value: Granularity | str) -> None:
        if value is not None:
            Granularity(value)  # validate
        self._granularity = value  # type: ignore[assignment]
        self._request_regeneration()

    # ------------------------------------------------------------------
    # Datetime properties
    # ------------------------------------------------------------------

    @property
    def start_datetime(self) -> str | None:
        return self._start_datetime

    @start_datetime.setter
    def start_datetime(self, value: str) -> None:
        if value is not None:
            try:
                datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError(
                    "Dates must be in ISO format (YYYY-MM-DD)."
                ) from exc
        self._start_datetime = value
        self._request_regeneration()

    @property
    def end_datetime(self) -> str | None:
        return self._end_datetime

    @end_datetime.setter
    def end_datetime(self, value: str) -> None:
        if value is not None:
            try:
                datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError(
                    "Dates must be in ISO format (YYYY-MM-DD)."
                ) from exc
        self._end_datetime = value
        self._request_regeneration()

    # ------------------------------------------------------------------
    # Collection properties
    # ------------------------------------------------------------------

    @property
    def dimensions(self) -> dict[str, Dimensions]:
        """Mapping of dimension name to Dimensions instance."""
        return {
            name: d
            for d in self._dimensions
            for name in ([d.name] if isinstance(d.name, str) else d.name)
        }

    @property
    def multi_items(self) -> dict[str, MultiItems]:
        """Mapping of comma-joined names to MultiItems instance."""
        return {
            ",".join(names): mt
            for mt in self._multi_items
            for names in ([mt.names] if isinstance(mt.names, list) else mt.names)
        }

    @property
    def metrics(self) -> dict[str, Metrics]:
        """Mapping of metric name to Metrics instance."""
        return {m.name: m for m in self._metrics}

    @property
    def baselines(self) -> dict[str, pd.DataFrame]:
        """Clean (anomaly-free) baseline DataFrames keyed by metric name.

        Populated after data generation. Empty until the first generation.
        """
        return self._baselines

    @property
    def trends(self) -> dict[str, dict[str, object]]:
        """Nested mapping: ``{metric_name: {trend_name: trend_instance}}``."""
        return {m.name: {t.name: t for t in m.trends} for m in self._metrics}

    # ------------------------------------------------------------------
    # Dimension management
    # ------------------------------------------------------------------

    def add_dimension(
        self,
        name: str,
        function: int | float | str | list[Any] | Generator[Any, None, None],
    ) -> None:
        """Add a new dimension column.

        Args:
            name: Unique column name for the dimension.
            function: An infinite generator, or a static value (int, float,
                str, list) which will be converted to a generator.

        Raises:
            DimensionError: If a dimension with this name already exists.
            ValidationError: If function is not a supported type.
        """
        if not isinstance(function, (int, float, str, list, Generator)):
            raise ValidationError(
                f"Function of dimension {name!r} must be int, float, str, "
                f"list, or a generator object."
            )

        if isinstance(function, (int, float, str)):
            function = constant(function)

        if isinstance(function, list):
            if not function:
                raise ValidationError("Dimension values list must not be empty.")
            function = cycle(function)

        dimension = Dimensions(name=name, function=function)

        if dimension in self._dimensions:
            raise DimensionError(
                f"Dimension with name {dimension.name!r} already exists."
            )

        self._dimensions.append(dimension)
        self._request_regeneration()

    def update_dimension(
        self, name: str, function: int | str | float | Generator | None
    ) -> None:
        """Update an existing dimension's generator function.

        Args:
            name: The dimension name to update.
            function: New generator or static value; if None, no-op.

        Raises:
            DimensionError: If the dimension does not exist.
            ValidationError: If the function type is invalid.
        """
        if name not in self.dimensions:
            raise DimensionError(f"Dimension with name {name!r} does not exist.")

        if function is None:
            return

        dimension = self.dimensions[name]
        if not isinstance(function, (int, str, float, Generator)):
            raise ValidationError("Function must be a generator, int, float, or str.")
        dimension.function = function

    def remove_dimension(self, name: str) -> None:
        """Remove a dimension and its column from the data.

        Args:
            name: The dimension name to remove.
        """
        if name in self.dimensions:
            self.data = self.data.drop([name], axis=1, errors="ignore")
        self._dimensions = [d for d in self._dimensions if d.name != name]

    # ------------------------------------------------------------------
    # Metric management
    # ------------------------------------------------------------------

    def add_metric(
        self,
        name: str,
        trends: list[Trends] | set[Trends],
        aggregation_type: AggregationType = AggregationType.AVG,
        anomalies: list[Anomaly] | None = None,
    ) -> None:
        """Add a new metric column composed of one or more trends.

        Args:
            name: Unique column name for the metric.
            trends: Collection of Trend instances. Their values are summed.
            aggregation_type: Aggregation method for resampling.
            anomalies: Optional list of Anomaly instances applied in order
                after trend composition.

        Raises:
            MetricError: If a metric with this name already exists, or if
                duplicate trends are detected.
        """
        if len(trends) != len(set(trends)):
            raise MetricError("Duplicate trends are present.")

        metric = Metrics(
            name=name,
            trends=set(trends),
            aggregation_type=aggregation_type,
            anomalies=anomalies,
        )

        if name in self.metrics:
            raise MetricError(f"Metric with name {name!r} already exists.")

        self._metrics.append(metric)
        self._request_regeneration()

    def remove_metric(self, name: str) -> None:
        """Remove a metric and its column from the data.

        Args:
            name: The metric name to remove.
        """
        if name in self.metrics:
            self.data = self.data.drop([name], axis=1, errors="ignore")
        self._metrics = [m for m in self._metrics if m.name != name]

    # ------------------------------------------------------------------
    # Multi-item management
    # ------------------------------------------------------------------

    def add_multi_items(
        self,
        names: list[str],
        function: int | float | str | list | Generator,
        aggregation_type: list[AggregationType | str] | None = None,
    ) -> None:
        """Add a group of linked columns generated from a single function.

        Args:
            names: List of column names.
            function: Generator that yields tuples matching len(names).
            aggregation_type: Optional aggregation methods for resampling.
                If provided, items are treated as metrics.

        Raises:
            MultiItemError: If any name overlaps with existing multi-items.
            ValidationError: If function type is invalid or generation fails.
        """
        if not isinstance(function, (int, float, str, list, Generator)):
            raise ValidationError(
                f"Function for multi-items {names} must be int, float, str, "
                f"list, or a generator object."
            )

        if isinstance(function, (int, float, str)):
            function = constant(function)

        if isinstance(function, list):
            if not function:
                raise ValidationError("Multi-item values list must not be empty.")
            function = cycle(function)

        items = MultiItems(
            names=names, function=function, aggregation_type=aggregation_type
        )

        name_set = set(names)
        for mt in self._multi_items:
            overlap = name_set & set(mt.names)
            if overlap:
                raise MultiItemError(
                    f"Multi-item with name(s) {overlap} already exists."
                )

        self._multi_items.append(items)

        try:
            self._generate_data()
        except Exception as exc:
            self._multi_items.remove(items)
            raise ValidationError(str(exc)) from exc

    def remove_multi_item(self, names: str | list[str]) -> None:
        """Remove a multi-item group and its columns.

        If any of the given names overlap with a multi-item group, that
        entire group is removed.

        Args:
            names: Name or list of names belonging to the multi-item group.
        """
        if isinstance(names, str):
            names = [names]

        name_set = set(names)
        overlapping = [mt for mt in self._multi_items if name_set & set(mt.names)]

        for item in overlapping:
            self.data.drop(item.names, axis=1, errors="ignore", inplace=True)
            self._multi_items = [
                mt for mt in self._multi_items if mt.names != item.names
            ]

    # ------------------------------------------------------------------
    # Data generation
    # ------------------------------------------------------------------

    def _request_regeneration(self) -> None:
        """Signal that data needs regeneration; defers until both datetimes are set."""
        if self._start_datetime and self._end_datetime:
            self._generate_data()

    def _validate_dates(self) -> None:
        """Validate that start/end datetimes are set and logically ordered.

        Raises:
            ValidationError: If dates are missing or start is after end.
        """
        if not self._start_datetime:
            raise ValidationError("start_datetime must be set.")
        if not self._end_datetime:
            raise ValidationError("end_datetime must be set.")

        start = datetime.fromisoformat(self._start_datetime)
        end = datetime.fromisoformat(self._end_datetime)
        if start > end:
            raise ValidationError("start_datetime cannot be after end_datetime.")

    def _generate_data(self) -> pd.DataFrame:
        """Build or rebuild the full generated DataFrame.

        Uses :class:`DataFrameBuilder` to compose dimension, metric, and
        multi-item data.

        Returns:
            The updated :attr:`data` DataFrame.
        """
        self._validate_dates()

        new_timestamps = pd.date_range(
            start=self._start_datetime,
            end=self._end_datetime,
            freq=self.granularity,
        )

        reset_needed = self._timestamps is not None and len(self._timestamps) != len(
            new_timestamps
        )

        if reset_needed or self.data.empty:
            self.data = pd.DataFrame(index=new_timestamps)

        self._timestamps = new_timestamps

        builder = DataFrameBuilder(
            dimensions=self.dimensions,
            metrics=self.metrics,
            multi_items=self.multi_items,
            rng=self._rng,
        )
        self.data = builder.build(new_timestamps, existing_data=self.data)
        self._baselines = builder.baselines
        return self.data

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    def aggregate(self, granularity: str) -> pd.DataFrame:
        """Aggregate data to a coarser granularity.

        Delegates to :func:`ts_data_generator.aggregator.aggregate_dataframe`.

        Args:
            granularity: Target granularity string (e.g. ``"h"``, ``"D"``).

        Returns:
            A new DataFrame aggregated to the target granularity.

        Raises:
            AggregationError: If target granularity is finer than current.
            KeyError: If granularity string is not recognized.
        """
        return aggregate_dataframe(
            data=self.data,
            metrics=self.metrics,
            dimensions=self.dimensions,
            multi_items=self.multi_items,
            from_granularity=self.granularity,
            to_granularity=granularity,
        )

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def normalize(self, method: str = "min-max") -> None:
        """Apply normalization to numeric columns in place.

        Args:
            method: ``"min-max"`` or ``"mean-std"``.

        Raises:
            ValidationError: If method is unrecognized.
        """
        self._normalizer = create_normalizer(method)
        self._normalizer.normalize(self.data)
        logger.info("Data normalized with method=%r.", method)

    def denormalize(self) -> None:
        """Reverse the last normalization in place."""
        if self._normalizer is None:
            logger.warning(
                "denormalize() called but no normalization has been applied."
            )
            return
        self._normalizer.denormalize(self.data)
        logger.info("Data denormalized.")

    # ------------------------------------------------------------------
    # Plotting
    # ------------------------------------------------------------------

    def plot(
        self,
        exclude: list[str] | None = None,
        include: list[str] | None = None,
        **matplotlib_kwargs: Any,
    ) -> None:
        """Plot numeric columns using matplotlib.

        Delegates to :func:`ts_data_generator.plotting.plot_time_series`.

        Args:
            exclude: Column names to exclude from the plot.
            include: Column names to include. If both are empty, all
                numeric columns (except ``epoch``) are plotted.
            matplotlib_kwargs: Additional keyword arguments for matplotlib's plot function.

        Raises:
            ValidationError: If both exclude and include are provided, or
                if no numeric columns are available.
        """
        plot_time_series(
            self.data,
            exclude=exclude,
            include=include,
            **matplotlib_kwargs,
        )
