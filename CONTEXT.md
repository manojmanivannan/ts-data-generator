# ts-data-generator

Synthetic time series generation library combining dimensions, trends, anomalies, and multi-item groups into timestamp-indexed datasets.

## Language

**DataGenerator**:
The core time series generation engine that orchestrates dimensions, metrics, and multi-items over a configured date range and granularity, evaluating lazily when `.data` or `.generate()` is accessed.
_Avoid_: DataGen (as the primary class name; kept only as a convenience alias)

**Granularity**:
A string-backed enumeration of time-step intervals (`SECOND`, `MINUTE`, `FIVE_MINUTE`, `HOUR`, `DAY`, `WEEK`, `MONTH`, `YEAR`) using singular time-unit nouns.
_Avoid_: ONE_SECOND, ONE_MIN, FIVE_MIN, HOURLY, DAILY, WEEKLY, MONTHLY, YEARLY

**Metric**:
A named numeric time series column composed additively of one or more trends and optional anomaly injectors, aggregated via a configured aggregation method when resampled.
_Avoid_: Metrics (as a single-instance class name)

**Dimension**:
A named categorical or continuous column driven by a value generator across timestamps or expanded across its distinct domain values in a Cartesian product.
_Avoid_: Dimensions (as a single-instance class name)

**MultiItem**:
A group of linked columns generated simultaneously as tuples from a single generator, acting either as linked dimensions or (when aggregation methods are specified) as linked metrics.
_Avoid_: MultiItems (as a single-instance class name)

**Trend**:
A deterministic or stochastic time series component evaluated over a timestamp index and summed into a Metric's clean baseline before anomalies are applied.
_Avoid_: Trends (as the abstract base class name)
