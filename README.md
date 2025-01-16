<!-- html title in the middle -->
<div align="center">

# Synthetic Time Series Data Generator

[![Python](https://img.shields.io/pypi/v/ts-data-generator)](https://pypi.org/project/ts-data-generator) ![CI](https://github.com/manojmanivannan/ts-data-generator/actions/workflows/ci.yaml/badge.svg)

A Python library for generating synthetic time series data

<sup>Special thanks to: [Nike-Inc](https://github.com/Nike-Inc/timeseries-generator) repo

<img src="https://github.com/manojmanivannan/ts-data-generator/raw/main/notebooks/image.png" alt="MarineGEO circle logo" style="height: 1000px; width:800px;"/>

<!-- ![Tutorial][tutorial] -->

</div>

## Installation
### PyPi (recommended)
You can install with pip directly by
```bash
pip install ts-data-generator
```

### Repo
After cloning this repo and creating a virtual environment, run the following command:
```bash
pip install --editable .
```


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

# Use data further however you want
processed_df = some_function(df)
```

#### Release method
1. `git tag <x.x.x>`
2. `git push origin <x.x.x>`

<!-- [tutorial]: /notebooks/test.gif -->