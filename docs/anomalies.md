---
permalink: /anomalies
layout: default
title: Anomaly Injection
parent: Core Concepts
nav_order: 3
---

# Anomaly Injection

Anomalies are perturbations applied to metrics **after** the base trends have been calculated. They allow you to simulate outliers, failures, and shifts in your data.

## Available Anomaly Types

### `PointAnomaly`
Isolated spikes or drops in the data.

- `probability`: The chance (0.0 to 1.0) of an anomaly occurring at any given timestamp.
- `mode`: 
    - `"additive"`: Adds the magnitude to the existing value.
    - `"replacement"`: Overwrites the value with the magnitude.
- `magnitude`: A fixed number or a tuple `(min, max)` for a random range.

**Example (CLI):** `"sales:PointAnomaly(probability=0.01,magnitude=(50,100))"`

### `MissingData`
Simulates sensor failures or data loss by injecting `NaN` values.

- `mode`:
    - `"random"`: Independent probability for each point.
    - `"burst"`: Injects gaps in contiguous blocks.
    - `"patterned"`: (API only) Uses a schedule function to determine gaps.
- `probability`: Probability for `"random"` mode.
- `burst_probability`: Probability of a burst starting.
- `min_length` / `max_length`: Duration of gaps in `"burst"` mode.

**Example (CLI):** `"temp:MissingData(mode=burst,burst_probability=0.005,min_length=10)"`

### `ConceptDrift`
Simulates a gradual shift in the data distribution over time (e.g., a baseline shift after a firmware update).

Drift is defined in **segments** using `DriftSegment`:
- `start_timestamp`: When the drift begins.
- `transition_window`: Duration (in seconds) to gradually shift from the old distribution to the new one.
- `target_mean`: The new mean value.
- `target_std`: The new standard deviation.
- `hold_duration`: How long to stay in the new regime.
- `restore`: If `true`, it transitions back to the original baseline after the hold.

**Example (CLI):**
```bash
# Drift starting at 6 AM, transitioning over 30 mins to a mean of 50, holding for 2 hours, then restoring.
--anomalies "load:ConceptDrift(start_timestamp=2024-01-01T06:00:00,transition_window=1800,target_mean=50,hold_duration=7200,restore=true)"
```

---

## Stacking Anomalies

You can apply multiple anomalies to the same metric. They are processed in the order they are defined.

```bash
# A metric with both spikes and missing data gaps
--anomalies "sensor_v:PointAnomaly(prob=0.01,mag=10)+MissingData(mode=random,prob=0.02)"
```

## Python API Usage

Anomalies are passed as a list to the `add_metric` method.

```python
from ts_data_generator.anomalies import PointAnomaly, MissingData, ConceptDrift, DriftSegment

# Define anomalies
anom_list = [
    PointAnomaly(probability=0.001, magnitude=500),
    MissingData(mode="burst", burst_probability=0.01)
]

# Apply to metric
dg.add_metric("io_wait", {LinearTrend(limit=10)}, anomalies=anom_list)

# Concept Drift Example
drift = ConceptDrift(segments=[
    DriftSegment(
        start_timestamp="2024-01-05T12:00:00",
        target_mean=100,
        transition_window=3600
    )
])
dg.add_metric("throughput", {SinusoidalTrend(amplitude=10)}, anomalies=[drift])
```
