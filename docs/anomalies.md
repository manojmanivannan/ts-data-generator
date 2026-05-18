---
layout: default
title: Anomaly Injection
---

# Anomaly Injection

Anomalies allow you to test the robustness of your models by injecting realistic irregularities.

## Anomaly Types

### `PointAnomaly`
Isolated spikes or drops in metric values.
- `probability`: Chance of an anomaly at any given step.
- `magnitude`: Value to add or replace with. Can be a scalar or a `(min, max)` tuple.
- `mode`: `"additive"` (adds to baseline) or `"replacement"` (overwrites baseline).

### `MissingData`
Simulates gaps in your data (NaN values).
- `mode`: `"random"`, `"burst"`, or `"patterned"`.
- `probability`: Chance of a gap starting.
- `min_length`: Minimum gap length (for burst mode).
- `max_length`: Maximum gap length (for burst mode).
- `schedule`: A callable or string expression for patterned mode (e.g., `weekday == 6` for Sundays).

### `ConceptDrift`
Gradual shifts in the underlying distribution.
- `segments`: A list of `DriftSegment` objects.

#### `DriftSegment`
- `start_timestamp`: When the drift starts.
- `transition_window`: Duration (in seconds) to transition from baseline to target.
- `target_mean`: Mean of the new distribution.
- `target_std`: Standard deviation of the new distribution.
- `hold_duration`: How long to stay at the target distribution.
- `restore`: Whether to transition back to baseline after the hold duration.
