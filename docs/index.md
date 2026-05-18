---
layout: default
title: Home
nav_order: 1
description: "Professional-grade synthetic time series data generation."
permalink: /
has_children: true
---

# Synthetic Time Series Data Generator

**Synthetic Time Series Data Generator** is a robust Python library and CLI designed for data scientists and engineers who need realistic, deterministic, and highly configurable time series data.

Whether you're benchmarking anomaly detection models, testing forecasting algorithms, or building dashboards without real data, this tool provides the primitives you need to simulate complex real-world behaviors.

---

{: .new }
> **Deterministic by Design**: Every dataset generated can be perfectly reproduced using a seed, ensuring your experiments are consistent across environments.

## Key Features

- **Realistic Trends**: Compose complex signals using Sinusoidal, Linear, AR(p) Noise, Markov Chains, and more. [Learn More]({{ site.baseurl }}/trends)
- **Anomaly Injection**: Inject point anomalies, missing data gaps (random, burst, or patterned), and gradual concept drifts. [Learn More]({{ site.baseurl }}/anomalies)
- **Dimension Context**: Add categorical context like regions, device IDs, or user types. [Learn More]({{ site.baseurl }}/dimensions)
- **CLI & API**: Seamlessly transition from rapid CLI prototyping to production-grade Python pipelines. [Learn More]({{ site.baseurl }}/cli)
- **Schema Imputing**: Bootstrap your generation configuration by analyzing existing CSV datasets. [Learn More]({{ site.baseurl }}/imputer)
- **Visualization**: Built-in plotting for quick data verification. [Learn More]({{ site.baseurl }}/visualize)

---

## Quickstart

### Installation

```bash
pip install ts-data-generator
```

### Generate Data in One Line (CLI)

```bash
tsdata generate --start 2024-01-01 --end 2024-01-07 --granularity D --dims "product:A,B" --mets "sales:LinearTrend(limit=100)" --output sales.csv
```

### Powerful Python API

```python
from ts_data_generator import DataGen
from ts_data_generator.utils.trends import SinusoidalTrend

dg = DataGen(seed=42)
dg.start_datetime = "2024-01-01"
dg.end_datetime = "2024-01-07"
dg.to_granularity("h")

dg.add_metric(
    "temperature",
    {SinusoidalTrend(amplitude=10, freq=24, noise_level=0.5)},
)

df = dg.data
dg.plot() # Built-in visualization
```

---

## Why use this?

Most synthetic data generators are either too simple (random noise) or too complex (black-box GANs). This library sits in the middle: **Composable Primitives**. You define the *components* of your data (trends, noise, anomalies), and the engine handles the temporal alignment and generation.

[Get Started with the CLI Reference]({{ site.baseurl }}/cli){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View the Python API]({{ site.baseurl }}/api){: .btn .fs-5 .mb-4 .mb-md-0 }
---
