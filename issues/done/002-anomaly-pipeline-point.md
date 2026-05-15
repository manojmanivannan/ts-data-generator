## Parent PRD

`issues/prd.md` — Problem Statement, Solution, Implementation Decisions (Architecture, Anomalies attach inline, PointAnomaly, Pipeline ordering)

## What to build

Establish the anomaly pipeline and ship PointAnomaly end-to-end. Create the `anomalies/` package with an abstract `Anomaly` base class defining `intervene(base_array, timestamps, rng) -> np.ndarray`. Add an `anomalies` parameter (list of `Anomaly` instances) to `Metrics` and `DataGen.add_metric()`. In `Metrics.generate()`, after trends compose the base array, run it through each anomaly's `intervene()` in order. Implement `PointAnomaly` with `probability`, `mode="additive"|"replacement"`, and `magnitude` (scalar or (min, max) range). The full flow: `dg.add_metric("m", {LinearTrend()}, anomalies=[PointAnomaly(prob=0.1, magnitude=5)])` → trend generates base → point anomalies intervene → metric column in DataFrame.

## Acceptance criteria

- [ ] `Anomaly` abstract base class exists with `intervene()` method signature
- [ ] `Metrics` accepts `anomalies` list; `DataGen.add_metric()` passes it through
- [ ] `PointAnomaly(prob=0.1, magnitude=5, mode="additive")` introduces spikes in ~10% of timestamps
- [ ] `PointAnomaly(prob=0.05, magnitude=999, mode="replacement")` replaces ~5% of values with 999
- [ ] `magnitude` as a tuple like `(5, 20)` samples uniformly from the range for each anomaly
- [ ] With a fixed seed, anomaly positions and magnitudes are deterministic
- [ ] Pipeline order is respected: if multiple anomalies are listed, they apply in order
- [ ] Tests in `tests/test_anomalies.py` cover both modes, seed determinism, rate tolerance, and pipeline ordering

## Blocked by

- Blocked by `issues/001-rng-foundation.md`

## User stories addressed

- 1. As an MLOps engineer benchmarking anomaly detection models, I want to inject point anomalies at a configurable rate and magnitude into my time series.
- 5. As a user who needs deterministic test datasets, I want to seed the entire generation pipeline.
- 12. As a user who needs additive anomalies, I want point anomalies that add to the underlying trend value.
- 13. As a user simulating sensor glitches, I want point anomalies that replace the underlying value entirely.
