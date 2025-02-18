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
1. To check out constructing for time series data, check the sample notebook [here](https://github.com/manojmanivannan/ts-data-generator/blob/main/notebooks/sample.ipynb)
2. To extract the trends from an existing data, check this sample notebook [here](https://github.com/manojmanivannan/ts-data-generator/blob/main/notebooks/imputer.ipynb)

### CLI

You can also use the command line utility `tsdata` to generate the data.
```bash
(venv) ~/ts-data-generator   cli $ tsdata generate --help
Usage: tsdata generate [OPTIONS]

  Generate time series data and save it to a CSV file.

Options:
  --start TEXT                    Start datetime 'YYYY-MM-DD'  [required]
  --end TEXT                      End datetime 'YYYY-MM-DD'  [required]
  --granularity [FIVE_MIN|HOURLY|DAILY]
                                  Granularity of the time series data  [required]
  --dims TEXT                     + separated list of dimensions definition of format 'name:function:values'  [required]
  --mets TEXT                     + separated list of metrics definition trends of format 'name:trend(*params)'  [required]
  --output TEXT                   Output file name  [required]
  --help                          Show this message and exit.
  ```
For example you can call this cli tool like below to generate data
```bash
tsdata generate \
  --start "2019-01-01" \
  --end "2019-01-12" \
  --granularity "FIVE_MIN" \
  --dims "product:random_choice:A,B,C,D" \
  --dims "product_id:random_float:1,4" \
  --dims "const:constant:5" \
  --mets "sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)" \
  --mets "trend:LinearTrend(limit=10)" \
  --output "data.csv"
```

#### Release method
1. `git tag <x.x.x>`
2. `git push origin <x.x.x>`

<!-- [tutorial]: /notebooks/test.gif -->