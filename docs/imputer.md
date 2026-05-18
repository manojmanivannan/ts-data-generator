---
permalink: /imputer
layout: default
title: Schema Imputing
nav_order: 5
---

# Schema Imputing

The **Schema Imputer** (via `SchemaConverter`) is a powerful utility that allows you to "reverse-engineer" a generation configuration from an existing CSV file. It analyzes your data to detect data types and approximate trends.

## How it Works

The imputer uses:
1.  **Dtype Inference**: Maps CSV columns to their pandas types.
2.  **FFT (Fast Fourier Transform)**: Identifies dominant seasonal frequencies in numeric data.
3.  **Curve Fitting**: Uses `scipy.optimize` to fit linear and sinusoidal models to your metrics.

## Python API Usage

```python
from ts_data_generator.schema.converter import SchemaConverter

# Initialize with an existing CSV
converter = SchemaConverter("historical_sales.csv", index_col="timestamp")

# 1. Impute basic schema (column names and types)
schema = converter.impute_schema()
print(schema) 
# Output: {"product": "object", "revenue": "float64"}

# 2. Analyze trends in numeric columns
# top_freq=3 will look for the 3 most dominant sine waves
trends = converter.analyze_numeric_trends(columns=["revenue"], top_freq=3)

print(trends["revenue"]["linear"])      # {'slope': 0.5, 'intercept': 100}
print(trends["revenue"]["sinusoidal"])  # List of magnitude, freq, phase
```

---

## Reconstructing Trends

You can use the detected parameters to build a "constructed" version of your original signal to see how well the imputer captured the patterns.

```python
# This adds a 'revenue_constructed' column to the converter's internal dataframe
converter.construct_trend_column("revenue", trends["revenue"])

# Compare original vs constructed
converter.data[["revenue", "revenue_constructed"]].plot()
```

## Limitations

- **Complexity**: The imputer works best on signals that are clearly composed of linear and periodic components. It may struggle with highly irregular or non-stationary data.
- **Noise**: High levels of random noise can make frequency detection less accurate.
- **Anomalies**: Existing anomalies in your source CSV might be interpreted as trends. It is often better to clean the data before imputing.
