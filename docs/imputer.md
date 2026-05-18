---
layout: default
title: Schema Imputing
---

# Schema Imputing

Reverse-engineer trend parameters from existing CSV data.

## Usage

Requires the `imputer` extra:
```bash
pip install "ts-data-generator[imputer]"
```

### Python Example

```python
from ts_data_generator.schema.converter import SchemaConverter

converter = SchemaConverter("data.csv", index_col=0)
schema = converter.impute_schema()
trends = converter.analyze_numeric_trends(columns=["sales"], top_freq=2)
converter.construct_trend_column("sales", trends["sales"])
```

The `SchemaConverter` analyzes your data to find the best-fitting trend parameters, making it easy to replicate real-world datasets.
