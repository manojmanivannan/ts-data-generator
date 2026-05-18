---
permalink: /dimensions
layout: default
title: Dimension Generators
parent: Core Concepts
nav_order: 1
---

# Dimension Generators

Dimensions are non-numeric or static numeric columns that provide context and grouping for your time series data. In `ts-data-generator`, dimensions are implemented as infinite Python iterators (generators), allowing them to produce values for any length of time series.

## Built-in Helpers

You can find these in `ts_data_generator.utils.functions`. These are designed to be used both in the Python API and via the CLI shorthand.

| Function | Description | Example CLI Shorthand |
|:---|:---|:---|
| `constant(value)` | Yields the same value indefinitely. If a list/tuple is provided, it cycles through them. | `region:constant:US` or `env:constant:prod,staging` |
| `random_choice(vals)` | Uniformly selects a random element from the provided list at each step. | `status:random_choice:OK,ERROR,WARN` |
| `ordered_choice(vals)` | Cycles through the provided elements in a round-robin (deterministic) fashion. | `node:ordered_choice:node1,node2,node3` |
| `random_int(min, max)`| Yields a random integer between `min` and `max` (inclusive). | `user_id:random_int:1000,9999` |
| `random_float(min, max)`| Yields a random float between `min` and `max` (exclusive). | `weight:random_float:0.0,1.0` |
| `auto_generate_name(pre)`| Generates incremental names with a prefix (e.g., `d_1`, `d_2`). | `id:auto_generate_name:device` |

## CLI Shorthand

The CLI provides a convenient way to define dimensions using the `--dims` (or `-d`) flag. The syntax follows:
`name:function:arg1,arg2,...`

If the function name is omitted, it defaults to `random_choice`:
`name:arg1,arg2,...`

### Examples:

```bash
# Randomly assign a region to each row
tsdata generate --dims "region:US,EU,AP" ...

# Use a specific helper with arguments
tsdata generate --dims "device_id:auto_generate_name:sensor" ...

# Multiple dimensions
tsdata generate --dims "env:prod,test" --dims "region:ordered_choice:US,EU" ...
```

## Python API Usage

In the Python API, you pass an iterator to the `add_dimension` method.

```python
from ts_data_generator import DataGen
from ts_data_generator.utils.functions import random_choice, auto_generate_name

dg = DataGen()

# Using built-in helpers
dg.add_dimension("region", random_choice(["North", "South"]))
dg.add_dimension("id", (f"id_{i}" for i in range(10000))) # Custom generator expression

# Using custom functions
def sequence_gen():
    i = 0
    while True:
        yield f"step_{i}"
        i += 1

dg.add_dimension("sequence", sequence_gen())
```

## Advanced: Linked Dimensions (MultiItems)

Sometimes you need multiple columns that are logically linked (e.g., a city and its corresponding country). You can use the `MultiItems` class for this.

```python
from ts_data_generator.core.models import MultiItems
import random

def city_country_gen():
    locations = [("New York", "US"), ("London", "UK"), ("Tokyo", "JP")]
    while True:
        yield random.choice(locations)

dg.add_multi_item(MultiItems(names=["city", "country"], function=city_country_gen()))
```
