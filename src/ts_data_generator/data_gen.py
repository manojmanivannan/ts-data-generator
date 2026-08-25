"""Core :class:`DataGen` engine for synthetic time series generation.

Orchestrates dimension, metric, and multi-item models to produce a
timestamp-indexed DataFrame.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from datetime import datetime
from enum import Enum
from itertools import chain, cycle
from typing import TYPE_CHECKING, Any, cast

import pandas as pd

from ts_data_generator.aggregator import aggregate_dataframe
from ts_data_generator.carriers import DimensionCarrier, DomainCarrier
from ts_data_generator.exceptions import (
    ConfigurationError,
    DimensionError,
    MetricError,
    MultiItemError,
    ValidationError,
)
from ts_data_generator.expand import build_expanded_dataframe
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


def _list_carrier(values: list[Any]) -> DimensionCarrier:
    """Wrap a static list as a domain-carrying carrier (no opaque itertools.cycle).

    The list is captured as the carrier's domain before it is cycled, so the
    expand path reads it directly instead of sampling an opaque C-level cycle.
    """
    values = list(values)

    def _source() -> Any:
        while True:
            yield from cycle(values)

    return DomainCarrier(_source(), values, "list")


def _tuple_list_carrier(values: list[tuple[Any, ...]]) -> DimensionCarrier:
    """Wrap a static list of tuples as a domain-carrying carrier.

    The tuples are captured as the carrier's domain before cycling, so the
    expand path reads it directly instead of sampling an opaque generator.
    """
    values = list(values)

    def _source() -> Any:
        while True:
            yield from cycle(values)

    return DomainCarrier(_source(), values, "list")


class PipelineState(Enum):
    CONFIGURED = "configured"
    GENERATED = "generated"
    NORMALIZED = "normalized"


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
        expand_dimensions: When ``True``, emit one row per
            *(timestamp x Cartesian product of all enumerable dimensions'
            distinct values)*, each combination carrying its own independently
            regenerated, reproducible metric series. Defaults to ``False``
            (one row per timestamp). Per-dimension ``expand`` overrides on
            ``add_dimension`` and ``add_multi_items`` make this flag an
            overridable default (#57, #58): ``expand=True`` forces a dimension
            into the product, ``expand=False`` opts it out (regenerating
            within-series). A non-enumerable dimension that is actually
            expanding raises :class:`~ts_data_generator.exceptions.ExpandError`;
            ``expand=False`` is the escape hatch. Multi-items compose by role:
            linked metrics regenerate per combination; linked dimensions expand
            over their tuple domain (#58).

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
        start_datetime: str | datetime | pd.Timestamp = "",
        end_datetime: str | datetime | pd.Timestamp = "",
        granularity: Granularity = Granularity.FIVE_MIN,
        seed: int | None = None,
        expand_dimensions: bool = False,
    ) -> None:
        self._dimensions = dimensions or []
        self._metrics = metrics or []
        self._multi_items = multi_items or []
        self._start_datetime = start_datetime
        self._end_datetime = end_datetime
        self._granularity = granularity
        self._normalizer: Normalizer | None = None
        self._timestamps: pd.DatetimeIndex | None = None
        self._pending_regeneration = False
        self._rng: RNGProtocol = SeedableRNG(seed) if seed is not None else DefaultRNG()
        self._expand_dimensions = expand_dimensions

        self.data: pd.DataFrame = pd.DataFrame()
        self._baselines: dict[str, pd.DataFrame] = {}
        self._state: PipelineState = PipelineState.CONFIGURED

        if start_datetime and end_datetime:
            self._generate_data()

    @property
    def state(self) -> PipelineState:
        return self._state

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
    # Expansion
    # ------------------------------------------------------------------

    @property
    def expand_dimensions(self) -> bool:
        """Whether per-combination Cartesian-product expansion is enabled.

        When ``True``, generation emits one row per
        *(timestamp x product of all enumerable dimensions' distinct values)*,
        each combination carrying its own independently regenerated metric
        series. Setting it triggers a regeneration.
        """
        return self._expand_dimensions

    @expand_dimensions.setter
    def expand_dimensions(self, value: bool) -> None:
        self._expand_dimensions = bool(value)
        self._request_regeneration()

    def _should_expand(self) -> bool:
        """Whether generation should take the expansion path.

        The global flag on always selects the expansion path (per-dim
        ``expand=False`` opts a dimension out of the *product*, not out of the
        path); with the global flag off, the path runs only when some dimension
        or linked dimension explicitly forces expansion via ``expand=True``
        (#57, #58). Pure flag logic — no domain resolution, so it never raises
        ``ExpandError``.
        """
        if self._expand_dimensions:
            return True
        if any(d.expand is True for d in self._dimensions):
            return True
        if any(mi.expand is True for mi in self._multi_items if not mi.aggregation_type):
            return True
        return False

    # ------------------------------------------------------------------
    # Datetime properties
    # ------------------------------------------------------------------

    @property
    def start_datetime(self) -> str | datetime | pd.Timestamp:
        return self._start_datetime

    @start_datetime.setter
    def start_datetime(self, value: str) -> None:
        if not value:
            try:
                datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError("Dates must be in ISO format (YYYY-MM-DD).") from exc
        self._start_datetime = value
        self._request_regeneration()

    @property
    def end_datetime(self) -> str | datetime | pd.Timestamp:
        return self._end_datetime

    @end_datetime.setter
    def end_datetime(self, value: str) -> None:
        if not value:
            try:
                datetime.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError("Dates must be in ISO format (YYYY-MM-DD).") from exc
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
        return {",".join(names): mt for mt in self._multi_items for names in [mt.names]}

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
        domain: list[Any] | None = None,
        expand: bool | None = None,
    ) -> None:
        """Add a new dimension column.

        ``function`` is stored as a domain-carrying carrier so the expand path
        can read its value domain with no generator introspection. Scalars and
        static lists are converted to carriers at construction; the static-list
        branch carries its domain directly (no opaque ``itertools.cycle``).

        Args:
            name: Unique column name for the dimension.
            function: An infinite generator (carrier or plain), or a static
                value (int, float, str, list) which is converted to a carrier.
            domain: Explicit value domain for an opaque custom/pre-built
                generator whose domain the engine cannot see structurally (the
                ``domain=`` escape hatch). Cannot be supplied to a carrier that
                already carries a domain, and cannot override the non-expandable
                range / auto-name rejection.
            expand: Per-dimension expansion override for ``expand_dimensions``
                (#57, decision #52). ``None`` (default) inherits the global
                flag; ``True`` forces this dimension into the Cartesian product
                even when the global flag is off; ``False`` opts it out of the
                product — it regenerates one-value-per-timestamp within each
                series instead, and a non-enumerable dim marked ``expand=False``
                is excluded from the product without raising ``ExpandError``.

        Raises:
            DimensionError: If a dimension with this name already exists.
            ValidationError: If function is not a supported type, or ``domain=``
                is misused (supplied to a carrier, or to a non-expandable
                range/auto-name generator).
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
            function = _list_carrier(function)

        function = self._apply_domain(name, function, domain)

        dimension = Dimensions(name=name, function=function, expand=expand)

        if dimension in self._dimensions:
            raise DimensionError(f"Dimension with name {dimension.name!r} already exists.")

        self._dimensions.append(dimension)
        self._request_regeneration()

    @staticmethod
    def _apply_domain(
        name: str,
        function: DimensionCarrier | Generator[Any, None, None],
        domain: list[Any] | None,
    ) -> DimensionCarrier | Generator[Any, None, None]:
        """Apply the ``domain=`` escape hatch and eager range rejection.

        ``domain=`` is the escape hatch for opaque generators (plain
        ``Generator`` objects with no carried domain): it wraps them in an
        expandable carrier. It cannot be supplied to a carrier that already
        carries a domain, and — critically — it cannot override the
        non-expandable range / auto-name rejection, which is eager here.
        """
        if domain is None:
            return function

        if isinstance(function, DimensionCarrier):
            if not function.expandable:
                raise ValidationError(
                    f"domain= cannot be supplied to {function.func_name}() "
                    f"for dimension {name!r}: it is a non-enumerable "
                    f"{function.func_name} generator. "
                    f"{function.non_expandable_reason}"
                )
            raise ValidationError(
                f"domain= is only for opaque generators without a known domain; "
                f"dimension {name!r} already carries its domain via "
                f"{function.func_name}()."
            )

        # Opaque plain generator — wrap it in an expandable carrier carrying the
        # declared domain. next() still delegates to the original generator.
        carrier_name = getattr(function, "__name__", "custom")
        return DomainCarrier(function, list(domain), carrier_name)

    def update_dimension(self, name: str, function: int | str | float | Generator | None) -> None:
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
        domain: list[Any] | None = None,
        expand: bool | None = None,
    ) -> None:
        """Add a group of linked columns generated from a single function.

        Args:
            names: List of column names.
            function: Generator that yields tuples matching len(names), or a
                static list of tuples/lists which is converted to a carrier.
            aggregation_type: Optional aggregation methods for resampling.
                If provided, items are treated as linked metrics.
            domain: Explicit tuple domain for an opaque custom/pre-built
                generator whose domain the engine cannot see structurally (the
                ``domain=`` escape hatch). Cannot be supplied to a carrier that
                already carries a domain, and cannot override non-expandable
                rejection.
            expand: Per-dimension expansion override for ``expand_dimensions``
                (for linked dimensions). ``None`` (default) inherits the global
                flag; ``True`` forces this linked dimension into the Cartesian
                product even when the global flag is off; ``False`` opts it out
                of the product (regenerating within-series).

        Raises:
            MultiItemError: If any name overlaps with existing multi-items.
            ValidationError: If function type is invalid, domain is invalid, or generation fails.
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
            tuple_values: list[tuple[Any, ...]] = []
            for item in function:
                t = tuple(item) if isinstance(item, (list, tuple)) else (item,)
                if len(t) != len(names):
                    raise ValidationError(
                        f"Multi-item values entry {item!r} length ({len(t)}) "
                        f"does not match len(names) ({len(names)})."
                    )
                tuple_values.append(t)
            function = _tuple_list_carrier(tuple_values)

        function = self._apply_multi_item_domain(names, function, domain)

        items = MultiItems(
            names=names,
            function=function,
            aggregation_type=aggregation_type,
            expand=expand,
        )

        name_set = set(names)
        for mt in self._multi_items:
            overlap = name_set & set(mt.names)
            if overlap:
                raise MultiItemError(f"Multi-item with name(s) {overlap} already exists.")

        self._multi_items.append(items)

        try:
            self._request_regeneration()
        except Exception:
            self._multi_items.remove(items)
            raise

    @staticmethod
    def _apply_multi_item_domain(
        names: list[str],
        function: DimensionCarrier | Generator[Any, None, None],
        domain: list[Any] | None,
    ) -> DimensionCarrier | Generator[Any, None, None]:
        """Apply the ``domain=`` escape hatch and eager validation for multi-items."""
        if domain is None:
            return function

        if not domain:
            raise ValidationError("Multi-item domain list must not be empty.")

        tuple_domain: list[tuple[Any, ...]] = []
        for item in domain:
            t = tuple(item) if isinstance(item, (list, tuple)) else (item,)
            if len(t) != len(names):
                raise ValidationError(
                    f"Multi-item domain entry {item!r} length ({len(t)}) "
                    f"does not match len(names) ({len(names)})."
                )
            tuple_domain.append(t)

        compound_name = ",".join(names)
        if isinstance(function, DimensionCarrier):
            if not function.expandable:
                raise ValidationError(
                    f"domain= cannot be supplied to {function.func_name}() "
                    f"for dimension {compound_name!r}: it is a non-enumerable "
                    f"{function.func_name} generator. "
                    f"{function.non_expandable_reason}"
                )
            raise ValidationError(
                f"domain= is only for opaque generators without a known domain; "
                f"dimension {compound_name!r} already carries its domain via "
                f"{function.func_name}()."
            )

        carrier_name = getattr(function, "__name__", "custom")
        return DomainCarrier(function, tuple_domain, carrier_name)

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
            self._multi_items = [mt for mt in self._multi_items if mt.names != item.names]

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

        start = datetime.fromisoformat(cast(str, self._start_datetime))
        end = datetime.fromisoformat(cast(str, self._end_datetime))
        if start > end:
            raise ValidationError("start_datetime cannot be after end_datetime.")

    def _generate_data(self) -> pd.DataFrame:
        """Build or rebuild the full generated DataFrame.

        Returns:
            The updated :attr:`data` DataFrame.
        """
        self._validate_dates()

        new_timestamps = pd.date_range(
            start=self._start_datetime,
            end=self._end_datetime,
            freq=self.granularity,
        )

        reset_needed = self._timestamps is not None and len(self._timestamps) != len(new_timestamps)

        self._timestamps = new_timestamps

        if self._should_expand():
            self.data = self._generate_expanded_data(new_timestamps)
            self._state = PipelineState.GENERATED
            return self.data

        if reset_needed or self.data.empty:
            self.data = pd.DataFrame(index=new_timestamps)

        existing_columns: set[str] = set()
        if not self.data.empty:
            existing_columns = set(self.data.columns)

        metric_df = self._build_metrics(new_timestamps, existing_columns)
        dimension_df = self._build_dimensions(new_timestamps, existing_columns)
        multi_item_df = self._build_multi_items(new_timestamps, existing_columns)

        data = self.data

        for component in (dimension_df, metric_df, multi_item_df):
            if not component.empty:
                data = pd.concat([data, component], axis=1)

        if "epoch" not in data.columns:
            unix_timestamps = [int(ts.timestamp()) for ts in new_timestamps]
            data = pd.concat(
                [
                    data,
                    pd.DataFrame(unix_timestamps, columns=["epoch"], index=new_timestamps),
                ],
                axis=1,
            )

        self.data = self._sort_columns(data)
        self._state = PipelineState.GENERATED
        return self.data

    def _generate_expanded_data(self, timestamps: pd.DatetimeIndex) -> pd.DataFrame:
        """Build the expanded DataFrame: one row per (timestamp x combination).

        The Cartesian product runs over *expanding* dimensions only — those whose
        per-dim ``expand`` override (falling back to the global flag) is true and
        which carry an enumerable domain; each combination carries its own
        independently regenerated metric series seeded per combination.
        Non-expanding dimensions regenerate one-value-per-timestamp within each
        series instead of being broadcast (#57). Multi-items compose by role:
        linked dimensions join dimension expansion over their tuple domain;
        linked metrics regenerate per combination (#58). Expanding dimensions
        stay groupby keys, so aggregation holds unchanged.

        When the engine is unseeded, a default base seed is derived per
        generation — mirroring how :class:`~ts_data_generator.random.DefaultRNG`
        makes unseeded ordinary generation work — so expand-then-filter works
        without the user thinking about seeding, while remaining
        non-deterministic across runs like ordinary unseeded generation.

        Args:
            timestamps: The full timestamp index for the dataset.

        Returns:
            The expanded DataFrame, sorted timestamp-first then by dimension
            value, with ``epoch`` appended and columns ordered per
            :meth:`_sort_columns` (alphabetical dimension names in expand mode).

        Raises:
            ExpandError: If a dimension that is actually expanding is
                non-enumerable (numeric range / auto-generated name / opaque
                generator without ``domain=``). ``expand=False`` opts a
                non-enumerable dimension out instead of erroring.
        """
        base_seed = self._rng.seed
        if base_seed is None:
            # Unseeded: derive a random base seed this run (see docstring).
            base_seed = int(self._rng.integers(0, 2**32))

        data = build_expanded_dataframe(
            dimensions=self.dimensions,
            metrics=self.metrics,
            timestamps=timestamps,
            base_seed=base_seed,
            global_expand=self._expand_dimensions,
            multi_items=self.multi_items,
        )

        if "epoch" not in data.columns:
            data = data.assign(epoch=data.index.map(lambda ts: int(ts.timestamp())))

        return self._sort_columns(data, dims_alphabetical=True)

    def _build_metrics(
        self, timestamps: pd.DatetimeIndex, existing_columns: set[str]
    ) -> pd.DataFrame:
        df = pd.DataFrame(index=timestamps)
        for metric in self.metrics.values():
            if metric.name not in existing_columns:
                result = metric.generate(timestamps, rng=self._rng)
                self._baselines[metric.name] = result.baseline
                df = pd.concat([df, result.signal], axis=1)
                if not result.labels.empty:
                    df = pd.concat([df, result.labels], axis=1)
        return df

    def _build_dimensions(
        self, timestamps: pd.DatetimeIndex, existing_columns: set[str]
    ) -> pd.DataFrame:
        df = pd.DataFrame(index=timestamps)
        for dimension in self.dimensions.values():
            if dimension.name not in existing_columns:
                generated = dimension.generate(timestamps, rng=self._rng)
                df = pd.concat([df, generated], axis=1)
        return df

    def _build_multi_items(
        self, timestamps: pd.DatetimeIndex, existing_columns: set[str]
    ) -> pd.DataFrame:
        df = pd.DataFrame(index=timestamps)
        for multi_item in self.multi_items.values():
            if any(item not in existing_columns for item in multi_item.names):
                generated = multi_item.generate(timestamps, rng=self._rng)
                df = pd.concat([df, generated], axis=1)
        return df

    def _sort_columns(self, data: pd.DataFrame, *, dims_alphabetical: bool = False) -> pd.DataFrame:
        linked_dims = {k: mi for k, mi in self.multi_items.items() if not mi.aggregation_type}
        linked_metrics = {k: mi for k, mi in self.multi_items.items() if mi.aggregation_type}

        if dims_alphabetical:
            # Expand mode: column order follows the same order-insensitive
            # principle as row ordering (alphabetical dimension-name order),
            # so output is identical regardless of the add order of dimensions.
            # Compound keys get one alphabetical slot; component columns sort
            # in declared names order.
            all_dim_keys = sorted(list(self.dimensions.keys()) + list(linked_dims.keys()))
            dimension_names: list[str] = []
            for key in all_dim_keys:
                if key in self.dimensions:
                    dimension_names.append(key)
                else:
                    dimension_names.extend(linked_dims[key].names)
        else:
            dimension_names = list(self.dimensions.keys())

        metric_names = list(self.metrics.keys())

        column_order: list[str] = ["epoch", *dimension_names]
        for name in metric_names:
            column_order.append(name)
            label_col = f"{name}_anomaly"
            if label_col in data.columns:
                column_order.append(label_col)

        if dims_alphabetical:
            for mi in linked_metrics.values():
                column_order.extend(mi.names)
        else:
            multi_item_names = list(
                chain.from_iterable(s.split(",") for s in self.multi_items.keys())
            )
            column_order.extend(multi_item_names)

        available = [col for col in dict.fromkeys(column_order) if col in data.columns]
        return data.reindex(columns=available)

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
        if self._state == PipelineState.CONFIGURED:
            raise ConfigurationError("Cannot normalize before generating data. Access .data first.")
        self._normalizer = create_normalizer(method)
        self._normalizer.normalize(self.data)
        logger.info("Data normalized with method=%r.", method)
        self._state = PipelineState.NORMALIZED

    def denormalize(self) -> None:
        """Reverse the last normalization in place."""
        if self._state != PipelineState.NORMALIZED:
            logger.warning("Data is not normalized. Denormalize has no effect.")
            return
        if self._normalizer is None:
            logger.warning("denormalize() called but no normalization has been applied.")
            return
        self._normalizer.denormalize(self.data)
        logger.info("Data denormalized.")
        self._state = PipelineState.GENERATED

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
