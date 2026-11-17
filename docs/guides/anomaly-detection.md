---
permalink: /guides/anomaly-detection
layout: default
title: Anomaly Detection Benchmarking
parent: Guides & Tutorials
nav_order: 2
---

# Anomaly Detection Benchmarking

To build, train, and evaluate machine learning models for anomaly detection (such as Isolation Forests, Autoencoders, or LSTM networks), you need two distinct pieces:
1.  **Clean Baseline Training Data**: Completely free of anomalies, used to train the model to learn the "normal" operational boundaries of the system.
2.  **Contaminated Test Data with Ground-Truth Labels**: Contains both normal patterns and realistic stochastically-injected anomalies, with a ground-truth label column (`<metric>_anomaly`) to compute evaluation metrics (Precision, Recall, F1-Score, ROC-AUC).

`ts-data-generator` builds both automatically from a **single generator**.

---

## 📐 Automatic Baselines & `<metric>_anomaly` Labels

Whenever you configure a metric with `anomalies=[...]`, `Metric.generate()` separates the clean trend sum from the post-trend anomaly interventions:
1.  **Automatic clean baseline (`dg.baselines[metric]`)**: Stores the exact anomaly-free baseline `pd.DataFrame` for each metric (populated in non-expanded mode) before anomalies are applied.
2.  **Automatic ground-truth labels (`dg.data[f"{metric}_anomaly"]`)**: Adds a boolean (`bool`) column to `dg.data` marking every timestamp where the contaminated signal deviates from the clean baseline. The check is NaN-aware (`equal_nan=False`), so `MissingData` gaps (`NaN`), `PointAnomaly` spikes/replacements, `ConceptDrift` regimes, and `PeriodicBurstAnomaly` windows are all flagged `True` automatically.
3.  **Optional separate training window**: If you want an independent training split (for example, an earlier date window), you can either train on `dg.baselines[metric]` directly or generate a separate clean `DataGenerator` over the training window while reading `dg_test.data[f"{metric}_anomaly"]` without manual diffing.

---

## 🐍 Complete Python API Machine Learning Pipeline

Here is a complete, runnable script that generates contaminated test data alongside its automatic clean baseline and ground-truth anomaly labels, ready for consumption by models in Scikit-Learn or PyTorch.

```python
import numpy as np
from ts_data_generator import (
    ARNoiseTrend,
    DataGenerator,
    MissingData,
    PointAnomaly,
    SinusoidalTrend,
)

# ==========================================
# 1. SETUP SIMULATION CONFIGURATION
# ==========================================
SEED = 42
START_DATE = "2024-01-01"
END_DATE = "2024-01-15"
GRANULARITY = "h"  # Hourly readings

# A typical industrial temperature sensor: daily cycle + sticky AR(1) fluctuations
sensor_trends = [
    SinusoidalTrend(amplitude=12.0, freq=1.0),  # Daily thermal cycle
    ARNoiseTrend(decay=0.85, noise_std=1.5),    # Atmospheric drift volatility
]

# Stochastically triggered anomalies
point_spikes = PointAnomaly(probability=0.015, mode="additive", magnitude=(20.0, 40.0))
data_dropouts = MissingData(mode="burst", burst_probability=0.01, min_length=2, max_length=4)

# ==========================================
# 2. GENERATE DATA + AUTOMATIC BASELINE & LABELS
# ==========================================
dg = DataGenerator(
    start_datetime=START_DATE,
    end_datetime=END_DATE,
    granularity=GRANULARITY,
    seed=SEED,
)
dg.add_metric(
    name="sensor_temperature",
    trends=sensor_trends,
    anomalies=[point_spikes, data_dropouts],
)

# Contaminated dataframe automatically includes `sensor_temperature_anomaly` (bool)
df_test = dg.data.copy()

# Clean anomaly-free baseline dataframe is automatically preserved in `dg.baselines`
df_train = dg.baselines["sensor_temperature"].copy()

# Optional integer 0/1 target column for ML frameworks that expect integer labels
df_test["is_anomaly"] = df_test["sensor_temperature_anomaly"].astype(int)

print(f"Baseline Training Rows: {df_train.shape[0]} (anomalies present: 0)")
print("--- Contaminated Test Data Samples ---")
print(df_test.head(15))

# ==========================================
# 3. VERIFY METRICS & ANOMALY DISTRIBUTION
# ==========================================
total_points = len(df_test)
is_anomaly = df_test["sensor_temperature_anomaly"]
is_missing = df_test["sensor_temperature"].isna()
anomaly_points = int(is_anomaly.sum())
anomaly_rate = (anomaly_points / total_points) * 100

print("\n--- Benchmark Dataset Verification ---")
print(f"Total Timestamps: {total_points}")
print(f"Anomaly Timestamps: {anomaly_points} ({anomaly_rate:.2f}% contamination rate)")
print(f"Spike (Non-NaN) Anomalies: {int(np.sum(is_anomaly & ~is_missing))}")
print(f"Sensor Dropout (NaN) Anomalies: {int(np.sum(is_missing))}")

# Ready for ML pipelines:
# X_train = df_train[["sensor_temperature"]].values
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
