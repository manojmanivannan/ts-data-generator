---
permalink: /imputer
layout: default
title: Schema Imputing
parent: Advanced Features
nav_order: 1
---

# Schema Imputing

One of the most powerful utilities in `ts-data-generator` is the **Schema Imputer** (implemented via `SchemaConverter`). It allows you to "reverse-engineer" a generation configuration directly from an existing historical CSV file. 

By analyzing your dataset, it automatically detects data types, maps column structures, identifies dominant periodic cycles using Fast Fourier Transforms (FFT), and approximates baseline trends using Scipy's curve fitting.

---

## 📐 How it Works under the Hood

The `SchemaConverter` executes a three-stage mathematical pipeline to extract trends:

### 1. Dtype Inference
It reads the source CSV file and maps columns to their corresponding Pandas types (e.g. `object` columns are flagged as categorical dimensions, while `float64` and `int64` are flagged as numeric metrics).

### 2. Frequency Detection via FFT
To identify cyclic seasonality (like daily, weekly, or seasonal oscillations), it:
*   Demeans the numeric column values to remove the constant bias: $y_{demeaned} = y - \bar{y}$.
*   Performs a **Fast Fourier Transform (FFT)** on the demeaned array to compute the frequency spectrum:
    \(Y(f) = \text{FFT}(y_{demeaned})\)
*   Computes absolute magnitudes and extracts the top $N$ (configured by `top_freq`) dominant frequencies with the largest spectral power. These act as initial guesses for the wave parameters.

### 3. Non-Linear Least Squares Curve Fitting
Using the top FFT frequencies as starting bounds, it uses `scipy.optimize.curve_fit` to perform a non-linear least squares fit on the data using a sum-of-sines function plus a linear slope component:
\(\hat{y}(t) = (\text{slope} \cdot t + \text{intercept}) + \sum_{i=1}^{N} A_i \sin(\omega_i t + \phi_i)\)
It solves for:
*   Linear slope and intercept coefficients.
*   Sinusoidal amplitudes ($A_i$), angular frequencies ($\omega_i$), and phase offsets ($\phi_i$).

---

## 🐍 Step-by-Step Reconstruction Guide

Here is a complete, runnable script showing how to read a historical CSV, analyze its schema and trends, reconstruct the fitted model, and plot the original vs. synthetic clone side-by-side.

### 1. Make Sure Optional Dependencies are Installed:
```bash
pip install scipy matplotlib
```

### 2. Create the Python Script:

```python
import os
import pandas as pd
import numpy as np
from ts_data_generator.schema.converter import SchemaConverter

# --- Step A: Generate a Dummy CSV File to Simulate Real Historical Data ---
dummy_csv_path = "historical_device_log.csv"
timestamps = pd.date_range("2024-01-01", "2024-01-07", freq="h")
x = np.arange(len(timestamps))

# Core mathematical signal: linear growth + strong daily cycle + random noise
clean_linear = 0.05 * x + 15.0
clean_seasonal = 8.0 * np.sin(2 * np.pi * (1/24.0) * x)
noise = np.random.normal(0, 1.0, len(timestamps))
sensor_readings = clean_linear + clean_seasonal + noise

# Save dummy data
df_historical = pd.DataFrame(
    {"temperature": sensor_readings, "device_state": "active"}, 
    index=timestamps
)
df_historical.index.name = "timestamp"
df_historical.to_csv(dummy_csv_path)
print(f"Created dummy historical file: {dummy_csv_path}\n")


# --- Step B: Initialize the Schema Converter ---
# Load our newly created historical file
converter = SchemaConverter(dummy_csv_path, index_col="timestamp")


# --- Step C: Impute Column Dtypes ---
schema = converter.impute_schema()
print("--- Imputed Column Types ---")
for col, dtype in schema.items():
    print(f"  Column: '{col}' -> Type: {dtype}")
print()


# --- Step D: Analyze Trends in Numeric Columns ---
# top_freq=1 fits a single dominant sine wave + linear slope
trends = converter.analyze_numeric_trends(columns=["temperature"], top_freq=1)

print("--- Extracted Mathematical Trend Parameters ---")
temp_trend = trends["temperature"]

print("Linear Components:")
print(f"  Slope: {temp_trend['linear']['slope']:.4f}")
print(f"  Intercept: {temp_trend['linear']['intercept']:.4f}")

print("\nSinusoidal Components (Top Frequencies):")
for idx, sine in enumerate(temp_trend["sinusoidal"]):
    print(f"  Wave {idx+1}:")
    print(f"    Magnitude (Amplitude): {sine['magnitude']:.4f}")
    print(f"    Angular Frequency (omega): {sine['angular_frequency']:.4f}")
    print(f"    Phase Offset: {sine['phase_offset']:.4f}")
print()


# --- Step E: Reconstruct the Synthetic Trend Column ---
# This adds a new 'temperature_constructed' column to the converter's dataframe
converter.construct_trend_column("temperature", temp_trend)

# Display the comparison of original vs reconstructed values
comparison_df = converter.data[["temperature", "temperature_constructed"]]
print("--- Reconstructed Comparison Header ---")
print(comparison_df.head(10))


# --- Step F: Clean Up Temporary File ---
if os.path.exists(dummy_csv_path):
    os.remove(dummy_csv_path)
```

---

## ⚠️ Limitations

While the Imputer is highly effective, keep the following constraints in mind:

*   **Stationarity & Outliers**: High amounts of random noise or severe, long-lasting anomalies (like concept drifts or dead-sensor lines) in the historical file can bias the curve fitter and result in inaccurate baseline approximations. It is often best to run basic cleanups/smoothing before importing.
*   **Highly Irregular Seasonality**: The FFT and curve fitter look for clear periodic components. Very irregular temporal behaviors or highly volatile shifts that do not follow repeating cyclic periods are difficult to fit.
*   **Sample Frequencies**: Ensure your historical data is evenly sampled and indexed. Unevenly spaced intervals can break standard FFT calculations.
