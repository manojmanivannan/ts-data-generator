---
layout: default
title: CLI Reference
permalink: /cli
nav_order: 2
---

# CLI Reference

The `tsdata` command-line interface is a powerful, zero-code tool for rapid prototyping, generating datasets, and managing simulation settings. It supports direct terminal parameters, full JSON configuration files, and environment variable overrides.

---

## 🚀 Running Without Installation

You can use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to run the CLI in a disposable environment — no install required:

```bash
uvx --from ts-data-generator tsdata --help
```

> **Important:** Use `--from` (not `--with`). The PyPI package is called `ts-data-generator` while the executable is `tsdata`, so `--from` tells uvx which package provides the command. Using `--with` will produce a warning and may resolve the wrong package.

---

## 📋 Get a Sample Config File

Not sure what a valid JSON config looks like? Use `--show-sample-config` to dump a ready-to-edit config to stdout:

```bash
# Save the sample config to a file
tsdata generate --show-sample-config > my_config.json

# Edit it, then generate data from your custom config
tsdata generate --config my_config.json
```

The sample config exercises all features — dimensions, composed metrics, and anomalies — so you can delete what you don't need and tweak the rest.

---

## 💻 Commands

### 1. `tsdata generate`
The primary command for creating synthetic datasets and saving them to CSV.

#### CLI Command Arguments & Flags:

| Flag | Shorthand | Type | Description | Default / Required |
|:---|:---|:---|:---|:---|
| `--start` | | `str` | Start date/time string (ISO format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`) | **Required** |
| `--end` | | `str` | End date/time string (ISO format) | **Required** |
| `--granularity`| `-g` | `str` | Time step frequency (e.g. `s`, `min`, `5min`, `h`, `D`, `W`, `ME`, `Y`) | **Required** |
| `--dims` | `-d` | `str` | Dimension specification. Can be repeated. | `None` |
| `--mets` | `-m` | `str` | Metric (trend composition) specification. Can be repeated. | `None` |
| `--anomalies` | `-a` | `str` | Anomaly specification keyed by metric. Can be repeated. | `None` |
| `--seed` | `-s` | `int` | Seed for PCG64 deterministic generation. | `None` |
| `--output` | `-o` | `str` | Destination path to save the generated CSV. | **Required** |
| `--config` | `-c` | `str` | Path to a local JSON configuration file. | `None` |
| `--preset` | `-p` | `str` | Use a built-in config preset. | `None` |
| `--show-sample-config` | | flag | Print a sample JSON config to stdout and exit. | `None` |

#### Simple Shorthand CLI Example:
```bash
tsdata generate \
  --start 2024-01-01 --end 2024-01-07 --granularity D \
  --dims "region:US,EU,AP" \
  --mets "sales:LinearTrend(slope=40)+SinusoidalTrend(amplitude=10,freq=7)" \
  --output sales_data.csv
```

---

### 2. `tsdata dimensions`
Lists all available dimension generator functions, their parameters, and CLI shorthand examples.

```bash
$ tsdata dimensions
```
*Expected Output:*
```
Available dimension functions:

  auto_generate_name(category: str) -> str
    → name:auto_generate_name:mycat
  constant(value: int | str | float | list | tuple) -> collections.abc.Generator[int | str | float, None, None]
    → name:constant:10
  ordered_choice(iterable: collections.abc.Iterable[~T]) -> collections.abc.Generator[~T, None, None]
    → name:ordered_choice:A,B,C
  random_choice(iterable: collections.abc.Iterable[~T]) -> collections.abc.Generator[~T, None, None]
    → name:random_choice:A,B,C
  random_float(start: float, end: float) -> collections.abc.Generator[float, None, None]
    → name:random_float:0.0,1.0
  random_int(start: int, end: int) -> collections.abc.Generator[int, None, None]
    → name:random_int:1,100
```

---

### 3. `tsdata metrics`
Lists all available metric trend functions, their exact parameters, and CLI shorthand examples. Uses the `Registry` class to reflectively discover all `Trends` subclasses in the `ts_data_generator.utils.trends` module.

```bash
$ tsdata metrics
```
*Expected Output:*
```
Available trend functions:

  ARNoiseTrend(name: 'str' = 'default', coefficients: 'list[float] | None' = None, noise_std: 'float' = 1.0, decay: 'float | None' = None, order: 'int' = 1) -> 'None'
    → sales:ARNoiseTrend(coefficients=[0.5,-0.2],noise_std=0.5)
  HolidayTrend(name: 'str' = 'default', country: 'str' = 'US', effect: 'float' = 50.0, pre_window: 'int' = 3, post_window: 'int' = 2, direction: "Literal['up', 'down']" = 'up', dates: 'list[str] | None' = None) -> 'None'
    → sales:HolidayTrend(country='US',effect=50,pre_window=3,post_window=2,direction='up')
  LinearTrend(name: 'str' = 'default', offset: 'float' = 0.0, noise_level: 'float' = 0.0, slope: 'float' = 2.0) -> 'None'
    → sales:LinearTrend(offset=0,noise_level=1,slope=10)
  MarkovTrend(name: 'str' = 'default', states: 'list[str] | None' = None, values: 'list[float] | None' = None, stickiness: 'float | None' = None, transition_matrix: 'list[list[float]] | None' = None, noise_std: 'float' = 0.0) -> 'None'
    → sales:MarkovTrend(states=['low','high'],values=[10,100],stickiness=0.9,noise_std=5)
  SinusoidalTrend(name: 'str' = 'default', amplitude: 'float' = 1.0, freq: 'float' = 1.0, phase: 'float' = 0.0, noise_level: 'float' = 0.0) -> 'None'
    → sales:SinusoidalTrend(amplitude=1,freq=24,phase=0,noise_level=0)
  StockTrend(name: 'str' = 'default', amplitude: 'float' = 15.0, direction: "Literal['up', 'down']" = 'up', noise_level: 'float' = 0.0) -> 'None'
    → sales:StockTrend(amplitude=15.0,direction='up',noise_level=0.0)
  WeekendTrend(name: 'str' = 'default', weekend_effect: 'float' = 1.0, direction: "Literal['up', 'down']" = 'up', noise_level: 'float' = 0.0, limit: 'float' = 10.0) -> 'None'
    → sales:WeekendTrend(weekend_effect=10,direction='up',noise_level=0.5,limit=10)
```

> [!NOTE]
> The `Trends` base class is automatically filtered out of the list. The CLI uses a `Registry` object with `base_class=Trends` to ensure only concrete trend subclasses are available.

---

### 4. `tsdata presets`
Lists available built-in presets or displays configuration details for a specific preset.

```bash
$ tsdata presets
```
*Expected Output:*
```
Available presets:

  daily-sales
    Start: 2024-01-01, End: 2024-01-31, Granularity: D
    Dimensions: 2, Metrics: 1
    Output: daily_sales.csv
  hourly-metrics
    Start: 2024-01-01, End: 2024-01-02, Granularity: h
    Dimensions: 1, Metrics: 2
    Output: hourly_metrics.csv
  minute-stock
    Start: 2024-01-01, End: 2024-01-02, Granularity: 5min
    Dimensions: 1, Metrics: 1
    Output: minute_stock.csv
  weekly-revenue
    Start: 2024-01-01, End: 2024-12-31, Granularity: D
    Dimensions: 2, Metrics: 1
    Output: weekly_revenue.csv
  monthly-recurring
    Start: 2024-01-01, End: 2024-12-31, Granularity: D
    Dimensions: 1, Metrics: 1
    Output: monthly_mrr.csv
```

To see exact config details of a preset:
```bash
$ tsdata presets daily-sales
```
*Expected Output:*
```
Preset: daily-sales

  Start: 2024-01-01
  End: 2024-01-31
  Granularity: D
  Dimensions: product:A,B,C,D, region:X,Y,Z
  Metrics: sales:LinearTrend(slope=30)+WeekendTrend(weekend_effect=100)
  Output: daily_sales.csv

Usage: tsdata generate --preset daily-sales --output <output.csv>
Or override specific values:
  tsdata generate --preset daily-sales --start 2024-02-01 --output mydata.csv
```

> [!NOTE]
> Presets define default values for `start`, `end`, `granularity`, `dims`, `mets`, and `output`.  CLI flags override preset values — use `--start`, `--end`, or `--output` to customise without editing the preset.

---

## 🔌 CLI Architecture: Pluggable Registries

The CLI parser uses the `schema/parser.py` module to extract strings like `name=func(args)` into strongly typed `DimensionSpec`, `TrendSpec`, and `AnomalySpec` dataclasses. The parser uses `Registry` objects (`ts_data_generator.utils.registry`) to look up components securely.

```python
# Each registry is instantiated with a module path and optional filters
_DIMENSION_REGISTRY = Registry(
    "ts_data_generator.utils.functions",
    name_filter=lambda n: not n.startswith("_"),
)
_TREND_REGISTRY = Registry(
    "ts_data_generator.utils.trends",
    name_filter=lambda n: not n.startswith("_") and n != "Trends",
    base_class=Trends,
)
_ANOMALY_REGISTRY = Registry(
    "ts_data_generator.anomalies",
    name_filter=lambda n: not n.startswith("_") and n != "Anomaly",
    base_class=Anomaly,
)
```

- **`name_filter`** controls which names appear in error messages and `list_available()`.
- **`base_class`** ensures only concrete subclasses of `Trends` or `Anomaly` are available, filtering out abstract bases and non-class values.

To add a new CLI-pluggable type (e.g. a custom trend), simply define a class that inherits from `Trends` in the `ts_data_generator.utils.trends` module — the Registry discovers it automatically. No need to register it manually.

---

## 📄 JSON Configuration Files

For large, multi-metric datasets or production pipelines, configuring generation inside a clean JSON file is highly recommended. 

To run a configuration file:
```bash
tsdata generate --config config.json
```

### Complete Example 1: `stock_price_simulation.json`
```json
{
  "start": "2024-01-01",
  "end": "2024-01-02",
  "granularity": "5min",
  "seed": 42,
  "dimensions": [
    "ticker:ordered_choice:AAPL,GOOG,MSFT",
    "exchange:constant:NASDAQ"
  ],
  "metrics": [
    "price:StockTrend(amplitude=150.0,noise_level=0.2)"
  ],
  "anomalies": [
    "price:MissingData(mode=random,probability=0.005)"
  ],
  "output": "simulated_stocks.csv"
}
```

### Complete Example 2: `iot_telemetry.json`
```json
{
  "start": "2024-06-01T00:00:00",
  "end": "2024-06-07T23:55:00",
  "granularity": "5min",
  "seed": 9876,
  "dimensions": [
    "device_id:auto_generate_name:sensor_"
  ],
  "metrics": [
    "temp:LinearTrend(offset=22.0,slope=15)+SinusoidalTrend(amplitude=3.0,freq=1.0)+ARNoiseTrend(decay=0.9,noise_std=0.2)",
    "humidity:SinusoidalTrend(amplitude=15.0,freq=1.0)+ARNoiseTrend(decay=0.8,noise_std=0.5)"
  ],
  "anomalies": [
    "temp:PointAnomaly(probability=0.005,magnitude=(5.0,15.0))+MissingData(mode=burst,burst_probability=0.002,min_length=3,max_length=6)"
  ],
  "output": "iot_telemetry.csv"
}
```

### Complete Example 3: `concept_drift.json`
```json
{
  "start": "2024-01-01T00:00:00",
  "end": "2024-01-07T23:00:00",
  "granularity": "h",
  "seed": 42,
  "dimensions": [
    "region:North,South"
  ],
  "metrics": [
    "cpu:LinearTrend(offset=30,slope=2)+SinusoidalTrend(amplitude=10,freq=1)"
  ],
  "anomalies": [
    "cpu:PointAnomaly(probability=0.01,magnitude=(10,20))",
    "cpu:ConceptDrift(start_timestamp=2024-01-03T12:00:00,transition_window=3600,target_mean=80,target_std=5,hold_duration=14400,restore=true)"
  ],
  "output": "concept_drift.csv"
}
```

---

## 🌐 Environment Variables

You can override or define default values for **any** CLI argument using environment variables prefixed with `TSDATA_`. 

Command-line parameters passed directly will always override their corresponding environment variables.

```bash
# 1. Export defaults
export TSDATA_START="2024-01-01"
export TSDATA_END="2024-01-31"
export TSDATA_GRANULARITY="D"
export TSDATA_SEED="12345"

# 2. Run the command (automatically picks up export values)
tsdata generate \
  --dims "region:US,EU" \
  --mets "visitors:LinearTrend(slope=10)" \
  --output visitors.csv
```
