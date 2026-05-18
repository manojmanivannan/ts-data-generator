---
layout: default
title: Contributing
permalink: /contributing
nav_order: 7
---

# Contributing

We welcome contributions to the Synthetic Time Series Data Generator!

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/manojmanivannan/ts-data-generator.git
   cd ts-data-generator
   ```

2. **Install dependencies** (using `uv` is recommended):
   ```bash
   uv sync --extra dev
   ```

3. **Run tests**:
   ```bash
   pytest
   ```

## Adding New Features

### New Trends
1. Create a new class in `src/ts_data_generator/utils/trends.py`.
2. Inherit from the `Trend` base class.
3. Implement the `__call__` method.

### New Anomalies
1. Create a new class in `src/ts_data_generator/anomalies/`.
2. Inherit from `Anomaly`.
3. Implement the `apply` method.

## Documentation
If you change any public API, please update the documentation in the `docs/` directory.
