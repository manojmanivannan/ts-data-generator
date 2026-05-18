## Parent PRD

`issues/prd.md` — Problem Statement, Solution, Implementation Decisions (MissingData)

## What to build

Implement `MissingData` anomaly class with `mode="random"` (per-timestamp independent probability) and `mode="burst"` (consecutive blocks of missing data). Random mode: `MissingData(mode="random", probability=0.05)` — each timestamp independently has 5% chance of being NaN. Burst mode: `MissingData(mode="burst", burst_probability=0.02, min_length=3, max_length=10)` — a burst starts with 2% probability at each timestamp (bursts cannot overlap), and the gap length is uniformly sampled from [min_length, max_length]. Since MissingData is always last in the pipeline, NaN values are never overwritten.

## Acceptance criteria

- [ ] `MissingData(mode="random", probability=0.05)` produces ~5% NaN values across the metric column
- [ ] `MissingData(mode="burst", burst_probability=0.02, min_length=3, max_length=10)` produces consecutive NaN blocks within the length range
- [ ] Burst mode does not produce overlapping gaps
- [ ] With a fixed seed, NaN positions are deterministic
- [ ] When both `PointAnomaly` and `MissingData` are on the same metric, point anomalies do not appear on NaN timestamps (NaN stays NaN)
- [ ] Tests in `tests/test_anomalies.py` cover both modes, seed determinism, burst length bounds, and NaN-preservation in pipeline

## Blocked by

- Blocked by `issues/002-anomaly-pipeline-point.md`

## User stories addressed

- 2. As a data engineer testing pipeline robustness, I want to introduce random missing data points into generated metrics.
- 4. As a reliability engineer modeling burst failures, I want to introduce consecutive blocks of missing data.
- 5. As a user who needs deterministic test datasets, I want to seed the entire generation pipeline.
