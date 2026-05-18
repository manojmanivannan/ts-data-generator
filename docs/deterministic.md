---
permalink: /deterministic
layout: default
title: Deterministic Seeds
parent: Advanced Features
nav_order: 2
---

# Deterministic Generation

One of the core design goals of this library is **reproducibility**. Given the same seed and configuration, the library will produce the exact same dataset every time, regardless of the machine or Python version.

## How it works

We avoid using the global `random` or `numpy.random` states. Instead, we use a dedicated `SeedableRNG` based on the **PCG64** algorithm. This RNG instance is:

1. Initialized with your provided seed.
2. Passed down into every Trend, Anomaly, and Dimension generator.
3. Used exclusively for all stochastic decisions.

## Usage

### CLI
```bash
tsdata generate --seed 12345 ...
```

### Python API
```python
from ts_data_generator import DataGen
dg = DataGen(seed=12345)
```

---

## Why this matters

- **Regression Testing**: Ensure your model's performance change is due to code changes, not a "lucky" dataset.
- **Collaboration**: Share a small config and a seed instead of a 1GB CSV file.
- **Debugging**: If an anomaly causes a crash, you can recreate the exact same scenario to debug.
