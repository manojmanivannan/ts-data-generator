---
layout: default
title: Python API
permalink: /api
nav_order: 5
---

# Python API Reference

The Python API provides the ultimate flexibility, allowing you to seamlessly integrate the generator into your machine learning pipelines, testing suites, or simulation environments.

This page orients you to the `DataGen` surface — the knobs, the read-outs, and a one-line gist of every method grouped by workflow stage. For the *why* behind it — how dimensions, metrics, trends, anomalies, and the deterministic pipeline fit together — see [`Core Concepts`](concepts.md). Authoritative per-method reference (signatures, args, raises, examples) lives in the docstrings; each method name below links to its source.

---

## 🏛️ The `DataGen` Class

`DataGen` generates synthetic time series data with dimensions, metrics, and trends. It is the central orchestrator that coordinates dates, timestamps, dimensions, composed metric trends, anomalies, and transforms.

```python
from ts_data_generator import DataGen
dg = DataGen(seed=42)
```

### `__init__`

```python
DataGen(
    dimensions: list[Dimensions] | None = None,
    metrics: list[Metrics] | None = None,
    multi_items: list[MultiItems] | None = None,
    start_datetime: str | datetime | pd.Timestamp = "",
    end_datetime: str | datetime | pd.Timestamp = "",
    granularity: Granularity = Granularity.FIVE_MIN,
    seed: int | None = None,
    expand_dimensions: bool = False,
    scale_variance: float = 0.0,
    workers: int | None = None,
) -> None
```

Full parameter semantics are documented in the [`__init__` docstring](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py).

### Properties — the knobs & read-outs

| property | what it is |
|---|---|
| `data` | The generated, timestamp-indexed DataFrame; regenerated whenever configuration changes. |
| `state` | Current pipeline state: `CONFIGURED` → `GENERATED` → `NORMALIZED`. |
| `granularity` | Time-step spacing of the generated series, as a string (e.g. `"5min"`). |
| `expand_dimensions` | Whether per-combination Cartesian-product expansion is enabled. |
| `scale_variance` | Std. dev. of the log-normal factor scaling metric slices across combinations. |
| `workers` | Number of parallel worker processes for data generation (`None` = sequential). |
| `start_datetime` | Start bound of the generated time range. |
| `end_datetime` | End bound of the generated time range. |
| `dimensions` | Mapping of dimension name to `Dimensions` instance. |
| `metrics` | Mapping of metric name to `Metrics` instance. |
| `multi_items` | Mapping of comma-joined names to `MultiItems` instance. |
| `trends` | Nested mapping: `{metric_name: {trend_name: trend_instance}}`. |
| `baselines` | Clean (anomaly-free) baseline `DataFrame`s keyed by metric name. |

---

## 📋 Method summary

Every `DataGen` method lives in [`data_gen.py`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py); each row links there. Signature, args, raises, and examples are in the docstring — this table is the orientation map.

### Configure

| method | gist |
|---|---|
| [`to_granularity`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Set the data granularity. |
| [`add_dimension`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Add a new dimension column. |
| [`update_dimension`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Update an existing dimension's generator function. |
| [`remove_dimension`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Remove a dimension and its column from the data. |
| [`add_metric`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Add a new metric column composed of one or more trends. |
| [`remove_metric`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Remove a metric and its column from the data. |
| [`add_multi_items`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Add a group of linked columns generated from a single function. |
| [`remove_multi_item`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Remove a multi-item group and its columns. |

### Retrieve / transform / visualize

| method | gist |
|---|---|
| [`shape`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Return the (rows, columns) shape of the generated data. |
| [`head`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Return the first *n* rows of generated data. |
| [`tail`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Return the last *n* rows of generated data. |
| [`aggregate`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Aggregate data to a coarser granularity. |
| [`normalize`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Apply normalization to numeric columns in place. |
| [`denormalize`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Reverse the last normalization in place. |
| [`plot`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Plot numeric columns using matplotlib. |

### Dunders (user-facing)

| symbol | gist |
|---|---|
| [`__len__`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Number of rows in the generated data. |
| [`__repr__`](https://github.com/manojmanivannan/ts-data-generator/blob/main/src/ts_data_generator/data_gen.py) | Debug representation listing configured dimensions, metrics, and multi-items. |

---

## 🐍 Quickstart: the core flow

The shortest end-to-end lifecycle the doctests cover: construct → add a dimension → compose a metric from trends → read out the DataFrame → aggregate.

```python
from ts_data_generator import DataGen
from ts_data_generator.schema.models import AggregationType
from ts_data_generator.utils.functions import random_choice
from ts_data_generator.utils.trends import LinearTrend, SinusoidalTrend

# 1. Construct — dates, granularity, and a seed for determinism
dg = DataGen(
    start_datetime="2024-01-01T00:00:00",
    end_datetime="2024-01-07T23:00:00",
    granularity="h",
    seed=12345,
)

# 2. Add a categorical dimension
dg.add_dimension("region", random_choice(["North", "South", "East"]))

# 3. Compose a metric from multiple trends (summed into the base signal)
dg.add_metric(
    name="cpu_utilization",
    trends={LinearTrend(offset=40.0, slope=2.0), SinusoidalTrend(amplitude=12.0, freq=1.0)},
    aggregation_type=AggregationType.AVG,
)

# 4. Retrieve the generated DataFrame
df = dg.data
print(df.head())

# 5. Aggregate to a coarser granularity (AVG applied per metric)
daily_df = dg.aggregate(granularity="D")
print(daily_df.head())
```

The wider surface — linked multi-items, anomaly injection, normalization/denormalization, and plotting — is exercised in each method's docstring examples. For the mental model behind this pipeline, see [`Core Concepts`](concepts.md).