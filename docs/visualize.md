---
permalink: /visualize
layout: default
title: Visualization
nav_order: 4
---

# Visualization

`ts-data-generator` provides clean built-in plotting utilities to quickly inspect and verify your generated signals. Additionally, since the engine outputs standard **Pandas DataFrames**, you can seamlessly plug the output into popular visualization libraries like Seaborn, Matplotlib, or Plotly for advanced reporting.

---

## 📈 Built-in Native Plotting

The `DataGen` class contains a `.plot()` method that leverages `matplotlib` to render quick line charts of your generated numeric metrics.

```python
from ts_data_generator import DataGen
from ts_data_generator.utils.trends import SinusoidalTrend, LinearTrend

dg = DataGen(seed=42)
dg.start_datetime = "2024-01-01"
dg.end_datetime = "2024-01-04"
dg.to_granularity("h")

# Composing a metric
dg.add_metric("temperature", {LinearTrend(offset=15.0, slope=2), SinusoidalTrend(amplitude=5, freq=1)})
dg.add_metric("humidity", {SinusoidalTrend(amplitude=15, freq=1)})

df = dg.data

# 1. Quick Native Plot (Plots all numeric columns)
dg.plot()
```

### Filtering Columns
You can easily control which metrics are rendered using the `include` or `exclude` parameters:

```python
# Renders ONLY the temperature line
dg.plot(include=["temperature"])

# Renders everything EXCEPT humidity (e.g. useful to hide high-scale metrics)
dg.plot(exclude=["humidity"])
```

---

## 🎨 Advanced Plotting with External Libraries

Because `dg.data` returns a standard Pandas DataFrame, you have total design control. Below are three copy-pasteable snippets for professional, premium quality visualizations.

### 1. Seaborn (Multi-Facet & Styling)
Seaborn is perfect for plotting metrics grouped by categorical dimensions (like regions or environments).

```python
import seaborn as sns
import matplotlib.pyplot as plt
from ts_data_generator import DataGen
from ts_data_generator.utils.functions import random_choice
from ts_data_generator.utils.trends import SinusoidalTrend

# Setup multi-variate generation
dg = DataGen(seed=42)
dg.start_datetime = "2024-01-01"
dg.end_datetime = "2024-01-03"
dg.to_granularity("h")

dg.add_dimension("region", random_choice(["North", "South"]))
dg.add_metric("temperature", {SinusoidalTrend(amplitude=10, freq=1)})

df = dg.data.reset_index() # Seaborn works best with long-format columns

# Styling parameters
sns.set_theme(style="whitegrid")
plt.figure(figsize=(12, 6))

# Line plot grouped by region
sns.lineplot(
    data=df, 
    x="index", 
    y="temperature", 
    hue="region", 
    linewidth=2.5,
    palette="muted"
)

plt.title("Temperature Seasonal Variations by Region", fontsize=14, fontweight="bold", pad=15)
plt.xlabel("Timestamp", fontsize=12)
plt.ylabel("Degrees Celsius", fontsize=12)
plt.tight_layout()
plt.show()
```

---

### 2. Plotly (Interactive & Dynamic Zoom)
Plotly allows you to hover over spikes, zoom in on stochastically placed anomalies, and export interactive HTML dashboards.

```python
import plotly.express as px
from ts_data_generator import DataGen
from ts_data_generator.utils.trends import StockTrend

# Setup a stock price simulation
dg = DataGen(seed=777)
dg.start_datetime = "2024-01-01"
dg.end_datetime = "2024-01-07"
dg.to_granularity("5min")
dg.add_metric("asset_price", {StockTrend(amplitude=150.0, noise_level=0.1)})

df = dg.data

# Render beautiful, interactive Plotly line chart
fig = px.line(
    df, 
    y="asset_price", 
    title="Simulated Asset Price Walk (5-Min Granularity)",
    labels={"index": "Timestamp", "asset_price": "Price (USD)"},
    template="plotly_dark" # Premium sleek dark mode
)

# Customize layout lines
fig.update_xaxes(rangeslider_visible=True) # Adds a timeline range slider
fig.update_traces(line_color="#00D2FF", line_width=1.5)
fig.show()
```

---

### 3. Correlation Heatmap
If you have generated many metric columns, plotting a correlation matrix heatmap helps verify how your metrics behave relative to each other.

```python
import seaborn as sns
import matplotlib.pyplot as plt

df = dg.data

plt.figure(figsize=(8, 6))
sns.heatmap(
    df.corr(), 
    annot=True, 
    cmap="coolwarm", 
    fmt=".2f", 
    linewidths=.5,
    square=True
)
plt.title("Metrics Correlation Heatmap", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.show()
```
