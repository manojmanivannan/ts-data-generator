<div align="center">

<img src="https://raw.githubusercontent.com/manojmanivannan/ts-data-generator/refs/heads/main/tsdata-logo.svg" alt="ts-data-generator logo" width="100"/>

# Synthetic Time Series Data Generator

[![CI](https://github.com/manojmanivannan/ts-data-generator/actions/workflows/ci.yaml/badge.svg)](https://github.com/manojmanivannan/ts-data-generator/actions/workflows/ci.yaml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

Generate realistic synthetic time series datasets with configurable dimensions,
metrics, composable trend functions, and injectable anomalies — via a Python API
or the `tsdata` CLI or [online](https://ts-data-generator.fastapicloud.dev/)

<img src="https://github.com/manojmanivannan/ts-data-generator/raw/main/notebooks/image.png" alt="sample plot" width="800"/>

</div>

---

## 📚 Documentation

For complete details on features, API reference, CLI usage, and advanced configuration, visit our documentation site:

👉 **[https://manojmanivannan.github.io/ts-data-generator/](https://manojmanivannan.github.io/ts-data-generator/)**

---

## Features

- **Realistic Data:** Mimic real-world time series with trends, seasonality, and noise.
- **Composable Trends:** Layer multiple functions (Sinusoidal, Linear, AR Noise, Markov) to create complex signals.
- **Multivariate Dimension Expansion:** Expand dimensions to their full Cartesian product (`expand_dimensions`) with independent, reproducible per-combination metric series and per-dimension control.
- **Correlated Multi-Items:** Generate linked dimension tuples and correlated metric groups simultaneously (`add_multi_items`).
- **Injectable Anomalies:** Simulate failures with point anomalies, missing data gaps, and concept drifts.
- **Deterministic:** Guaranteed reproducibility via a seedable RNG.
- **CLI & API:** Use the `tsdata` CLI for rapid prototyping or the Python API for production pipelines.
- **Schema Imputing:** Reverse-engineer generation configs from existing CSV datasets.

---

## Quickstart

### Installation

```bash
pip install ts-data-generator
```

> **No install needed?** Run the CLI directly with [uv](https://docs.astral.sh/uv/):
> ```bash
> uvx --from ts-data-generator tsdata --help
> ```
> Use `--from` (not `--with`) because the package name (`ts-data-generator`) differs from the executable name (`tsdata`).

### CLI Usage

```bash
# Standard generation (one row per timestamp)
tsdata generate --start 2024-01-01 --end 2024-01-07 --granularity h \
    --dims "region:US,EU,AP" \
    --mets "sales:LinearTrend(slope=45)+SinusoidalTrend(amplitude=10,freq=24)" \
    --output sales.csv

# Multivariate expansion (Cartesian product of dimensions with independent series per combo)
tsdata generate --start 2024-01-01 --end 2024-01-07 --granularity h \
    --dims "region=random_choice(US,EU)" \
    --dims "env=random_choice(prod,dev)" \
    --mets "sales:LinearTrend(slope=45)+SinusoidalTrend(amplitude=10,freq=24)" \
    --expand-dimensions \
    --output expanded_sales.csv
```

### Python API

```python
from ts_data_generator import DataGen
from ts_data_generator.utils.functions import random_choice
from ts_data_generator.utils.trends import SinusoidalTrend, LinearTrend

# Expand dimensions across Cartesian product of dimensions
dg = DataGen(
    start_datetime="2024-01-01",
    end_datetime="2024-01-07",
    granularity="h",
    seed=42,
    expand_dimensions=True,
)

dg.add_dimension("region", random_choice(["US", "EU"]))
dg.add_dimension("environment", random_choice(["prod", "dev"]))
dg.add_metric("sales", {LinearTrend(offset=100, slope=10), SinusoidalTrend(amplitude=20, freq=24)})

# Linked correlated columns
dg.add_multi_items(
    names=["city", "country"],
    function=[("New York", "US"), ("London", "UK")],
)

df = dg.data
print(f"Generated {len(df)} rows across {df.groupby(['region', 'environment', 'city']).ngroups} combinations")
dg.plot()
```

---

## License

MIT — see [LICENSE](./LICENSE).
