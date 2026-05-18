---
permalink: /anomalies
layout: default
title: Anomaly Injection
parent: Core Concepts
nav_order: 3
---

# Anomaly Injection

Anomalies are applied to metrics *after* the trends have been calculated. They can be stacked and are processed in a deterministic order.

## Point Anomalies

Isolated spikes or drops.

- **Modes**:
    - `additive`: Adds the magnitude to the current value.
    - `replacement`: Overwrites the current value with the magnitude.
- **Magnitude**: Can be a fixed number or a tuple `(min, max)` for random range.

## Missing Data (Gaps)

Simulates sensor failure, network outages, or scheduled maintenance.

- **Modes**:
    - `random`: Every point has an independent probability of being NaN.
    - `burst`: Gaps occur in chunks. When a gap starts, it lasts for a random duration between `min_length` and `max_length`.
    - `patterned`: Gaps occur based on a schedule (e.g., "every Sunday" or "between 2 AM and 4 AM").

## Concept Drift

Simulates a fundamental change in the data distribution (e.g., a new baseline after a system upgrade).

- **DriftSegment**:
    - `transition_window`: How many seconds it takes to move from the old mean/std to the new one (linear interpolation).
    - `restore`: If true, the signal will transition back to the original baseline after `hold_duration`.

---

## Stacking Anomalies

You can apply multiple anomaly types to the same metric.

```bash
--anomalies "temp:PointAnomaly(prob=0.01,mag=50)+MissingData(mode=burst,prob=0.005)"
```

> **Note**: Anomalies are applied in order. If `MissingData` makes a point NaN, a subsequent `PointAnomaly` will *not* overwrite it (it respects the "missingness").
