---
permalink: /guides/anomaly-detection
layout: default
title: Anomaly Detection Benchmarking
parent: Guides & Tutorials
nav_order: 2
---

# Anomaly Detection Benchmarking

To build, train, and evaluate machine learning models for anomaly detection (such as Isolation Forests, Autoencoders, or LSTM networks), you need two distinct datasets:
1.  **Clean Baseline Training Data**: Completely free of anomalies, used to train the model to learn the "normal" operational boundaries of the system.
2.  **Contaminated Test Data with Ground-Truth Labels**: Contains both normal patterns and realistic stochastically-injected anomalies, with a perfect binary classification target column (`is_anomaly: 0 or 1`) to compute evaluation metrics (Precision, Recall, F1-Score, ROC-AUC).

By using **deterministic seeding**, `ts-data-generator` makes creating these paired datasets incredibly simple.

---

## 📐 The Paired-Generation Strategy

To generate a perfectly labeled dataset, we exploit the library's PCG64 seeding engine:
1.  We generate a **baseline dataframe** using a specific `seed` **without** adding any anomalies. This represents the absolute, clean ground-truth normal behavior.
2.  We generate a **contaminated dataframe** using the **exact same seed** and trend parameters, but we attach a list of **anomalies**.
3.  Because the seeds are identical, the underlying base trend, noise, and dimensional broadcasting are completely identical in both runs.
4.  We compute the perfect binary label `is_anomaly` by simply comparing where the clean dataframe differs from the contaminated dataframe:
    $$\text{is\_anomaly}_t = \begin{cases} 1 & \text{if } y_{\text{contaminated}, t} \neq y_{\text{baseline}, t} \text{ or } y_{\text{contaminated}, t} \text{ is NaN} \\ 0 & \text{otherwise} \end{cases}$$

---

## 🐍 Complete Python API Machine Learning Pipeline

Here is a complete, runnable script that generates a clean training dataset and a stochastically-contaminated test dataset with perfect classification labels, ready for consumption by models in Scikit-Learn or PyTorch.

```python
import pandas as pd
import numpy as np
from ts_data_generator import DataGen
from ts_data_generator.utils.trends import SinusoidalTrend, ARNoiseTrend
from ts_data_generator.anomalies import PointAnomaly, MissingData

# ==========================================
# 1. SETUP SHARED SIMULATION CONFIGURATION
# ==========================================
SEED = 42
START_DATE = "2024-01-01"
END_DATE = "2024-01-15"
GRANULARITY = "h" # Hourly readings

# A typical industrial temperature sensor: daily cycle + sticky AR(1) fluctuations
sensor_trends = {
    SinusoidalTrend(amplitude=12.0, freq=1.0), # Daily thermal cycle
    ARNoiseTrend(decay=0.85, noise_std=1.5)     # Atmospheric drift volatility
}

# ==========================================
# 2. GENERATE CLEAN BASELINE TRAINING DATA
# ==========================================
print("Generating clean baseline training dataset...")
dg_train = DataGen(seed=SEED)
dg_train.start_datetime = START_DATE
dg_train.end_datetime = END_DATE
dg_train.to_granularity(GRANULARITY)

# Add metric without any anomalies list
dg_train.add_metric(
    name="sensor_temperature",
    trends=sensor_trends
)
df_train = dg_train.data.copy()

print(f"Training Data Generated: {df_train.shape[0]} rows. Anomalies present: 0\n")


# ==========================================
# 3. GENERATE CONTAMINATED TEST DATA (SAME SEED!)
# ==========================================
print("Generating contaminated test dataset...")

# Add stochastically triggered anomalies
point_spikes = PointAnomaly(probability=0.015, mode="additive", magnitude=(20.0, 40.0))
data_dropouts = MissingData(mode="burst", burst_probability=0.01, min_length=2, max_length=4)

dg_test = DataGen(seed=SEED)
dg_test.start_datetime = START_DATE
dg_test.end_datetime = END_DATE
dg_test.to_granularity(GRANULARITY)

# Add metric with the SAME trends, but WITH the anomalies list
dg_test.add_metric(
    name="sensor_temperature",
    trends=sensor_trends,
    anomalies=[point_spikes, data_dropouts]
)
df_test = dg_test.data.copy()


# ==========================================
# 4. COMPUTE EXACT GROUND-TRUTH BINARY LABELS
# ==========================================
# An anomaly exists wherever:
#   A) The clean value does not match the contaminated value, OR
#   B) The contaminated value has been dropped out to NaN (sensor failure)
is_different = df_train["sensor_temperature"] != df_test["sensor_temperature"]
is_missing = df_test["sensor_temperature"].isna()

# Combine both boolean checks and cast to integer (0 or 1)
df_test["is_anomaly"] = (is_different | is_missing).astype(int)

# Fill NaNs with a fallback representation if needed, or leave for model imputation
# For visualization, we keep NaNs to show sensor dropout locations
print("--- Contaminated Test Data Samples ---")
print(df_test.head(15))


# ==========================================
# 5. VERIFY METRICS & ANOMALY DISTRIBUTION
# ==========================================
total_points = len(df_test)
anomaly_points = df_test["is_anomaly"].sum()
anomaly_rate = (anomaly_points / total_points) * 100

print(f"\n--- Benchmark Dataset Verification ---")
print(f"Total Timestamps: {total_points}")
print(f"Anomaly Timestamps: {anomaly_points} ({anomaly_rate:.2f}% contamination rate)")
print(f"Spike (Non-NaN) Anomalies: {np.sum(is_different & ~is_missing)}")
print(f"Sensor Dropout (NaN) Anomalies: {np.sum(is_missing)}")

# Ready for ML pipelines:
# X_train = df_train["sensor_temperature"].values
# X_test = df_test[["sensor_temperature"]].values
# y_test = df_test["is_anomaly"].values
```

---

## 💡 Practical Benchmarking Tips

*   **Vary Anomaly Magnitude**: Test if your models are sensitive enough to catch subtle deviations (e.g. spike magnitude of $+5.0$) versus massive, obvious spikes (magnitude of $+50.0$).
*   **Evaluate False Positive Rates**: Feed your trained model the clean `df_train` dataset to verify its baseline **False Positive Rate (FPR)**. A model that flags $0\%$ anomalies on clean data is highly desirable.
*   **Handle Missing Values**: Many ML models (like Support Vector Machines or standard MLP Neural Networks) cannot digest raw `NaN` values. Before feeding `df_test` to such models, you should record the `is_anomaly` label, then impute or interpolate the NaNs:
    ```python
    # Interpolate missing values in the test stream before training/inference
    df_test["imputed_temperature"] = df_test["sensor_temperature"].interpolate(method="linear")
    ```
