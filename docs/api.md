---
layout: default
title: Python API
---

# Python API Reference

The Python API allows for programmatic data generation and integration into your data science workflows.

## `DataGen` Class

The central orchestrator for data generation.

### Initialization

```python
from ts_data_generator import DataGen
dg = DataGen(seed=42)
```

### Methods

#### `add_dimension(name, function)`
Adds a categorical or continuous column.
- `name`: Column name.
- `function`: An infinite generator function or a helper from `utils.functions`.

#### `add_metric(name, trends, anomalies=None, aggregation_type=None)`
Adds a numeric metric column.
- `name`: Column name.
- `trends`: A set or list of `Trend` objects.
- `anomalies`: Optional list of `Anomaly` objects.
- `aggregation_type`: Optional `AggregationType` (SUM, MEAN, MIN, MAX).

#### `add_multi_items(names, function)`
Adds multiple linked columns from a single generator.
- `names`: List of column names.
- `function`: A generator yielding tuples of values.

#### `to_granularity(granularity)`
Sets the target time step.

#### `aggregate(granularity)`
Resamples the generated data to a coarser granularity.

### Properties

#### `data`
Returns the generated data as a `pandas.DataFrame`.
