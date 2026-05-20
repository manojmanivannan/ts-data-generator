---
permalink: /dimensions
layout: default
title: Dimension Generators
parent: Core Concepts
nav_order: 1
---

# Dimension Generators

Dimensions are non-numeric or static categorical columns that provide context, labeling, and grouping for your time series metrics (e.g., `store_id`, `region`, `device_id`, `client_version`). 

In `ts-data-generator`, dimensions are designed to be **infinite Python iterators** (generators). Because they yield values on-demand, they can easily populate a dataset of any arbitrary duration or granularity without running out of memory.

---

## 🛠️ Built-in Dimension Helpers

The package includes a comprehensive set of pre-built dimension helpers inside `ts_data_generator.utils.functions`. These functions can be used in your Python scripts or invoked directly in your terminal using the CLI shorthand.

| Helper | Type | Description | Example CLI Shorthand |
|:---|:---|:---|:---|
| `constant(value)` | Deterministic | Yields the same value indefinitely. | `env:constant:production` |
| `ordered_choice(vals)` | Deterministic | Cycles through values in a round-robin order. | `server:ordered_choice:srv1,srv2,srv3` |
| `random_choice(vals)` | Stochastic | Selects a random element uniformly at each step. | `region:random_choice:US,EU,AP` |
| `random_int(min, max)`| Stochastic | Yields random integers in `[min, max]` (inclusive). | `user_id:random_int:1000,9999` |
| `random_float(min, max)`| Stochastic | Yields random floats in `[min, max)` (exclusive). | `weight:random_float:0.0,1.0` |
| `auto_generate_name(pre)`| Deterministic | Yields incrementing string keys with a prefix. | `id:auto_generate_name:sensor` |

---

## 💻 CLI Shorthand Syntax

The CLI provides a convenient way to define dimensions using the `--dims` (or `-d`) flag. 

The format follows:
```bash
--dims "column_name:helper_name:arg1,arg2,..."
```

> [!TIP]
> If you omit the helper name entirely, the CLI will automatically default to `random_choice`:
> `--dims "region:US,EU,AP"` is identical to `--dims "region:random_choice:US,EU,AP"`

### Concrete CLI Examples:

```bash
# 1. Uniformly assign a random region to each row
tsdata generate --dims "region:US,EU,AP" --start 2024-01-01 --end 2024-01-02 --granularity h --output data.csv

# 2. Cycle deterministically through nodes (ordered_choice)
tsdata generate --dims "node:ordered_choice:nodeA,nodeB,nodeC" --start 2024-01-01 --end 2024-01-02 --granularity h --output data.csv

# 3. Generate incrementing device IDs with a prefix
tsdata generate --dims "device:auto_generate_name:device_" --start 2024-01-01 --end 2024-01-02 --granularity h --output data.csv

# 4. Generate random continuous float weights and random discrete integer IDs
tsdata generate \
  --dims "sensor_weight:random_float:0.5,1.5" \
  --dims "cust_id:random_int:100000,999999" \
  --start 2024-01-01 --end 2024-01-02 --granularity h --output data.csv
```

---

## 🐍 Python API Usage

When using the Python API, you pass an infinite generator or any standard Python `Iterable` to the `.add_dimension()` method.

Here is a fully runnable script showcasing all built-in helpers and custom generators:

```python
from ts_data_generator import DataGen
from ts_data_generator.utils.functions import (
    constant,
    ordered_choice,
    random_choice,
    random_float,
    random_int,
    auto_generate_name
)

# Initialize DataGen
dg = DataGen(seed=42)
dg.start_datetime = "2024-01-01"
dg.end_datetime = "2024-01-03"
dg.to_granularity("h")

# 1. Using a static constant
dg.add_dimension("environment", constant("production"))

# 2. Cycling through list in round-robin order
dg.add_dimension("node_id", ordered_choice(["node_01", "node_02", "node_03"]))

# 3. Uniformly picking random values
dg.add_dimension("region", random_choice(["North", "South", "East", "West"]))

# 4. Generating random integers
dg.add_dimension("user_segment", random_int(1, 5))

# 5. Generating random floats
dg.add_dimension("coefficient", random_float(0.0, 1.0))

# 6. Auto-generating prefixed names (e.g. dev_1, dev_2, etc.)
dg.add_dimension("device_group", auto_generate_name("dev"))

# 7. Creating and attaching a completely custom infinite generator
def custom_infinite_seq():
    index = 0
    while True:
        yield f"batch_val_{index}"
        index += 3

dg.add_dimension("custom_batch", custom_infinite_seq())

# Verify column outputs
df = dg.data
print(df.head())
```

Output:
```bash
                          epoch environment  node_id region  user_segment  coefficient device_group  custom_batch
2024-01-01 00:00:00  1704067200  production  node_01   East             3     0.719306          d_1   batch_val_0
2024-01-01 01:00:00  1704070800  production  node_02   West             3     0.323770          d_1   batch_val_3
2024-01-01 02:00:00  1704074400  production  node_03   West             3     0.092849          d_1   batch_val_6
2024-01-01 03:00:00  1704078000  production  node_01   East             2     0.189741          d_1   batch_val_9
2024-01-01 04:00:00  1704081600  production  node_02  North             4     0.138835          d_1  batch_val_12
```
---

## 🔗 Advanced: Linked Dimensions (Multi-Items)

In real-world data, columns are often closely linked. For example, if you have a `city` column and a `country` column, you can't assign them independently (e.g., `New York` must map to `US`, not `UK`). 

To generate multiple correlated columns simultaneously, use the `add_multi_items` API.

> [!WARNING]
> Do not use `.add_dimension()` for linked columns, as they will be generated independently and lose correlation. Instead, use `.add_multi_items()`.

Here is a complete, runnable example showing how to configure linked city-country columns:

```python
import random
from ts_data_generator import DataGen

# 1. Define an infinite generator yielding tuples of values
def city_country_generator():
    options = [
        ("New York", "US", "North America"),
        ("London", "UK", "Europe"),
        ("Tokyo", "JP", "Asia"),
        ("Sydney", "AU", "Oceania")
    ]
    while True:
        # Uniformly pick one tuple
        yield random.choice(options)

# 2. Setup DataGen
dg = DataGen(seed=123)
dg.start_datetime = "2024-01-01"
dg.end_datetime = "2024-01-02"
dg.to_granularity("h")

# 3. Add linked dimensions by passing the columns names list and the generator function
dg.add_multi_items(
    names=["city", "country", "continent"],
    function=city_country_generator()
)

# Render and verify
df = dg.data
print(df[["city", "country", "continent"]].head(10))
```

Output:
```bash
                         city country      continent
2024-01-01 00:00:00    London      UK         Europe
2024-01-01 01:00:00    Sydney      AU        Oceania
2024-01-01 02:00:00  New York      US  North America
2024-01-01 03:00:00    London      UK         Europe
2024-01-01 04:00:00  New York      US  North America
2024-01-01 05:00:00  New York      US  North America
2024-01-01 06:00:00    Sydney      AU        Oceania
2024-01-01 07:00:00     Tokyo      JP           Asia
2024-01-01 08:00:00    Sydney      AU        Oceania
2024-01-01 09:00:00     Tokyo      JP           Asia
```
