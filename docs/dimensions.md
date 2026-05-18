---
permalink: /dimensions
layout: default
title: Dimension Generators
parent: Core Concepts
nav_order: 1
---

# Dimension Generators

Dimensions are non-numeric or static numeric columns that provide context. They are implemented as infinite Python iterators.

## Built-in Helpers

You can find these in `ts_data_generator.utils.functions`.

| Function | Description | Example |
|:---|:---|:---|
| `random_choice(vals)` | Uniform random selection | `["US", "EU", "AP"]` |
| `ordered_choice(vals)` | Round-robin selection | `["A", "B", "C"]` |
| `random_int(min, max)`| Random integer | `1, 100` |
| `random_float(min, max)`| Random float | `0.0, 1.0` |
| `constant(val)` | Always the same value | `"Production"` |
| `auto_generate_name(pre)`| Incremental names | `"user_"` -> `user_1, user_2, ...` |

## CLI Shorthand

In the CLI, you can define dimensions quickly:

```bash
# Defaults to random_choice
--dims "region:US,EU,AP"

# Explicit helper
--dims "id:auto_generate_name:device_"
```

## Custom Generators

Because dimensions are just iterators, you can pass any generator function to the API:

```python
def poisson_id():
    import numpy as np
    while True:
        yield f"node_{np.random.poisson(5)}"

dg.add_dimension("node", poisson_id())
```
