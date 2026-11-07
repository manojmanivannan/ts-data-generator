"""ts-data-generator — Synthetic time series data generation library.

Generate realistic time series datasets with configurable dimensions,
metrics, trends, and anomalies. Re-exports the primary orchestrator
:class:`DataGenerator` (and its backwards-compatible alias :class:`DataGen`),
schema models (:class:`Granularity`, :class:`AggregationType`, :class:`Metric`,
:class:`Dimension`, :class:`MultiItem`), trend classes (:class:`Trend`,
:class:`LinearTrend`, :class:`SinusoidalTrend`, :class:`MarkovTrend`,
:class:`ARNoiseTrend`, :class:`StockTrend`, :class:`WeekendTrend`,
:class:`HolidayTrend`), dimension carrier functions (:func:`random_choice`,
:func:`ordered_choice`, :func:`constant`, :func:`random_int`,
:func:`random_float`, :func:`auto_generate_name`), and anomaly injectors
(:class:`Anomaly`, :class:`PointAnomaly`, :class:`ConceptDrift`,
:class:`DriftSegment`, :class:`MissingData`, :class:`PeriodicBurstAnomaly`,
:class:`EventSchedule`). Provides both a Python API (:class:`DataGenerator`)
and a CLI (``tsdata``).

Quickstart::

    from ts_data_generator import (
        DataGenerator,
        Granularity,
        SinusoidalTrend,
        random_choice,
    )

    dg = DataGenerator(
        start_datetime="2024-01-01",
        end_datetime="2024-01-07",
        granularity=Granularity.HOUR,
    )
    dg.add_dimension("region", random_choice(["US", "EU", "AP"]))
    dg.add_metric("temperature", [SinusoidalTrend(amplitude=10, freq=24)])
    print(dg.data.head())
"""

from ts_data_generator._version import __version__
from ts_data_generator.anomalies import (
    Anomaly,
    ConceptDrift,
    DriftSegment,
    EventSchedule,
    MissingData,
    PeriodicBurstAnomaly,
    PointAnomaly,
)
from ts_data_generator.data_gen import DataGen, DataGenerator
from ts_data_generator.functions import (
    auto_generate_name,
    constant,
    ordered_choice,
    random_choice,
    random_float,
    random_int,
)
from ts_data_generator.schema.models import (
    AggregationType,
    Dimension,
    Granularity,
    Metric,
    MultiItem,
)
from ts_data_generator.trends import (
    ARNoiseTrend,
    HolidayTrend,
    LinearTrend,
    MarkovTrend,
    SinusoidalTrend,
    StockTrend,
    Trend,
    WeekendTrend,
)

__all__ = [
    "ARNoiseTrend",
    "AggregationType",
    "Anomaly",
    "ConceptDrift",
    "DataGen",
    "DataGenerator",
    "Dimension",
    "DriftSegment",
    "EventSchedule",
    "Granularity",
    "HolidayTrend",
    "LinearTrend",
    "MarkovTrend",
    "Metric",
    "MissingData",
    "MultiItem",
    "PeriodicBurstAnomaly",
    "PointAnomaly",
    "SinusoidalTrend",
    "StockTrend",
    "Trend",
    "WeekendTrend",
    "__version__",
    "auto_generate_name",
    "constant",
    "ordered_choice",
    "random_choice",
    "random_float",
    "random_int",
]
