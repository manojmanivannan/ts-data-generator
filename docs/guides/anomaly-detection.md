---
permalink: /guides/anomaly-detection
layout: default
title: Anomaly Detection Benchmarking
parent: Guides & Tutorials
nav_order: 2
---

# Anomaly Detection Benchmarking

Generate labeled datasets to evaluate your anomaly detection models.

## The Strategy

To test a model, you need:
1. **Clean Baseline**: To train or calibrate your model.
2. **Contaminated Data**: With known, labeled anomalies.

## Generating Labeled Data

By using deterministic seeds, you can generate the baseline and the contaminated data separately, or use the `DataGen` object to inspect where anomalies were placed.

### Example: Point Anomalies in Sensor Data

```python
from ts_data_generator import DataGen
from ts_data_generator.utils.trends import ARNoiseTrend
from ts_data_generator.anomalies import PointAnomaly

# 1. Generate Baseline
dg_clean = DataGen(seed=42)
dg_clean.add_metric("sensor", {ARNoiseTrend(decay=0.9, noise_std=1)})
# ... set dates ...
df_clean = dg_clean.data

# 2. Generate with Anomalies (Same Seed!)
dg_faulty = DataGen(seed=42)
dg_faulty.add_metric("sensor", 
    {ARNoiseTrend(decay=0.9, noise_std=1)},
    anomalies=[PointAnomaly(probability=0.05, magnitude=10)]
)
df_faulty = dg_faulty.data

# 3. Create Labels
# Points where the two DataFrames differ are our anomalies
df_faulty['is_anomaly'] = (df_clean['sensor'] != df_faulty['sensor']).astype(int)
```

## Tips for Better Benchmarking

- **Vary Magnitude**: Test if your model catches subtle anomalies (magnitude=2) vs obvious ones (magnitude=20).
- **Vary Frequency**: Test "swamping" (too many anomalies) and "masking".
- **Concept Drift**: Use `ConceptDrift` to test if your model can adapt to new normals without flagging them as permanent anomalies.
