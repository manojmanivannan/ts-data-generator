---
layout: default
title: Trend Functions
---

# Trend Functions

Metrics are built by composing one or more trend functions.

## Available Trends

### `SinusoidalTrend`
Generates a sine wave pattern. Useful for seasonality.
- `amplitude`: Height of the wave.
- `freq`: Frequency (steps per cycle).
- `phase`: Starting phase.
- `noise_level`: Standard deviation of Gaussian noise.

### `LinearTrend`
A straight line ramp.
- `limit`: The value at the end of the generation.
- `offset`: Starting value.
- `noise_level`: Standard deviation of Gaussian noise.

### `WeekendTrend`
Injects spikes or drops on Saturdays and Sundays.
- `weekend_effect`: Magnitude of the effect.
- `direction`: "positive" or "negative".
- `limit`: Base value.

### `HolidayTrend`
Ramps values up or down around public holidays.
- `country`: ISO country code (e.g., "US", "GB").
- `effect`: Magnitude of the holiday effect.
- `pre_window`: Number of days before the holiday to start the effect.
- `post_window`: Number of days after the holiday to end the effect.

### `ARNoiseTrend`
Autoregressive noise (AR(p) model).
- `coefficients`: List of AR coefficients.
- `decay`: Alternative to coefficients, a single decay value.
- `order`: AR order.
- `noise_std`: Standard deviation of the innovation noise.

### `MarkovTrend`
A discrete-state Markov chain.
- `states`: Number of states.
- `values`: List of values for each state.
- `stickiness`: Probability of staying in the same state.
- `transition_matrix`: Full transition matrix (optional).

### `StockTrend`
Simulates stock-like movement using random walk and multi-scale sine waves.
