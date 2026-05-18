---
permalink: /imputer
layout: default
title: Schema Imputing
parent: Advanced Features
nav_order: 1
---

# Schema Imputing

The `SchemaConverter` allows you to take an existing CSV file and "impute" the parameters needed to recreate it. This is extremely useful for generating "more data like this" while maintaining the same statistical properties.

## How it works

1. **Temporal Analysis**: It detects the granularity and time range.
2. **Dimension Profiling**: It identifies categorical columns and their distributions.
3. **Trend Fitting**: It uses FFT (Fast Fourier Transform) and linear regression to estimate `SinusoidalTrend` and `LinearTrend` parameters.

## Usage

```python
from ts_data_generator.schema.converter import SchemaConverter

# Load existing data
converter = SchemaConverter("real_world_data.csv", index_col="timestamp")

# Analyze trends for a specific column
# top_freq=2 means find the 2 most dominant seasonal patterns
trends = converter.analyze_numeric_trends(columns=["sales"], top_freq=2)

# trends["sales"] now contains a list of Trend objects!
print(trends["sales"])
```

---

## Limitations

- The imputer currently focuses on dominant frequencies and linear trends.
- It does not automatically detect Markov transitions or complex ARNoise parameters yet.
- Requires `scipy` (`pip install "ts-data-generator[imputer]"`).
