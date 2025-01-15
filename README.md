<!-- html title in the middle -->
<p style="text-align: center;">
    <h1 align="center">Synthetic Time Series Data Generator</h1>
    <h3 align="center">A Python library for generating synthetic time series data</h3>
</p>
<p align="center">
<img src="notebooks/image.png" alt="MarineGEO circle logo" style="height: 1000px; width:800px;"/>
</p>


<!-- insert image from notebooks directory -->



## Installation

### Repo
After cloning this repo and creating a virtual environment, run the following command:
```bash
pip install --editable .
```
### PyPi
Coming soon


## Usage

```python
d = DataGen()
d.start_datetime = "2019-01-01"
d.end_datetime = "2019-01-03"
d.granularity = Granularity.FIVE_MIN
d.add_dimension("product", random_choice(["A", "B", "C", "D"]))

metric1_trend = SinusoidalTrend(name="sine", amplitude=10, freq=24, phase=0, noise_level=10)

d.add_metric(name="temperature", trends=[metric1_trend])

metric2_trend = SinusoidalTrend(name="sine", amplitude=1, freq=12, phase=0, noise_level=2)
metric3_trend = LinearTrend(name="linear", limit=100, offset=10, noise_level=1)

d.add_metric(name="humidity", trends=[metric2_trend,metric3_trend])
d.generate_data()
df = d.data

# Use utility functions
processed_df = some_function(df)
```

#### Release method
1. `git tag <x.x.x>`
2. `git push origin <x.x.x>`