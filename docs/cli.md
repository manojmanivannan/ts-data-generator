---
layout: default
title: CLI Reference
permalink: /cli
nav_order: 2
---

# CLI Reference

The `tsdata` command-line interface is the fastest way to generate datasets without writing Python code. It supports environment variables, JSON configurations, and powerful shorthand for complex generation.

## Basic Usage

```bash
tsdata generate --start 2024-01-01 --end 2024-01-31 --granularity D --output data.csv
```

---

## Commands

### `generate`

The primary command for data creation.

| Option | Shorthand | Description | Default |
|:---|:---|:---|:---|
| `--start` | | Start datetime (ISO 8601) | Required |
| `--end` | | End datetime (ISO 8601) | Required |
| `--granularity`| `-g` | Time step (e.g., `s`, `min`, `h`, `D`, `W`) | `5min` |
| `--dims` | `-d` | Dimension specification (Repeatable) | None |
| `--mets` | `-m` | Metric specification (Repeatable) | None |
| `--anomalies` | `-a` | Anomaly specification (Repeatable) | None |
| `--seed` | `-s` | Integer seed for reproducibility | None |
| `--output` | `-o` | Output CSV path | `stdout` |
| `--config` | `-c` | Path to JSON config file | None |
| `--preset` | `-p` | Use a built-in configuration preset | None |

#### Dimension Specification Syntax
`name:function:arg1,arg2,...` or `name:arg1,arg2,...` (defaults to `random_choice`).

Example: `--dims "region:US,EU,AP"`

#### Metric Specification Syntax
`name:Trend1(arg=val)+Trend2(arg=val)`

Example: `--mets "temp:SinusoidalTrend(amplitude=10,freq=24)+LinearTrend(limit=5)"`

### `dimensions`
Lists all available dimension functions and their expected arguments.

### `metrics`
Lists all available trend functions, their parameters, and documentation.

### `presets`
Lists available built-in presets (e.g., `daily-sales`, `minute-stock`). Use `tsdata presets <name>` for details.

---

## Configuration Files

For complex setups, use a JSON configuration file.

```json
{
  "start": "2024-01-01",
  "end": "2024-01-07",
  "granularity": "h",
  "dimensions": ["device:A,B,C"],
  "metrics": ["load:LinearTrend(limit=100)"],
  "seed": 123
}
```

Run with: `tsdata generate --config my_config.json`
