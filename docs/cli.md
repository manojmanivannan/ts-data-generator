---
layout: default
title: CLI Reference
---

# CLI Reference

The `tsdata` CLI provides a powerful way to generate datasets from the command line or via configuration files.

## Commands

### `generate`

The main command to create datasets.

| Option | Description |
|---|---|
| `--start` | Start datetime (e.g., `2024-01-01`) |
| `--end` | End datetime (e.g., `2024-01-31`) |
| `--granularity` | Time step (`s`, `min`, `5min`, `h`, `D`, `W`, `ME`, `Y`) |
| `--dims` | Dimension specifications. Format: `name:function:args` or `name:args` |
| `--mets` | Metric specifications. Format: `name:Trend1(args)+Trend2(args)` |
| `--anomalies` | Anomaly specifications. Format: `metric:Anomaly1(args)+Anomaly2(args)` |
| `--seed` | Integer seed for reproducibility |
| `--output` | CSV file path to save the data |
| `--config` | Path to a JSON configuration file |
| `--preset` | Use a built-in configuration preset |

### `dimensions`

List all available dimension functions and their usage.

### `metrics`

List all available trend functions (metrics) and their parameters.

### `presets`

List available preset configurations or show details for a specific preset.

---

## Configuration File

You can use a JSON file to define your data generation schema.

```json
{
  "start": "2024-01-01",
  "end": "2024-01-12",
  "granularity": "5min",
  "dimensions": ["product:A,B,C", "region:X,Y,Z"],
  "metrics": [
    "sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)",
    "orders:LinearTrend(limit=200)"
  ],
  "anomalies": [
    "sales:PointAnomaly(probability=0.01,magnitude=5)+MissingData(probability=0.05)"
  ],
  "seed": 42,
  "output": "data.csv"
}
```

Run with:
```bash
tsdata generate --config schema.json
```
