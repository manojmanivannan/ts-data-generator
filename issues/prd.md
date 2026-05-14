## Problem Statement

Users of `ts-data-generator` need synthetic time series data that reflects real-world imperfections — anomalies, missing data, and regime shifts — to benchmark anomaly detection pipelines and test data pipeline robustness. The library's current trend model (Sinusoidal, Linear, Weekend, Stock) produces only clean, uninterrupted signals. Additionally, the trend vocabulary lacks localized holiday effects and autoregressive noise models (AR, Markov chains) that would increase real-world fidelity for domain-specific use cases like retail forecasting and sensor simulation.

## Solution

Extend `ts-data-generator` with two capabilities:

**Anomaly and missing data injection** — a first-class anomaly pipeline attached to individual metrics, applying during generation rather than as post-processing. Three anomaly types: configurable point anomalies (additive spikes or replacement outliers), concept drifts (gradual distribution-level regime shifts with multi-segment sequencing and restore), and missing data injection (random, burst, or patterned NaN gaps). All governed by a global seed for full reproducibility.

**Expanded trend models** — a `HolidayTrend` with pre/post ramping windows powered by the `holidays` library (optional dependency), an `ARNoiseTrend` for autoregressive order-p noise (explicit coefficients or auto-generated from a stability-preserving decay parameter), and a `MarkovTrend` for discrete-state regime-switching noise (stickiness for CLI, full transition matrix for Python API).

## User Stories

1. As an MLOps engineer benchmarking anomaly detection models, I want to inject point anomalies at a configurable rate and magnitude into my time series, so that I can measure my detector's precision and recall against known ground truth.

2. As a data engineer testing pipeline robustness, I want to introduce random missing data points into generated metrics, so that I can verify my imputation and null-handling logic works end-to-end.

3. As a data scientist simulating real-world sensor degradation, I want to apply a gradual concept drift that shifts a metric's mean and variance over a transition window, so that I can benchmark drift-detection algorithms against realistic regime changes.

4. As a reliability engineer modeling burst failures, I want to introduce consecutive blocks of missing data (not just isolated points), so that I can test how my pipeline handles sustained sensor outages.

5. As a user who needs deterministic test datasets, I want to seed the entire generation pipeline — trends, anomalies, and missing data — so that I get identical output on every run.

6. As a retail data scientist generating sales forecasts, I want a holiday trend that boosts values on major holidays with configurable pre-holiday and post-holiday ramp windows, so that my synthetic data reflects seasonal shopping behavior.

7. As a quant generating synthetic asset prices, I want a discrete Markov chain noise model where I can define states (low-vol, high-vol, crash) and transition probabilities, so that my data exhibits realistic regime-switching behavior.

8. As a time series researcher, I want autoregressive noise with configurable order and coefficients, so that residuals in my synthetic data exhibit realistic serial correlation instead of white noise.

9. As a CLI-first user, I want to specify anomaly specs from the command line alongside my existing `--mets` and `--dims` flags, so that I don't need to write Python to generate data with anomalies.

10. As a library user who doesn't want to install `holidays`, I want `HolidayTrend` to accept a user-provided list of dates as a fallback, so that I can use holiday effects without the optional dependency.

11. As a user running experiments across multiple locales, I want to specify a country code for `HolidayTrend` and have it automatically resolve the correct federal and bank holidays, including moving holidays like Easter.

12. As a user who needs additive anomalies, I want point anomalies that add to the underlying trend value, so that the base signal structure is preserved beneath the spike.

13. As a user simulating sensor glitches, I want point anomalies that replace the underlying value entirely (like a sensor reading 999), so that I can benchmark systems that detect value substitution attacks.

14. As a user modeling complex seasonal patterns, I want to define an arbitrary sequence of concept drifts — transition to regime A, hold, transition to regime B, hold, restore to baseline — so that my data reflects multi-phase behavioral shifts.

15. As a user who wants patterned missing data, I want to specify that data is missing during specific recurring time windows (e.g., "every Sunday 2-4am"), so that I can simulate maintenance windows or batch processing gaps.

16. As a user installing the library, I want to install all optional features with a single `pip install "ts-data-generator[all]"` command, so that I don't need to remember individual extra names.

## Implementation Decisions

### Architecture: anomalies as first-class generation pipeline

Anomalies and missing data apply during metric generation, not as post-hoc DataFrame mutations. Within each metric, the pipeline is fixed: trends produce a base array by additive composition, then anomalies intervene in order (PointAnomaly → ConceptDrift → MissingData). MissingData always applies last so NaN values are never overwritten by subsequent anomaly steps.

### Anomalies attach inline to Metrics

`Metrics` gains an `anomalies` parameter — a list of anomaly spec instances. This keeps the mental model simple (a metric = signal + corruptions) and avoids creating a fourth top-level entity type alongside Dimensions, Metrics, and MultiItems.

### PointAnomaly — single class, dual mode

One class with `mode="additive"|"replacement"`. In additive mode, `magnitude` is added to the underlying trend value. In replacement mode, `magnitude` replaces the value entirely. `magnitude` can be a fixed scalar or a `(min, max)` range for uniform sampling.

### ConceptDrift — distribution-level, Gaussian only, gradual onset, multi-segment

Concept drift replaces trend output with draws from a target Gaussian distribution (`target_mean`, `target_std`) during the drift window. Onset is always gradual: over a `transition_window` of N timestamps, values interpolate between the current regime and the target distribution. Each drift segment has an optional `restore` flag that transitions back to the trend-generated baseline after the hold duration. Multiple segments can be sequenced for multi-regime scenarios. Explicit transition matrices and non-Gaussian target distributions are deferred.

### MissingData — NaN injection, three modes

Missing data manifests as `np.nan` in the metric column (not row removal, not sentinel values). Three modes: `"random"` (per-timestamp independent probability), `"burst"` (consecutive blocks of configurable length range), and `"patterned"` (recurring schedule, e.g., time-of-day or day-of-week gaps). For v1, patterned mode supports a callable `is_missing(timestamp) -> bool`; cron-like shorthand is deferred.

### Global seed with dedicated RNG module

`DataGen` accepts a `seed` parameter that initializes a `SeedableRNG` wrapping `numpy.random.Generator` (PCG64). This RNG is passed through the generation pipeline to all trends, anomaly specs, and missing data samplers. Existing trend classes are refactored to accept an optional `rng` parameter in `generate()` — when not provided, they fall back to the global `np.random` for backward compatibility.

### HolidayTrend — optional `holidays` library, pre/post linear ramps

`HolidayTrend` uses the `holidays` Python library when installed, falling back to a user-provided list of date strings. Holiday effects ramp linearly: starting at 0 at `t_holiday - pre_window` days, peaking at full `effect` on the holiday itself, returning to 0 at `t_holiday + post_window` days. Non-linear ramp shapes are deferred.

### ARNoiseTrend — numpy-only, explicit or auto coefficients

Pure numpy implementation: `value[t] = sum(coefficients[i] * value[t-i-1]) + N(0, noise_std)`. Users provide explicit `coefficients` or a `decay` parameter that auto-generates stable coefficients (roots inside the unit circle). No `statsmodels` dependency.

### MarkovTrend — discrete states, stickiness for CLI

Finite discrete states with a `stickiness` parameter (probability of remaining in current state) for CLI shorthand. The full N×N `transition_matrix` is available in the Python API. State transitions are sampled at each timestamp; the trend outputs the corresponding `state_value` plus optional Gaussian noise.

### CLI: separate `--anomalies` flag

A new `--anomalies` flag (repeatable) accepts anomaly specs keyed by metric name: `--anomalies "sales:PointAnomaly(prob=0.01,magnitude=5)+MissingData(prob=0.02)"`. For concept drifts, each flag specifies one drift segment; sequences are built by repeating the flag. A new `--seed` flag sets the global seed. The existing `--mets` flag is unchanged.

### Optional dependency extras

`pyproject.toml` gains `[holidays]` (the `holidays` library) and `[all]` (includes both `[imputer]` and `[holidays]`).

### Module structure

New modules: `random.py` (SeedableRNG), `anomalies/` package with `base.py` (abstract Anomaly), `point.py` (PointAnomaly), `drift.py` (ConceptDrift and DriftSegment), `missing.py` (MissingData). Modified modules: `trends.py` (HolidayTrend, ARNoiseTrend, MarkovTrend), `models.py` (Metrics gains anomalies field), `data_gen.py` (seed parameter, add_metric signature change), `dataframe_builder.py` (RNG threading), `cli.py` (--anomalies and --seed flags), `pyproject.toml` (new extras).

## Testing Decisions

### What makes a good test

Tests assert external behavior, not implementation details. The hybrid approach: seeded deterministic assertions verify exact outputs when RNG is controlled (number of NaNs injected, specific anomaly indices), while statistical tolerance assertions verify distributional properties (drift window mean approximates target mean, point anomaly rate is within confidence bounds). All tests must pass with a fixed seed for reproducibility.

### Modules tested

All new and modified modules: `random.py`, `anomalies/base.py`, `anomalies/point.py`, `anomalies/drift.py`, `anomalies/missing.py`, `trends.py` (new trends), `models.py` (Metrics with anomalies), `data_gen.py` (seed propagation, pipeline ordering), `cli.py` (new flags), `dataframe_builder.py` (RNG threading).

### Prior art

Existing tests in `tests/test_generator.py` and `tests/test_aggregation.py` follow the pattern of constructing a `DataGen` instance, calling generation methods, and asserting on the resulting DataFrame shape and content. The imputer tests in `tests/test_schema_converter.py` demonstrate how the codebase handles optional-dependency-gated features. The CLI tests in `tests/test_cli.py` use Click's `CliRunner` for integration-level assertions on command output.

## Out of Scope

- Non-Gaussian target distributions for concept drift
- Non-linear ramp shapes for holiday trend (linear only)
- Continuous-state Markov processes
- Parameter-level concept drift (changing trend internals)
- Cron-like shorthand for patterned missing data (callable only)
- Full ARIMA/seasonal ARIMA (requires statsmodels)
- Multi-item anomaly support (anomalies attach to singular metrics only)
- Anomaly injection into dimension columns

## Further Notes

The existing `WeekendTrend` shares conceptual DNA with `HolidayTrend`. Consider whether to refactor them under a common `CalendarEffectTrend` base class later — not required for v1.

The `holidays` library only needs to be imported lazily inside `HolidayTrend.generate()` so that the import error surfaces at runtime rather than at package import time, matching how the imputer gates its `scipy` dependency.

When exposing the `--anomalies` flag in CLI, ensure the help text shows complete examples for all three anomaly types, since the shorthand syntax is the primary discovery mechanism for CLI-first users.
