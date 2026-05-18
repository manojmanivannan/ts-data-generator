---
layout: default
title: Python API
permalink: /api
nav_order: 3
---

# Python API Reference

The Python API provides the most flexibility, allowing you to integrate the generator into your ML training pipelines, simulation environments, or testing suites.

## The `DataGen` Class

The central orchestrator for data generation.

```python
from ts_data_generator import DataGen
dg = DataGen(seed=42)
```

### Configuration Methods

#### `to_granularity(granularity: str)`
Sets the generation time step using Pandas frequency strings.
- **Example**: `dg.to_granularity("15min")`

#### `add_dimension(name: str, function: Iterable)`
Adds a categorical or continuous column.
- **Parameters**:
    - `name`: The resulting column name in the DataFrame.
    - `function`: An infinite iterator (generator) that yields values.

#### `add_metric(name, trends, anomalies=None, aggregation_type=None)`
Adds a numeric metric column built from trends.
- **Parameters**:
    - `name`: Column name.
    - `trends`: A list or set of `Trend` objects.
    - `anomalies`: (Optional) A list of `Anomaly` objects.
    - `aggregation_type`: (Optional) How to aggregate this metric when using `.aggregate()`.

#### `add_multi_items(names, function)`
Adds multiple columns that are generated together (linked).
- **Parameters**:
    - `names`: List of column names.
    - `function`: An infinite iterator yielding tuples of the same length as `names`.

### Data Retrieval

#### `dg.data` (Property)
Triggers the generation process (if not already cached) and returns a `pandas.DataFrame`.

#### `dg.aggregate(granularity: str)`
Returns a *new* DataFrame aggregated to a coarser granularity.
- **Example**: `hourly_df = dg.aggregate("h")`

---

## Utility Components

### Trends
Located in `ts_data_generator.utils.trends`.
- `SinusoidalTrend`, `LinearTrend`, `WeekendTrend`, `HolidayTrend`, `ARNoiseTrend`, `MarkovTrend`, `StockTrend`.

### Anomalies
Located in `ts_data_generator.anomalies`.
- `PointAnomaly`, `MissingData`, `ConceptDrift`.

### Dimension Helpers
Located in `ts_data_generator.utils.functions`.
- `random_choice`, `random_int`, `random_float`, `constant`, `ordered_choice`, `auto_generate_name`.
