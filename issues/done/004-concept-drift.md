## Parent PRD

`issues/prd.md` — Problem Statement, Solution, Implementation Decisions (ConceptDrift)

## What to build

Implement `ConceptDrift` anomaly class with a single drift segment. A `DriftSegment` specifies: `start_index` or `start_timestamp`, `transition_window` (number of timestamps for gradual onset), `target_mean`, `target_std`, `hold_duration` (how long to stay in the new regime), and `restore` (bool). During `transition_window`, values interpolate between the trend-generated baseline and draws from `N(target_mean, target_std)` — early timestamps are mostly baseline, late timestamps are mostly target. During `hold_duration`, all values are drawn from `N(target_mean, target_std)`. If `restore=True`, after the hold duration there's another transition window interpolating back to the baseline.

## Acceptance criteria

- [ ] `ConceptDrift(segments=[DriftSegment(start_index=100, transition_window=50, target_mean=50, target_std=5, hold_duration=200, restore=True)])` shifts the metric to the target distribution
- [ ] During transition, values visibly move from baseline to target (not an abrupt jump)
- [ ] During hold, the sample mean approximates `target_mean` and sample std approximates `target_std` within tolerance
- [ ] When `restore=True`, values return to baseline distribution after hold
- [ ] With a fixed seed, drift timing and drawn values are deterministic
- [ ] Tests in `tests/test_anomalies.py` cover: transition interpolation, hold distribution moments, restore behavior, and seed determinism

## Blocked by

- Blocked by `issues/002-anomaly-pipeline-point.md`

## User stories addressed

- 3. As a data scientist simulating real-world sensor degradation, I want to apply a gradual concept drift that shifts a metric's mean and variance over a transition window.
- 5. As a user who needs deterministic test datasets, I want to seed the entire generation pipeline.
