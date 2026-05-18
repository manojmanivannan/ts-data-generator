---
permalink: /trends
layout: default
title: Trend Functions
parent: Core Concepts
nav_order: 2
---

# Trend Functions

Trends are the atomic units of metrics. You create a metric by **composing** (adding) multiple trends together.

## Available Trends

### `SinusoidalTrend`
Perfect for modeling seasonality (daily, weekly, yearly).

- `amplitude`: The peak deviation from the mean.
- `freq`: Number of steps per full cycle. If your granularity is `h`, `freq=24` represents a daily cycle.
- `noise_level`: Std Dev of Gaussian noise added to every point.

### `LinearTrend`
Models growth, decay, or a constant baseline.

- `limit`: The target value at the end of the time range.
- `offset`: The starting value at the beginning.

### `ARNoiseTrend`
Autoregressive noise creates "sticky" randomness where the current value depends on previous values. This is much more realistic than pure Gaussian white noise.

- `decay`: How fast the influence of past values fades.
- `order`: How many past steps to consider.

### `MarkovTrend`
Simulates a process that jumps between discrete states (e.g., "Normal", "Warning", "Error").

- `values`: The numeric value associated with each state.
- `stickiness`: How likely the process is to stay in its current state vs. jumping.

---

## Composition Example

You can combine these to create highly realistic signals:

```python
# A growing sine wave with AR noise
trends = {
    LinearTrend(offset=10, limit=100),
    SinusoidalTrend(amplitude=10, freq=24),
    ARNoiseTrend(decay=0.9, noise_std=2)
}
dg.add_metric("usage", trends)
```

In the CLI:
```bash
--mets "usage:LinearTrend(offset=10,limit=100)+SinusoidalTrend(amplitude=10,freq=24)"
```
