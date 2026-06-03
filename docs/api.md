---
layout: default
title: Python API
permalink: /api
nav_order: 5
---

# Python API Reference

The Python API provides the ultimate flexibility, allowing you to seamlessly integrate the generator into your machine learning pipelines, testing suites, or simulation environments.

---

## 🏛️ The `DataGen` Class

The `DataGen` class is the central orchestrator that coordinates dates, timestamps, dimensions, composed metric trends, anomalies, and transforms.

```python
from ts_data_generator import DataGen
dg = DataGen(seed=42)
```

### Initializer Parameters:
*   `dimensions` (list[Dimensions] | None): Initial dimensions list (default `None`).
*   `metrics` (list[Metrics] | None): Initial metrics list (default `None`).
*   `multi_items` (list[MultiItems] | None): Initial multi-items list (default `None`).
*   `start_datetime` (str | None): Start date/time string (ISO format `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`).
*   `end_datetime` (str | None): End date/time string (ISO format).
*   `granularity` (Granularity | str): Time step interval (default `Granularity.FIVE_MIN`).
*   `seed` (int | None): Seed for deterministic PCG64 random generation. When set, all randomness flows through an isolated `SeedableRNG` instance backed by PCG64.

### Properties:
*   `.data` — The generated `pd.DataFrame`, indexed by timestamp. Triggers lazy generation if not yet built.
*   `.granularity` — Read/write property. Get or set the current granularity (accepts `Granularity` enum or string like `"h"`, `"D"`). Writing triggers regeneration.
*   `.start_datetime` / `.end_datetime` — Read/write ISO datetime strings. Writing triggers regeneration.
*   `.dimensions` — Mapping of dimension name to `Dimensions` instance.
*   `.metrics` — Mapping of metric name to `Metrics` instance.
*   `.multi_items` — Mapping of comma-joined names to `MultiItems` instance.
*   `.trends` — Nested mapping `{metric_name: {trend_name: trend_instance}}`.

---

## ⚙️ Configuration Methods

### `.to_granularity(granularity: Granularity | str)`
Sets the generation time step using a predefined frequency or Pandas alias string.
*   **Examples**: `"s"`, `"min"`, `"5min"`, `"h"`, `"D"`, `"W"`, `"ME"`, `"YE"`.

### `.add_dimension(name: str, function: int | float | str | list | Generator)`
Adds a categorical or context column mapping to the index.
*   **Parameters**:
    *   `name`: The resulting column name in the DataFrame.
    *   `function`: An infinite generator, static value, or list that cycles. Static values (`int`, `float`, `str`) are wrapped as constants; lists are cycled infinitely.
*   **Raises**: `DimensionError` if a dimension with this name already exists. `ValidationError` if the function type is unsupported.

### `.update_dimension(name: str, function: int | str | float | Generator | None)`
Update an existing dimension's generator function.
*   **Parameters**:
    *   `name`: The dimension name to update.
    *   `function`: New generator or static value. Pass `None` to skip.
*   **Raises**: `DimensionError` if the dimension does not exist.

### `.remove_dimension(name: str)`
Remove a dimension and its column from the data.
*   **Parameters**:
    *   `name`: The dimension name to remove.

### `.add_metric(name: str, trends: list[Trends] | set[Trends], aggregation_type: AggregationType = AggregationType.AVG, anomalies: list[Anomaly] | None = None)`
Composes and adds a numeric metric column by summing multiple trends together.
*   **Parameters**:
    *   `name`: The resulting column name in the DataFrame.
    *   `trends`: A list or set of `Trends` subclasses (e.g. `SinusoidalTrend`, `LinearTrend`). Their generated arrays are summed to form the base signal.
    *   `aggregation_type`: The `AggregationType` enum (e.g. `AVG`, `SUM`, `MIN`, `MAX`) used when resampling via `.aggregate()`. Defaults to `AVG`.
    *   `anomalies`: An optional list of `Anomaly` instances applied sequentially *after* trend composition.
*   **Raises**: `MetricError` if a metric with this name already exists, or if duplicate trends are detected.

### `.remove_metric(name: str)`
Remove a metric and its column from the data.
*   **Parameters**:
    *   `name`: The metric name to remove.

### `.add_multi_items(names: list[str], function: int | float | str | list | Generator, aggregation_type: list[AggregationType | str] | None = None)`
Adds multiple correlated columns that are generated together from a single iterator (e.g., city and country).
*   **Parameters**:
    *   `names`: A list of column names.
    *   `function`: A generator yielding tuples of values matching the length of `names`. Static values are wrapped as constants; lists are cycled.
    *   `aggregation_type`: Optional list of aggregation methods for resampling.
*   **Raises**: `MultiItemError` if any name overlaps with existing multi-items. `ValidationError` if generation fails.

### `.remove_multi_item(names: str | list[str])`
Remove a multi-item group and its columns from the data.
*   If any of the given names overlap with a multi-item group, that entire group is removed.

---

## 📊 Retrieval, Aggregation, Normalization & Visualization

### `.data` (Property)
Generates the data (if not already generated) and returns a clean, fully aligned `pandas.DataFrame` indexed by timestamp. Generation runs a pipeline combining dimensions, metrics, and multi-items, applying any configured anomalies.

### `.state` (Property)
Returns the current `PipelineState` (`CONFIGURED`, `GENERATED`, or `NORMALIZED`). Guard rails are in place to ensure you don't call `.normalize()` before generating data, or `.denormalize()` on unnormalized data.

### `.baselines` (Property)
Returns a dictionary mapping metric names to their clean `pandas.DataFrame` baseline (i.e. the signal generated by Trends *before* any Anomalies were applied). Useful for training anomaly detection models.

### `.shape() -> tuple[int, int]`
Return the `(rows, columns)` shape of the generated data.

### `.head(n: int = 5) -> pd.DataFrame`
Return the first *n* rows of generated data.

### `.tail(n: int = 5) -> pd.DataFrame`
Return the last *n* rows of generated data.

### `.aggregate(granularity: str) -> pd.DataFrame`
Aggregates the generated data to a coarser granularity (e.g., daily down to weekly, or hourly down to daily).
*   **Rule**: You can only aggregate to a *coarser* granularity than the current one. Uses `Granularity.coarser_than()` and `Granularity.finer_than()` for validation, which replaced the old module-level `_GRANULARITY_ORDER` dict.
*   It automatically applies the metric-specific aggregation types (`AVG`, `SUM`, etc.) and multi-item aggregation types defined when the metrics were added.

### `.normalize(method: str = "min-max")`
Apply normalization to numeric columns in place.
*   `method`: `"min-max"` or `"mean-std"` (default `"min-max"`).
*   Uses the `Normalizer` class from `ts_data_generator.transforms.normalizer`.

### `.denormalize()`
Reverse the last normalization in place. Safe to call even if no normalization has been applied.

### `.plot(include: list[str] | None = None, exclude: list[str] | None = None, **matplotlib_kwargs)`
Renders a quick, native line plot of your numeric columns using matplotlib.
*   `include`: Explicit list of column names to plot.
*   `exclude`: List of column names to omit from plotting.
*   `matplotlib_kwargs`: Additional keyword arguments passed to matplotlib's `plot` function (e.g. `figsize`, `color`, `linestyle`).
*   **Raises**: `ImportError` if matplotlib is not installed. Install with `uv add 'ts-data-generator[plotting]'`.

---

## 🐍 Full End-to-End Lifecycle Script

Here is a complete, copy-pasteable script that exercises the full `DataGen` lifecycle: setup, dimensions, composition of metrics with trends and anomalies, linked multi-items, dataframe extraction, normalization, aggregation, and plotting.

```python
from ts_data_generator import DataGen
from ts_data_generator.schema.models import AggregationType
from ts_data_generator.utils.functions import random_choice, ordered_choice
from ts_data_generator.utils.trends import LinearTrend, SinusoidalTrend, ARNoiseTrend
from ts_data_generator.anomalies import PointAnomaly, MissingData

# 1. Initialize with dates, granularity, and seed
dg = DataGen(
    start_datetime="2024-01-01T00:00:00",
    end_datetime="2024-01-07T23:00:00",
    granularity="h",
    seed=12345
)

# 2. Add categorical dimensions
dg.add_dimension("region", random_choice(["North", "South", "East"]))
dg.add_dimension("priority", ordered_choice(["low", "high"]))

# 3. Add correlated Multi-Item dimensions (linked columns)
def server_specs_generator():
    specs = [
        ("srv_alpha", "intel", "16GB"),
        ("srv_beta", "amd", "32GB"),
        ("srv_gamma", "arm", "8GB")
    ]
    while True:
        yield random_choice(specs) # yields tuple: (srv, CPU, RAM)

dg.add_multi_items(
    names=["server_name", "cpu_vendor", "ram_capacity"],
    function=server_specs_generator()
)

# 4. Compose Metric 1: CPU load (summing growth + cycle + AR noise, adding spikes)
cpu_trends = {
    LinearTrend(offset=40.0, slope=2.0),
    SinusoidalTrend(amplitude=12.0, freq=1.0)
}
cpu_anomalies = [
    PointAnomaly(probability=0.015, mode="additive", magnitude=(30.0, 45.0))
]
dg.add_metric(
    name="cpu_utilization",
    trends=cpu_trends,
    aggregation_type=AggregationType.AVG, # CPU load aggregated via average
    anomalies=cpu_anomalies
)

# 5. Compose Metric 2: Completed Transactions (using SUM aggregation and bursty dropouts)
trans_trends = {
    LinearTrend(offset=500.0, slope=10.0),
    SinusoidalTrend(amplitude=150.0, freq=1.0, phase=4.0)
}
trans_anomalies = [
    MissingData(mode="burst", burst_probability=0.01, min_length=2, max_length=4)
]
dg.add_metric(
    name="completed_transactions",
    trends=trans_trends,
    aggregation_type=AggregationType.SUM, # Revenue/Transactions aggregated via sum
    anomalies=trans_anomalies
)

# 6. Retrieve the generated Pandas DataFrame
df = dg.data
print("--- Raw Generated DataFrame ---")
print(df.head(10))

# 7. Normalize numeric columns in-place
dg.normalize(method="min-max")
print("\n--- Normalized DataFrame ---")
print(dg.data.head())

# 8. Denormalize back to original values
dg.denormalize()

# 9. Aggregate to daily granularity
# cpu_utilization is automatically averaged, completed_transactions is summed!
daily_df = dg.aggregate(granularity="D")
print("\n--- Daily Aggregated DataFrame ---")
print(daily_df.head())

# 10. Render quick built-in line charts of our numeric metrics
dg.plot(include=["cpu_utilization"])
```

---

## 🏗️ Internal Architecture

### `DataGen` Pipeline
`DataGen` directly orchestrates generation across dimensions, metrics, and multi-items in a deterministic pipeline. It maintains state via `PipelineState` (`CONFIGURED`, `GENERATED`, `NORMALIZED`).

### `MetricResult` (`ts_data_generator.schema.models`)
When a metric generates data, it now returns a `MetricResult` NamedTuple containing two `pd.DataFrame`s: the `baseline` (pure trends) and the `signal` (trends + anomalies). This guarantees access to the clean pre-contamination signal.

### `SeedableRNG` / `DefaultRNG` / `RNGProtocol` (`ts_data_generator.random`)
Handles deterministic randomness. `SeedableRNG` wraps a PCG64-backed `numpy.random.Generator`. When `DataGen` is not seeded, a `DefaultRNG` is used. This implements a unified `RNGProtocol` ensuring deterministic behaviour is threaded thoroughly across Trends, Anomalies, and Dimensions without global side effects.

### `Schema Parser` (`ts_data_generator.schema.parser`)
Isolates string parsing and validation into strict `dataclasses` (`DimensionSpec`, `TrendSpec`, `AnomalySpec`, `PresetConfig`). The CLI and Python interfaces use this parser alongside the lightweight `Registry` to look up available components.

### `Normalizer` (`ts_data_generator.transforms.normalizer`)
Provides `min-max` and `mean-std` normalization with exact denormalization support.

### `aggregate_dataframe` (`ts_data_generator.aggregator`)
Handles DataFrame resampling to coarser granularities, respecting per-metric aggregation types and granularity ordering via `Granularity.coarser_than()` and `Granularity.finer_than()`.
