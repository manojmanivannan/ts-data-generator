---
layout: default
title: CLI Reference
permalink: /cli
nav_order: 2
---

# CLI Reference

The `tsdata` command-line interface is a powerful tool for rapid prototyping and generating datasets without writing Python code. It supports environment variables, JSON configurations, and powerful shorthand syntax.

## Commands

### `tsdata generate`
The primary command for data creation.

| Option | Shorthand | Description | Default |
|:---|:---|:---|:---|
| `--start` | | Start datetime (ISO 8601 or YYYY-MM-DD) | Required |
| `--end` | | End datetime (ISO 8601 or YYYY-MM-DD) | Required |
| `--granularity`| `-g` | Time step (e.g., `s`, `min`, `5min`, `h`, `D`, `W`, `ME`, `Y`) | Required |
| `--dims` | `-d` | Dimension specification. Repeat for multiple. | None |
| `--mets` | `-m` | Metric specification. Repeat for multiple. | None |
| `--anomalies` | `-a` | Anomaly specification keyed by metric. | None |
| `--seed` | `-s` | Integer seed for deterministic randomness. | None |
| `--output` | `-o` | Output CSV path. | Required |
| `--config` | `-c` | Path to a JSON configuration file. | None |
| `--preset` | `-p` | Use a built-in configuration preset. | None |

#### Dimension Syntax
`name:function:arg1,arg2,...` or `name:val1,val2,...` (defaults to `random_choice`).

#### Metric Syntax
`name:Trend1(arg=val)+Trend2(arg=val)`

#### Anomaly Syntax
`metric_name:Anomaly1(arg=val)+Anomaly2(arg=val)`

---

### `tsdata dimensions`
Lists all available dimension functions, their signatures, and examples.

### `tsdata metrics`
Lists all available trend functions and their parameters.

### `tsdata presets`
Lists available built-in presets. Use `tsdata presets <name>` to see the details of a specific preset.

---

## Configuration Files

For complex datasets or reproducible pipelines, use a JSON configuration file.

### Config Schema

```json
{
  "start": "2024-01-01",
  "end": "2024-01-31",
  "granularity": "h",
  "dimensions": [
    "region:random_choice:US,EU,AP",
    "product:A,B,C"
  ],
  "metrics": [
    "sales:LinearTrend(limit=1000)+SinusoidalTrend(amplitude=50,freq=7)",
    "stock:StockTrend(amplitude=10)"
  ],
  "anomalies": [
    "sales:PointAnomaly(probability=0.01,magnitude=100)",
    "stock:MissingData(mode=burst,burst_probability=0.01)"
  ],
  "seed": 42,
  "output": "my_dataset.csv"
}
```

**Usage:**
```bash
tsdata generate --config my_config.json
```

---

## Environment Variables

You can set any CLI option using environment variables with the prefix `TSDATA_`.

```bash
export TSDATA_START="2024-01-01"
export TSDATA_END="2024-01-07"
export TSDATA_GRANULARITY="5min"
tsdata generate --output output.csv ...
```

## Presets

Presets are "batteries-included" configurations for common use cases.

- `daily-sales`: 1 month of daily data with product/region dimensions and weekend effects.
- `hourly-metrics`: 1 day of hourly sensor data (temp/humidity).
- `minute-stock`: 1 day of 5-minute interval stock price simulation.

To use a preset:
```bash
tsdata generate --preset daily-sales --output sales.csv
```
