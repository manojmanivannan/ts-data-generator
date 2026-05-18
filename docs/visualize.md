---
permalink: /visualize
layout: default
title: Visualization
nav_order: 4
---

# Visualization

`ts-data-generator` provides built-in utilities to quickly visualize your generated data, helping you verify that your trends and anomalies look as expected.

## Built-in Plotting

The `DataGen` class has a `plot()` method that leverages `matplotlib` to render your metrics.

```python
from ts_data_generator import DataGen
from ts_data_generator.utils.trends import SinusoidalTrend

dg = DataGen()
dg.start_datetime = "2024-01-01"
dg.end_datetime = "2024-01-02"
dg.to_granularity("h")

dg.add_metric("temperature", {SinusoidalTrend(amplitude=10, freq=24)})

# Generate and plot
dg.plot()
```

### Parameters

The `plot()` method accepts the following optional arguments:

- `include`: A list of column names to include in the plot.
- `exclude`: A list of column names to exclude (useful for hiding static dimensions).

```python
# Only plot specific metrics
dg.plot(include=["temperature", "humidity"])

# Exclude dimension columns
dg.plot(exclude=["region", "device_id"])
```

---

## External Libraries

Since `dg.data` returns a standard **Pandas DataFrame**, you can easily use any other Python plotting library.

### Matplotlib / Seaborn

```python
import matplotlib.pyplot as plt
import seaborn as sns

df = dg.data

plt.figure(figsize=(12, 6))
sns.lineplot(data=df, x=df.index, y="temperature", hue="region")
plt.title("Temperature by Region")
plt.show()
```

### Plotly (Interactive)

```python
import plotly.express as px

df = dg.data
fig = px.line(df, y="sales", title="Interactive Sales Chart")
fig.show()
```

---

## Visualizing in Notebooks

The library is highly compatible with Jupyter Notebooks. The `plot()` method will render inline if `%matplotlib inline` is set or if you are using a modern IDE like VS Code or PyCharm.

For a full walkthrough, check out the [Visualization Notebook](https://github.com/manojmanivannan/ts-data-generator/blob/main/notebooks/visualize.ipynb).
