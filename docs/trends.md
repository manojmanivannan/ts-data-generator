---
permalink: /trends
layout: default
title: Trend Functions
parent: Core Concepts
nav_order: 2
---

# Trend Functions

Trends are the atomic building blocks of metrics. A metric is created by **composing** (summing) one or more trends. This additive model allows you to build complex, realistic signals from simple components.

## Available Trend Types

### `SinusoidalTrend`
Perfect for modeling periodic patterns like daily, weekly, or seasonal cycles.

- `amplitude`: The peak deviation from the baseline.
- `freq`: The period of oscillation in days (e.g., `1` for daily, `7` for weekly).
- `phase`: Phase offset in hours.
- `noise_level`: Standard deviation of Gaussian noise added to each point.

### `LinearTrend`
Models steady growth, decay, or a constant baseline.

- `offset`: The starting value at the beginning of the time range.
- `limit`: Controls the slope; essentially the target value shift over a "standard" interval.
- `noise_level`: Standard deviation of Gaussian noise.

### `ARNoiseTrend`
Autoregressive AR(p) noise creates "sticky" randomness where the current value depends on previous values. This is much more realistic than pure white noise.

- `coefficients`: Explicit list of AR coefficients `[phi_1, phi_2, ...]`.
- `decay`: Alternatively, provide a decay factor `(0, 1)` to auto-generate stable coefficients.
- `order`: The order `p` of the AR process (when using `decay`).
- `noise_std`: Standard deviation of the white-noise innovation.

### `MarkovTrend`
Simulates a process that jumps between discrete states (e.g., "Idle", "Busy", "Error").

- `states`: List of state names.
- `values`: Numeric values associated with each state.
- `stickiness`: Probability of staying in the current state vs. jumping.
- `transition_matrix`: Alternatively, provide a full N×N probability matrix.
- `noise_std`: Gaussian noise added to the state value.

### `WeekendTrend`
Applies a specific adjustment during weekends (Saturday and Sunday).

- `weekend_effect`: The magnitude of the adjustment.
- `direction`: `"up"` (increase) or `"down"` (decrease).
- `noise_level`: Gaussian noise added to the effect.
- `limit`: Clamps the trend value.

### `HolidayTrend`
Applies ramps and peaks around public holidays. Requires the `holidays` Python library or explicit dates.

- `country`: ISO country code (e.g., `"US"`, `"GB"`).
- `effect`: Peak magnitude on the holiday.
- `pre_window`: Number of days before the holiday to start the ramp-up.
- `post_window`: Number of days after the holiday to ramp-down.
- `direction`: `"up"` or `"down"`.

### `StockTrend`
A specialized trend that combines a random walk with multi-scale sinusoidal components to mimic financial charts.

- `amplitude`: Overall scale of the price movement.
- `direction`: General trend direction (`"up"` or `"down"`).
- `noise_level`: Volatility of the random walk.

---

## Composition and Layering

You can layer multiple trends to create sophisticated signals. For example, a retail sales metric might have a linear growth trend, a daily sinusoidal cycle, a weekend boost, and some AR noise.

### Python API Example

```python
from ts_data_generator.utils.trends import LinearTrend, SinusoidalTrend, ARNoiseTrend

# Create a complex metric by summing trends
usage_metric = {
    LinearTrend(offset=100, limit=200, name="growth"),
    SinusoidalTrend(amplitude=20, freq=1, name="daily_cycle"),
    ARNoiseTrend(decay=0.8, noise_std=5, name="volatility")
}

dg.add_metric("cpu_usage", usage_metric)
```

### CLI Example

In the CLI, use the `+` operator to compose trends for a metric.

```bash
tsdata generate --mets "revenue:LinearTrend(limit=1000)+SinusoidalTrend(amplitude=50,freq=7)+WeekendTrend(weekend_effect=200)"
```

> **Tip**: You can use the `tsdata metrics` command to see a full list of available trends and their parameters directly in your terminal.
