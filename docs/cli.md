---
layout: default
title: CLI Reference
permalink: /cli
nav_order: 2
---

# CLI Reference

The `tsdata` command-line interface is a powerful, zero-code tool for rapid prototyping, generating datasets, and managing simulation settings. It supports direct terminal parameters, full JSON configuration files, and environment variable overrides.

---

## 🚀 Running Without Installation

You can use [`uvx`](https://docs.astral.sh/uv/guides/tools/) to run the CLI in a disposable environment — no install required:

```bash
uvx --from ts-data-generator tsdata --help
```

> **Important:** Use `--from` (not `--with`). The PyPI package is called `ts-data-generator` while the executable is `tsdata`, so `--from` tells uvx which package provides the command. Using `--with` will produce a warning and may resolve the wrong package.

---

## 📋 Get a Sample Config File

Not sure what a valid JSON config looks like? Use `--show-sample-config` to dump a ready-to-edit config to stdout:

```bash
# Save the sample config to a file
tsdata generate --show-sample-config > my_config.json

# Edit it, then generate data from your custom config
tsdata generate --config my_config.json
```

The sample config exercises all features — dimensions, composed metrics, and anomalies — so you can delete what you don't need and tweak the rest.

---

## 💻 Commands

### 1. `tsdata generate`
The primary command for creating synthetic datasets and saving them to CSV.

#### CLI Command Arguments & Flags:

| Flag | Shorthand | Type | Description | Default / Required |
|:---|:---|:---|:---|:---|
| `--start` | | `str` | Start date/time string (ISO format: `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM:SS`) | **Required** (unless in config/preset) |
| `--end` | | `str` | End date/time string (ISO format) | **Required** (unless in config/preset) |
| `--granularity` | | `str` | Time step frequency (`s`, `min`, `5min`, `h`, `D`, `W`, `ME`, `Y`) | **Required** (unless in config/preset) |
| `--dims` | | `str` | Dimension specification. Can be repeated. | `None` |
| `--mets` | | `str` | Metric (trend composition) specification. Can be repeated. | `None` |
| `--anomalies` | | `str` | Anomaly specification keyed by metric. Can be repeated. | `None` |
| `--expand-dimensions` / `--no-expand-dimensions` | | `bool` | Expand enumerable dimensions to their Cartesian product with independent per-combination metric series. | `False` |
| `--scale-variance` | | `float` | Standard deviation for log-normal metric scaling across dimension combinations (`0.0` = disabled). | `0.0` |
| `--workers` | `-w` | `int` | Number of worker processes for parallel generation (`1` for sequential, `-1` for all CPUs). | `auto` / `1` |
| `--seed` | | `int` | Seed for PCG64 deterministic generation. | `None` |
| `--output` | | `str` | Destination path to save the generated CSV. | **Required** (unless in config/preset) |
| `--config` | | `str` | Path to a local JSON configuration file. | `None` |
| `--preset` | | `str` | Use a built-in config preset. | `None` |
| `--show-sample-config` | | flag | Print a sample JSON config to stdout and exit. | `False` |
| `--aggregate` | | `str` | Resample generated data to a coarser granularity before writing (e.g. `D`). | `None` |
| `--by` | | `str` | Comma-separated subset of dimension column names to group by when aggregating (only with `--aggregate`). | `None` |

#### Simple Shorthand CLI Example:
```bash
tsdata generate \
  --start 2024-01-01 --end 2024-01-07 --granularity D \
  --dims "region:US,EU,AP" \
  --mets "sales:LinearTrend(slope=40)+SinusoidalTrend(amplitude=10,freq=7)" \
  --output sales_data.csv
```

#### Multivariate Cartesian Product Expansion with Scaling:
```bash
tsdata generate \
  --start 2024-01-01 --end 2024-01-07 --granularity h \
  --dims "region=random_choice(US,EU),weights={US:5,EU:2}" \
  --dims "store_type=ordered_choice(online,retail)" \
  --mets "sales:LinearTrend(slope=40)+SinusoidalTrend(amplitude=10,freq=24)" \
  --expand-dimensions \
  --scale-variance 0.3 \
  --output expanded_sales.csv
```

> [!TIP]
> **Per-Dimension Expansion & Scaling Control**: When using modern dimension syntax (`name=func(...)`), you can override expansion per dimension using a trailing `,expand=true` or `,expand=false`, and specify scale multipliers using `,weights={key:val}` (e.g. `--dims "tier=random_choice(enterprise,free),weights={enterprise:10,free:1},expand=true"`).

---

### 2. `tsdata dimensions`
Lists all available dimension generator functions, their parameters, and CLI shorthand examples.

```bash
$ tsdata dimensions
```
*Expected Output:*
```
Available dimension functions:

  auto_generate_name(category: 'str', rng: 'RNGProtocol | None' = None) -> 'DimensionCarrier[str]'
    → name:auto_generate_name:mycat
  constant(value: 'int | str | float | list[int | str | float] | tuple[int | str | float, ...]') -> 'DimensionCarrier[int | str | float]'
    → name:constant:10
  ordered_choice(iterable: '_Iterable[_T]') -> 'DimensionCarrier[_T]'
    → name:ordered_choice:A,B,C
  random_choice(iterable: '_Iterable[_T]', rng: 'RNGProtocol | None' = None) -> 'DimensionCarrier[_T]'
    → name:random_choice:A,B,C
  random_float(start: 'float', end: 'float', rng: 'RNGProtocol | None' = None) -> 'DimensionCarrier[float]'
    → name:random_float:0.0,1.0
  random_int(start: 'int', end: 'int', rng: 'RNGProtocol | None' = None) -> 'DimensionCarrier[int]'
    → name:random_int:1,100
```

---

### 3. `tsdata metrics`
Lists all available metric trend functions, their exact parameters, and CLI shorthand examples. Uses the `Registry` class to reflectively discover all `Trend` subclasses in the `ts_data_generator.trends` module.

```bash
$ tsdata metrics
```
*Expected Output:*
```
Available trend functions:

  ARNoiseTrend(name: 'str | None' = None, coefficients: 'list[float] | None' = None, noise_std: 'float' = 1.0, decay: 'float | None' = None, order: 'int' = 1) -> 'None'
    → sales:ARNoiseTrend(coefficients=[0.5,-0.2],noise_std=0.5)
  HolidayTrend(name: 'str | None' = None, country: 'str' = 'US', effect: 'float' = 50.0, pre_window: 'int' = 3, post_window: 'int' = 2, direction: "Literal['up', 'down']" = 'up', dates: 'list[str] | None' = None) -> 'None'
    → sales:HolidayTrend(country='US',effect=50,pre_window=3,post_window=2,direction='up')
  LinearTrend(name: 'str | None' = None, offset: 'float' = 0.0, noise_level: 'float' = 0.0, slope: 'float' = 10.0) -> 'None'
    → sales:LinearTrend(offset=0,noise_level=1,slope=30)
  MarkovTrend(name: 'str | None' = None, states: 'list[str] | None' = None, values: 'list[float] | None' = None, stickiness: 'float | None' = None, transition_matrix: 'list[list[float]] | None' = None, noise_std: 'float' = 0.0) -> 'None'
    → sales:MarkovTrend(states=['low','high'],values=[10,100],stickiness=0.9,noise_std=5)
  SinusoidalTrend(name: 'str | None' = None, amplitude: 'float' = 1.0, freq: 'float' = 1.0, phase: 'float' = 0.0, noise_level: 'float' = 0.0) -> 'None'
    → sales:SinusoidalTrend(amplitude=1,freq=24,phase=0,noise_level=0)
  StockTrend(name: 'str | None' = None, amplitude: 'float' = 15.0, direction: "Literal['up', 'down']" = 'up', noise_level: 'float' = 0.0) -> 'None'
    → sales:StockTrend(amplitude=15.0,direction='up',noise_level=0.0)
  WeekendTrend(name: 'str | None' = None, weekend_effect: 'float' = 1.0, direction: "Literal['up', 'down']" = 'up', noise_level: 'float' = 0.0, limit: 'float' = 10.0) -> 'None'
    → sales:WeekendTrend(weekend_effect=10,direction='up',noise_level=0.5,limit=10)
```

> [!NOTE]
> The `Trend` base class is automatically filtered out of the list. The CLI uses a `Registry` object with `base_class=Trend` to ensure only concrete trend subclasses are available.

---

### 4. `tsdata presets`
Lists available built-in presets or displays configuration details for a specific preset.

```bash
$ tsdata presets
```
*Expected Output:*
```
Available presets:

  minute-stock
    Start: 2024-01-01 09:30:00, End: 2024-01-01 16:00:00, Granularity: min
    Dimensions: 1, Metrics: 1
    Output: minute_stock.csv

  weekly-revenue
    Start: 2020-01-01, End: 2025-12-31, Granularity: W
    Dimensions: 1, Metrics: 1
    Output: weekly_revenue.csv

  monthly-recurring
    Start: 2018-01-01, End: 2025-12-31, Granularity: ME
    Dimensions: 1, Metrics: 1
    Output: monthly_mrr.csv

  scientific-mock
    Start: 2025-01-01T00:00:00, End: 2025-01-07T00:00:00, Granularity: 5min
    Dimensions: 5, Metrics: 5
    Output: scientific_mock_data.csv

  economics-cycle
    Start: 2024-01-01, End: 2025-12-31, Granularity: D
    Dimensions: 3, Metrics: 3
    Output: economics_cycle.csv

  sociology-mobility
    Start: 2023-01-01, End: 2025-12-31, Granularity: D
    Dimensions: 4, Metrics: 3
    Output: sociology_mobility.csv

  electronics-reliability
    Start: 2025-03-01T00:00:00, End: 2025-03-08T00:00:00, Granularity: 5min
    Dimensions: 7, Metrics: 6
    Output: electronics_reliability.csv

  epidemiology-wave
    Start: 2023-01-01, End: 2025-12-31, Granularity: D
    Dimensions: 3, Metrics: 6
    Output: epidemiology_wave.csv

  electronics-paths
    Start: 2024-03-28T00:00:00, End: 2024-04-05T00:00:00, Granularity: 5min
    Dimensions: 0, Metrics: 1
    Output: electronics_paths.csv

  mega-stacked-sinewaves
    Start: 2024-01-01T00:00:00, End: 2024-01-15T00:00:00, Granularity: 5min
    Dimensions: 0, Metrics: 1
    Output: mega_stacked_sinewaves.csv

Use 'tsdata presets <name>' for detailed info on a preset.
Example: tsdata presets minute-stock
```

To see exact config details of a preset:
```bash
$ tsdata presets minute-stock
```
*Expected Output:*
```
Preset: minute-stock

  Start: 2024-01-01 09:30:00
  End: 2024-01-01 16:00:00
  Granularity: min
  Dimensions: ticker:AAPL,MSFT,GOOGL
  Metrics: price:LinearTrend(offset=100,slope=0.2)+MarkovTrend(states=[bear,neutral,bull],values=[10,50,120],stickiness=0.98,noise_std=2.0)+StockTrend(amplitude=10.0,direction=up,noise_level=0.01)
  Output: minute_stock.csv

Usage: tsdata generate --preset minute-stock --output <output.csv>
Or override specific values:
  tsdata generate --preset minute-stock --start 2024-02-01 --output mydata.csv
```

Details for the remaining 9 presets (`tsdata presets <name>`):

<details>
<summary>All 9 additional preset details (weekly-revenue through mega-stacked-sinewaves)</summary>

```
Preset: weekly-revenue

  Start: 2020-01-01
  End: 2025-12-31
  Granularity: W
  Dimensions: department:ordered_choice:electronics,clothing,home
  Metrics: revenue:LinearTrend(offset=10000,slope=10)+SinusoidalTrend(freq=365,amplitude=2000)+MarkovTrend(states=[low,normal,promo],values=[0,2000,8000],stickiness=0.85,noise_std=100)+ARNoiseTrend(decay=0.98,noise_std=50)
  Output: weekly_revenue.csv

Usage: tsdata generate --preset weekly-revenue --output <output.csv>
Or override specific values:
  tsdata generate --preset weekly-revenue --start 2024-02-01 --output mydata.csv
```

```
Preset: monthly-recurring

  Start: 2018-01-01
  End: 2025-12-31
  Granularity: ME
  Dimensions: tier:ordered_choice:basic,pro,enterprise
  Metrics: mrr:LinearTrend(offset=50000,slope=10)+MarkovTrend(states=[slow,normal,fast],values=[1000,5000,15000],stickiness=0.9,noise_std=500)+ARNoiseTrend(decay=0.85,noise_std=1000)
  Output: monthly_mrr.csv

Usage: tsdata generate --preset monthly-recurring --output <output.csv>
Or override specific values:
  tsdata generate --preset monthly-recurring --start 2024-02-01 --output mydata.csv
```

```
Preset: scientific-mock

  Start: 2025-01-01T00:00:00
  End: 2025-01-07T00:00:00
  Granularity: 5min
  Dimensions: experiment_id:auto_generate_name:exp_, sensor_type:random_choice:temperature,pressure,radiation,voltage, lab_location:ordered_choice:Site_A,Site_B,Site_C, batch_number:random_int:1,100, calibration_factor:random_float:0.9,1.1
  Metrics: temperature:SinusoidalTrend(amplitude=5,freq=1.0,phase=0)+LinearTrend(offset=25,slope=0)+ARNoiseTrend(decay=0.85,noise_std=0.1)+WeekendTrend(weekend_effect=4,direction=down), pressure:SinusoidalTrend(amplitude=8,freq=1.0,phase=-2)+LinearTrend(offset=1013,slope=0)+ARNoiseTrend(decay=0.85,noise_std=0.2)+WeekendTrend(weekend_effect=10,direction=down), radiation_level:MarkovTrend(states=[safe,elevated,danger],values=[0.5,1.5,3.5],stickiness=0.95,noise_std=0.05)+SinusoidalTrend(amplitude=2.5,freq=1.0,phase=0)+LinearTrend(offset=2.0,slope=0.01), voltage:SinusoidalTrend(amplitude=3.0,freq=1.0,phase=-1)+LinearTrend(offset=12.0,slope=0)+ARNoiseTrend(decay=0.85,noise_std=0.05)+StockTrend(amplitude=1.0,direction=up,noise_level=0.05)+WeekendTrend(weekend_effect=1.5,direction=down), equipment_load:SinusoidalTrend(amplitude=10,freq=1.0,phase=0)+LinearTrend(offset=80,slope=0)+ARNoiseTrend(decay=0.85,noise_std=0.5)+WeekendTrend(weekend_effect=20,direction=down)
  Output: scientific_mock_data.csv

Usage: tsdata generate --preset scientific-mock --output <output.csv>
Or override specific values:
  tsdata generate --preset scientific-mock --start 2024-02-01 --output mydata.csv
```

```
Preset: economics-cycle

  Start: 2024-01-01
  End: 2025-12-31
  Granularity: D
  Dimensions: country:random_choice:US,DE,IN,BR,JP, sector:random_choice:manufacturing,services,energy,technology, policy_regime:ordered_choice:tightening,neutral,easing
  Metrics: gdp_index:SinusoidalTrend(amplitude=15.0,freq=1000,phase=0)+LinearTrend(offset=120,slope=0.02)+ARNoiseTrend(decay=0.98,noise_std=0.15)+WeekendTrend(weekend_effect=1.0,direction=down), inflation_rate:SinusoidalTrend(amplitude=3.0,freq=1000,phase=-48)+LinearTrend(offset=4.5,slope=0.005)+ARNoiseTrend(decay=0.98,noise_std=0.05)+WeekendTrend(weekend_effect=0.2,direction=down), unemployment_rate:SinusoidalTrend(amplitude=-2.5,freq=1000,phase=-48)+LinearTrend(offset=6.5,slope=-0.005)+ARNoiseTrend(decay=0.98,noise_std=0.03)+WeekendTrend(weekend_effect=0.1,direction=up)
  Output: economics_cycle.csv

Usage: tsdata generate --preset economics-cycle --output <output.csv>
Or override specific values:
  tsdata generate --preset economics-cycle --start 2024-02-01 --output mydata.csv
```

```
Preset: sociology-mobility

  Start: 2023-01-01
  End: 2025-12-31
  Granularity: D
  Dimensions: age_group:ordered_choice:18-24,25-34,35-49,50-64,65+, region:random_choice:urban,suburban,rural, education_level:random_choice:high_school,bachelors,masters,doctorate, respondent_batch:random_int:1,50
  Metrics: mobility_score:SinusoidalTrend(amplitude=12,freq=1000,phase=0)+LinearTrend(offset=55,slope=0.01)+ARNoiseTrend(decay=0.98,noise_std=0.15)+WeekendTrend(weekend_effect=4.0,direction=down), trust_index:SinusoidalTrend(amplitude=8,freq=1000,phase=-24)+LinearTrend(offset=60,slope=0)+ARNoiseTrend(decay=0.98,noise_std=0.1)+WeekendTrend(weekend_effect=2.5,direction=down), participation_rate:SinusoidalTrend(amplitude=6,freq=1000,phase=-48)+LinearTrend(offset=58,slope=0.01)+ARNoiseTrend(decay=0.98,noise_std=0.15)+WeekendTrend(weekend_effect=3.0,direction=down)
  Output: sociology_mobility.csv

Usage: tsdata generate --preset sociology-mobility --output <output.csv>
Or override specific values:
  tsdata generate --preset sociology-mobility --start 2024-02-01 --output mydata.csv
```

```
Preset: electronics-reliability

  Start: 2025-03-01T00:00:00
  End: 2025-03-08T00:00:00
  Granularity: 5min
  Dimensions: chip_id:auto_generate_name:chip, assembly_line:ordered_choice:Line_A,Line_B,Line_C,Line_D, component_family:random_choice:power,rf,digital,sensor,analog, test_station:random_choice:ICT1,ICT2,FCT1,FCT2,BURNIN, lot_number:random_int:1000,1300, reference_voltage:random_float:3.0,3.6, qa_mode:constant:production
  Metrics: voltage_drift:LinearTrend(offset=3.3,slope=-0.0003)+SinusoidalTrend(amplitude=0.2,freq=7.0,phase=0)+ARNoiseTrend(decay=0.99,noise_std=0.001)+WeekendTrend(weekend_effect=0.15,direction=down,limit=0.15), temperature_c:SinusoidalTrend(amplitude=5.0,freq=7.0,phase=-6)+LinearTrend(offset=25.0,slope=0.01)+ARNoiseTrend(decay=0.99,noise_std=0.05)+WeekendTrend(weekend_effect=2.0,direction=down,limit=2.0), defect_ppm:MarkovTrend(states=[normal,warn,critical],values=[1.0,2.0,3.0],stickiness=0.99,noise_std=0.1)+SinusoidalTrend(amplitude=150.0,freq=7.0,phase=-12)+LinearTrend(offset=500.0,slope=0)+ARNoiseTrend(decay=0.99,noise_std=5.0)+WeekendTrend(weekend_effect=70.0,direction=down,limit=70.0), throughput_units:SinusoidalTrend(amplitude=100.0,freq=7.0,phase=0)+LinearTrend(offset=850,slope=0.03)+ARNoiseTrend(decay=0.99,noise_std=1.0)+WeekendTrend(weekend_effect=70.0,direction=down,limit=70.0), supplier_shock_index:StockTrend(amplitude=10.0,direction=up,noise_level=0.05)+SinusoidalTrend(amplitude=5.0,freq=7.0,phase=-18)+LinearTrend(offset=100.0,slope=0)+WeekendTrend(weekend_effect=2.0,direction=down,limit=2.0), holiday_pressure_index:HolidayTrend(effect=40,pre_window=1,post_window=1,direction=up,dates=[2025-03-03,2025-03-06])+SinusoidalTrend(amplitude=80.0,freq=7.0,phase=0)+LinearTrend(offset=120.0,slope=0)
  Output: electronics_reliability.csv

Usage: tsdata generate --preset electronics-reliability --output <output.csv>
Or override specific values:
  tsdata generate --preset electronics-reliability --start 2024-02-01 --output mydata.csv
```

```
Preset: epidemiology-wave

  Start: 2023-01-01
  End: 2025-12-31
  Granularity: D
  Dimensions: region:random_choice:North,South,East,West, age_band:ordered_choice:0-17,18-39,40-64,65+, pathogen_variant:ordered_choice:A,B,C
  Metrics: incidence_rate:SinusoidalTrend(amplitude=80,freq=1000,phase=0)+LinearTrend(offset=150,slope=0)+ARNoiseTrend(decay=0.98,noise_std=1.0)+WeekendTrend(weekend_effect=15,direction=down), hospitalization_rate:SinusoidalTrend(amplitude=12,freq=1000,phase=-48)+LinearTrend(offset=25,slope=0)+ARNoiseTrend(decay=0.98,noise_std=0.15)+WeekendTrend(weekend_effect=2,direction=down), testing_volume:SinusoidalTrend(amplitude=250,freq=1000,phase=0)+LinearTrend(offset=1500,slope=0)+ARNoiseTrend(decay=0.98,noise_std=4.0)+WeekendTrend(weekend_effect=700,direction=down), positivity_rate:SinusoidalTrend(amplitude=8,freq=1000,phase=-24)+LinearTrend(offset=15,slope=0)+ARNoiseTrend(decay=0.98,noise_std=0.1)+WeekendTrend(weekend_effect=2.0,direction=down), death_rate:SinusoidalTrend(amplitude=1.5,freq=1000,phase=-96)+LinearTrend(offset=4.0,slope=0)+ARNoiseTrend(decay=0.98,noise_std=0.015)+WeekendTrend(weekend_effect=0.8,direction=down), icu_occupancy:SinusoidalTrend(amplitude=3.5,freq=1000,phase=-72)+LinearTrend(offset=8.0,slope=0)+ARNoiseTrend(decay=0.98,noise_std=0.04)+WeekendTrend(weekend_effect=0.8,direction=down)
  Output: epidemiology_wave.csv

Usage: tsdata generate --preset epidemiology-wave --output <output.csv>
Or override specific values:
  tsdata generate --preset epidemiology-wave --start 2024-02-01 --output mydata.csv
```

```
Preset: electronics-paths

  Start: 2024-03-28T00:00:00
  End: 2024-04-05T00:00:00
  Granularity: 5min
  Dimensions: 
  Metrics: paths:LinearTrend(offset=860,slope=0)+SinusoidalTrend(amplitude=4,freq=1,phase=6,noise_level=0)+ARNoiseTrend(decay=0.7,noise_std=3)
  Output: electronics_paths.csv

Usage: tsdata generate --preset electronics-paths --output <output.csv>
Or override specific values:
  tsdata generate --preset electronics-paths --start 2024-02-01 --output mydata.csv
```

```
Preset: mega-stacked-sinewaves

  Start: 2024-01-01T00:00:00
  End: 2024-01-15T00:00:00
  Granularity: 5min
  Dimensions: 
  Metrics: mega_signal:LinearTrend(offset=60,slope=0,noise_level=0.3)+SinusoidalTrend(amplitude=22,freq=30,phase=0,noise_level=0.2)+SinusoidalTrend(amplitude=18,freq=14,phase=4,noise_level=0.2)+SinusoidalTrend(amplitude=15,freq=7,phase=2,noise_level=0.2)+SinusoidalTrend(amplitude=12,freq=3.5,phase=6,noise_level=0.2)+SinusoidalTrend(amplitude=10,freq=1.75,phase=1,noise_level=0.2)+SinusoidalTrend(amplitude=8,freq=1,phase=6,noise_level=0.2)+SinusoidalTrend(amplitude=6,freq=0.5,phase=3,noise_level=0.2)+SinusoidalTrend(amplitude=5,freq=0.25,phase=0,noise_level=0.15)+SinusoidalTrend(amplitude=4,freq=0.125,phase=9,noise_level=0.15)+SinusoidalTrend(amplitude=3,freq=0.0625,phase=5,noise_level=0.1)+SinusoidalTrend(amplitude=2,freq=0.05,phase=12,noise_level=0.1)+WeekendTrend(weekend_effect=10,direction=down,noise_level=1.0,limit=12)+MarkovTrend(states=[low,mid,high],values=[-8,0,8],stickiness=0.95,noise_std=1.5)+ARNoiseTrend(decay=0.55,noise_std=1.8)+StockTrend(amplitude=1.5,direction=up,noise_level=0.3)
  Output: mega_stacked_sinewaves.csv

Usage: tsdata generate --preset mega-stacked-sinewaves --output <output.csv>
Or override specific values:
  tsdata generate --preset mega-stacked-sinewaves --start 2024-02-01 --output mydata.csv
```

</details>

> [!NOTE]
> Presets define default values for `start`, `end`, `granularity`, `dims`, `mets`, and `output`.  CLI flags override preset values — use `--start`, `--end`, or `--output` to customise without editing the preset.

---

## 🔌 CLI Architecture: Pluggable Registries

The CLI parser in `cli.py` uses helper functions (`_parse_dimension_spec`, `_parse_trend_spec`, and `_parse_anomaly_spec`) to parse spec strings like `name=func(args)` into `GeneratorConfig` / component instances, backed by `Registry` objects (`ts_data_generator.registry`) for component lookup.

```python
# Each registry is instantiated with a module path and optional filters
_DIMENSION_REGISTRY = Registry(
    "ts_data_generator.functions",
    name_filter=lambda n: not n.startswith("_"),
)
_TREND_REGISTRY = Registry(
    "ts_data_generator.trends",
    name_filter=lambda n: not n.startswith("_") and n != "Trend",
    base_class=Trend,
)
_ANOMALY_REGISTRY = Registry(
    "ts_data_generator.anomalies",
    name_filter=lambda n: not n.startswith("_") and n != "Anomaly",
    base_class=Anomaly,
)
```

- **`name_filter`** controls which names appear in error messages and `list_available()`.
- **`base_class`** ensures only concrete subclasses of `Trend` or `Anomaly` are available, filtering out abstract bases and non-class values.

To add a new CLI-pluggable type (e.g. a custom trend), simply define a class that inherits from `Trend` in the `ts_data_generator.trends` module (and include it in `__all__`) — the Registry discovers it automatically. No need to register it manually.

---

## 📄 JSON Configuration Files

For large, multi-metric datasets or production pipelines, configuring generation inside a clean JSON file is highly recommended. 

To run a configuration file:
```bash
tsdata generate --config config.json
```

### Complete Example 1: `stock_price_simulation.json`
```json
{
  "start": "2024-01-01",
  "end": "2024-01-02",
  "granularity": "5min",
  "seed": 42,
  "expand_dimensions": true,
  "dimensions": [
    "ticker:ordered_choice:AAPL,GOOG,MSFT",
    "exchange:constant:NASDAQ"
  ],
  "metrics": [
    "price:StockTrend(amplitude=150.0,noise_level=0.2)"
  ],
  "anomalies": [
    "price:MissingData(mode=random,probability=0.005)"
  ],
  "output": "simulated_stocks.csv"
}
```

### Complete Example 2: `iot_telemetry.json`
```json
{
  "start": "2024-06-01T00:00:00",
  "end": "2024-06-07T23:55:00",
  "granularity": "5min",
  "seed": 9876,
  "dimensions": [
    "device_id:auto_generate_name:sensor_"
  ],
  "metrics": [
    "temp:LinearTrend(offset=22.0,slope=15)+SinusoidalTrend(amplitude=3.0,freq=1.0)+ARNoiseTrend(decay=0.9,noise_std=0.2)",
    "humidity:SinusoidalTrend(amplitude=15.0,freq=1.0)+ARNoiseTrend(decay=0.8,noise_std=0.5)"
  ],
  "anomalies": [
    "temp:PointAnomaly(probability=0.005,magnitude=(5.0,15.0))+MissingData(mode=burst,burst_probability=0.002,min_length=3,max_length=6)"
  ],
  "output": "iot_telemetry.csv"
}
```

### Complete Example 3: `concept_drift.json`
```json
{
  "start": "2024-01-01T00:00:00",
  "end": "2024-01-07T23:00:00",
  "granularity": "h",
  "seed": 42,
  "dimensions": [
    "region:North,South"
  ],
  "metrics": [
    "cpu:LinearTrend(offset=30,slope=2)+SinusoidalTrend(amplitude=10,freq=1)"
  ],
  "anomalies": [
    "cpu:PointAnomaly(probability=0.01,magnitude=(10,20))",
    "cpu:ConceptDrift(start_timestamp=2024-01-03T12:00:00,transition_window=3600,target_mean=80,target_std=5,hold_duration=14400,restore=true)"
  ],
  "output": "concept_drift.csv"
}
```

---

## 🌐 Environment Variables

You can override or define default values for **any** CLI argument using environment variables prefixed with `TSDATA_`. 

Command-line parameters passed directly will always override their corresponding environment variables.

```bash
# 1. Export defaults
export TSDATA_START="2024-01-01"
export TSDATA_END="2024-01-31"
export TSDATA_GRANULARITY="D"
export TSDATA_SEED="12345"

# 2. Run the command (automatically picks up export values)
tsdata generate \
  --dims "region:US,EU" \
  --mets "visitors:LinearTrend(slope=10)" \
  --output visitors.csv
```
