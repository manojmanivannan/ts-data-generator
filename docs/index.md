---
layout: default
title: Home
nav_order: 1
description: "Professional-grade synthetic time series data generation."
permalink: /
has_children: true
---

# Synthetic Time Series Data Generator

**Synthetic Time Series Data Generator** (`ts-data-generator`) is a professional-grade Python library and command-line interface (CLI) engineered for data scientists, ML engineers, and software developers who require realistic, deterministic, and highly configurable synthetic time series datasets.

Whether you are benchmarking anomaly detection models, testing forecasting algorithms, or populating frontend dashboards before live data becomes available, `ts-data-generator` provides clean, composable building blocks to simulate complex, real-world temporal patterns.

---

{: .new }
> **Deterministic by Design**: Every dataset generated is perfectly reproducible using a PCG64-backed pseudo-random number generator (PRNG) seed. This guarantees consistent generation across different machines, environments, and Python versions.

---

## 🚀 Getting Started in 5 Minutes

### 1. Installation

Install the package via `pip` or using `uv` (recommended):

```bash
pip install ts-data-generator
# Or with uv:
uv pip install ts-data-generator
```

*Optional extras (install features as needed):*
```bash
# Schema imputing / CSV reverse-engineering (requires scipy)
pip install "ts-data-generator[imputer]"

# Built-in line plotting (requires matplotlib)
pip install "ts-data-generator[plotting]"

# Country-specific holiday detection (requires holidays)
pip install holidays

# All optional features
pip install "ts-data-generator[imputer,plotting]" holidays
```

### 2. Choose Your Workflow

`ts-data-generator` adapts to your workspace. Choose between rapid terminal prototyping or robust pipeline scripting.

<div class="row" style="display: flex; gap: 20px; flex-wrap: wrap;">
  <div class="col" style="flex: 1; min-width: 300px; background: #fafafa; border: 1px solid #eee; border-radius: 6px; padding: 15px;" markdown="1">
### 💻 Rapid Terminal Prototyping (CLI)

Generate a production-ready dataset in a single terminal line with dimensions and composed metrics:

```bash
tsdata generate \
  --start 2024-01-01 \
  --end 2024-01-07 \
  --granularity h \
  --dims "region:US,EU,AP" \
  --mets "sales:LinearTrend(slope=10)+SinusoidalTrend(amplitude=10,freq=24)" \
  --output sales_data.csv
```
  </div>
  <div class="col" style="flex: 1; min-width: 300px; background: #fafafa; border: 1px solid #eee; border-radius: 6px; padding: 15px;" markdown="1">
### 🐍 Pipeline Integration (Python API)

Compose your generators directly inside your training/validation pipelines or notebooks:

```python
from ts_data_generator import DataGen
from ts_data_generator.utils.trends import LinearTrend, SinusoidalTrend

dg = DataGen(seed=42)
dg.start_datetime = "2024-01-01"
dg.end_datetime = "2024-01-07"
dg.to_granularity("h")

# Composing a metric from multiple trends
dg.add_metric(
    "sales",
    {
        LinearTrend(offset=10.0, slope=10),
        SinusoidalTrend(amplitude=10.0, freq=24.0)
    }
)

df = dg.data # Retrieves the Pandas DataFrame
dg.plot() # Instant interactive visualization
```
  </div>
</div>

---

## 🧩 Architectural Highlights

The generator is designed from the ground up around **Modular Compositions**:

*   **Realistic Trends & Seasonality**: Compose complex signals by layering multiple trends (Sinusoidal, Linear, AR Noise, Markov Chains, stock-like random walks) onto a single metric. [Explore Trend Functions]({{ site.baseurl }}/trends){: .btn .btn-outline .btn-xs }
*   **Contextual Dimensions**: Enrich your metrics with dimensions (such as `region`, `device_id`, or `user_type`) using built-in or custom infinite iterables. [Explore Dimensions]({{ site.baseurl }}/dimensions){: .btn .btn-outline .btn-xs }
*   **Stochastic Anomaly Injection**: Inject realistic anomalies (isolated spikes, bursty data drops, or gradual concept drifts) *after* your trends are calculated to benchmark your detection pipelines. [Explore Anomalies]({{ site.baseurl }}/anomalies){: .btn .btn-outline .btn-xs }
*   **Schema Imputing**: Bootstrap a generation config instantly by analyzing an existing historical CSV file. [Explore Imputer]({{ site.baseurl }}/imputer){: .btn .btn-outline .btn-xs }

---

## ⚖️ Why Composable Primitives?

Most synthetic data generators lie at two extremes: they are either too simple (generating basic white noise) or too complex (requiring expensive black-box GAN models that lack direct interpretability). 

`ts-data-generator` sits perfectly in the middle. By utilizing **Composable Primitives**, you retain total control over the mathematical laws governing your data. You explicitly specify the *rules* (the base growth, seasonal variations, noise patterns, and failure events) and the generator handles the complex temporal alignment, index building, dimension broadcasting, and execution.

---

[Quickstart CLI Reference]({{ site.baseurl }}/cli){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View the Python API]({{ site.baseurl }}/api){: .btn .fs-5 .mb-4 .mb-md-0 }
