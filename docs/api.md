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
*   `seed` (int | None): Seed for deterministic PCG64 random generation.

---

## ⚙️ Configuration Methods

### `.to_granularity(granularity: Granularity | str)`
Sets the generation time step using a predefined frequency or Pandas alias string.
*   **Examples**: `"s"`, `"min"`, `"5min"`, `"h"`, `"D"`, `"W"`, `"ME"`, `"YE"`.

### `.add_dimension(name: str, function: int | float | str | list | Generator)`
Adds a categorical or context column mapping to the index.
*   **Parameters**:
    *   `name`: The resulting column name in the DataFrame.
    *   `function`: An infinite generator, static value, or list that cycles.

### `.add_metric(name: str, trends: list[object] | set[object], aggregation_type: AggregationType = AggregationType.AVG, anomalies: list[Anomaly] | None = None)`
Composes and adds a numeric metric column by summing multiple trends together.
*   **Parameters**:
    *   `name`: The resulting column name in the DataFrame.
    *   `trends`: A list or set of `Trend` instances. Their generated arrays are summed.
    *   `aggregation_type`: The `AggregationType` enum (e.g. `AVG`, `SUM`, `MIN`, `MAX`) used when resampling via `.aggregate()`. Defaults to `AVG`.
    *   `anomalies`: An optional list of `Anomaly` instances applied sequentially *after* trend composition.

### `.add_multi_items(names: list[str], function: int | float | str | list | Generator, aggregation_type: list[AggregationType | str] | None = None)`
Adds multiple correlated columns that are generated together from a single iterator (e.g., city and country).
*   **Parameters**:
    *   `names`: A list of column names.
    *   `function`: A generator yielding tuples of values matching the length of `names`.
    *   `aggregation_type`: Optional list of aggregation methods for resampling.

---

## 📊 Retrieval, Aggregation, & Visualization

### `.data` (Property)
Triggers the underlying dataframe builder (if not already compiled/cached) and returns a clean, fully aligned `pandas.DataFrame` indexed by timestamp.

### `.aggregate(granularity: str) -> pd.DataFrame`
Aggregates the generated data to a coarser granularity (e.g., daily down to weekly, or hourly down to daily).
*   **Rule**: You can only aggregate to a *coarser* granularity than the current one (e.g., you cannot downsample hourly to minutes).
*   It automatically applies the metric-specific aggregation types (`AVG`, `SUM`, etc.) defined when the metrics were added.

### `.plot(include: list[str] | None = None, exclude: list[str] | None = None)`
Renders a quick, native line plot of your numeric columns using matplotlib.
*   `include`: Explicit list of column names to plot.
*   `exclude`: List of column names to omit from plotting.

---

## 🐍 Full End-to-End Lifecycle Script

Here is a complete, copy-pasteable script that exercises the full `DataGen` lifecycle: setup, dimensions, composition of metrics with trends and anomalies, linked multi-items, dataframe extraction, aggregation, and plotting.

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
    LinearTrend(offset=40.0, limit=2.0),
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
    LinearTrend(offset=500.0, limit=10.0),
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

# 7. Aggregate to daily granularity
# cpu_utilization is automatically averaged, completed_transactions is summed!
daily_df = dg.aggregate(granularity="D")
print("\n--- Daily Aggregated DataFrame ---")
print(daily_df.head())

# 8. Render quick built-in line charts of our numeric metrics
dg.plot(include=["cpu_utilization"])
```
