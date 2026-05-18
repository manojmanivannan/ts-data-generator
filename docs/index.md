---
layout: default
title: Home
---

# Synthetic Time Series Data Generator

Generate realistic synthetic time series datasets with configurable dimensions, metrics, composable trend functions, and injectable anomalies — via a Python API or the `tsdata` CLI.

## Quickstart

### CLI

```bash
uvx --python 3.11 --from ts-data-generator tsdata generate \
    --preset daily-sales --output sales.csv
```

### Python API

```python
from ts_data_generator import DataGen
from ts_data_generator.utils.trends import SinusoidalTrend

dg = DataGen(seed=42)
dg.start_datetime = "2024-01-01"
dg.end_datetime = "2024-01-07"
dg.to_granularity("h")

dg.add_metric(
    "temperature",
    {SinusoidalTrend(amplitude=10, freq=24)},
)

print(dg.data.head())
```

## Documentation

- [CLI Reference]({{ site.baseurl }}/cli)
- [Python API Reference]({{ site.baseurl }}/api)
- [Trend Functions]({{ site.baseurl }}/trends)
- [Anomaly Injection]({{ site.baseurl }}/anomalies)
- [Dimension Generators]({{ site.baseurl }}/dimensions)
- [Schema Imputing]({{ site.baseurl }}/imputer)
