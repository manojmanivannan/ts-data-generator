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

### UV
You can easily run it using `uv`
```bash
uvx --python 3.11 --from ts-data-generator tsdata generate \
    --start "2019-01-01" \
    --end "2019-01-12" \
    --granularity "5min" \
    --dims "product_id:random_float:1,4" \
    --dims "const:constant:5" 
    --mets "sales:LinearTrend(limit=500)+WeekendTrend(weekend_effect=50)" 
    --mets "trend:LinearTrend(limit=10)" 
    --output "data.csv"
```

### CLI

You can also use the command line utility `tsdata` to generate the data.
```bash
~/G/ts-data-generator on  main! 🐍 (ts-data-generator) $ tsdata                  
Usage: tsdata [OPTIONS] COMMAND [ARGS]...

  CLI tool for generating time series data.

Options:
  --help  Show this message and exit.

Commands:
  dimensions  List all available dimension functions in ts_data_generator.utils.functions.
  generate    Generate time series data and save it to a CSV file.
  metrics     List all available metric trends in ts_data_generator.utils.trends.
~/G/ts-data-generator on  main! 🐍 (ts-data-generator) $ 
```

```bash
~/G/ts-data-generator on  main! 🐍 (ts-data-generator) $ tsdata dimensions       
Available dimension functions are:
- auto_generate_name(category: str) -> str
        Example: name:auto_generate_name:mycat
- constant(value: Union[int, str, float, list])
        Example: name:constant:10
- ordered_choice(iterable)
        Example: name:ordered_choice:A,B,C
- random_choice(iterable: Iterable[~T]) -> Generator[~T, NoneType, NoneType]
        Example: name:random_choice:A,B,C
- random_float(start: float, end: float)
        Example: name:random_float:0.0,1.0
- random_int(start: int, end: int) -> Generator[int, NoneType, NoneType]
        Example: name:random_int:1,100
~/G/ts-data-generator on  main! 🐍 (ts-data-generator) $ 
```

```bash
~/G/ts-data-generator on  main! 🐍 (ts-data-generator) $ tsdata metrics   
Available metric trends & parameters are:
- LinearTrend(name: str = 'default', offset: float = 0.0, noise_level: float = 0.0, limit: float = 2.0)
        Example: sales:LinearTrend(offset=0,noise_level=1,limit=10)
- SinusoidalTrend(name: str = 'default', amplitude: float = 1, freq: float = 1, phase: float = 0, noise_level: float = 0)
        Example: sales:SinusoidalTrend(amplitude=1,freq=24,phase=0,noise_level=0)
- StockTrend(name: str = 'default', amplitude: float = 15.0, direction: Literal['up', 'down'] = 'up', noise_level: float = 0.0)
        Example: sales:StockTrend(amplitude=15.0,direction='up',noise_level=0.0)
- WeekendTrend(name: str = 'default', weekend_effect: float = 1.0, direction: Literal['up', 'down'] = 'up', noise_level: float = 0.0, limit: float = 10.0)
        Example: sales:WeekendTrend(weekend_effect=10,direction='up',noise_level=0.5,limit=10)
~/G/ts-data-generator on  main! 🐍 (ts-data-generator) $ 
```

```bash
~/G/ts-data-generator on  main! 🐍 (ts-data-generator) $ tsdata generate
Usage: tsdata generate [OPTIONS]

  Generate time series data and save it to a CSV file.

Options:
  --start TEXT                    Start datetime 'YYYY-MM-DD'
  --end TEXT                      End datetime 'YYYY-MM-DD'
  --granularity [s|min|5min|h|D|W|ME|Y]
                                  Granularity of the time series data
  --dims TEXT                     + separated list of dimensions definition of format 'name:function:values'
  --mets TEXT                     + separated list of metrics definition trends of format 'name:trend(*params)'
  --output TEXT                   Output file name
  --help                          Show this message and exit.
~/G/ts-data-generator on  main! 🐍 (ts-data-generator) $ 
  ```
  
For example you can call this cli tool like below to generate data
```bash
tsdata generate \
  --start "2019-01-01" \
  --end "2019-01-12" \
  --granularity "5min" \
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
