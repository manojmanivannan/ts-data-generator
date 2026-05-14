## Parent PRD

`issues/prd.md` — Problem Statement, Solution, Implementation Decisions (Global seed with dedicated RNG module)

## What to build

Introduce a `SeedableRNG` class in a new `random.py` module that wraps `numpy.random.Generator` (PCG64) and exposes the subset of random operations needed by trends and anomalies: `normal()`, `uniform()`, `choice()`, `random()`. Add a `seed` parameter to `DataGen.__init__` that creates this RNG instance. Thread the RNG through `DataFrameBuilder` to all existing trend classes by adding an optional `rng` parameter to each trend's `generate()` method — when not provided, fall back to global `np.random` for backward compatibility. The RNG reaches `Metrics.generate()` and then each trend's `generate(timestamps, rng=None)`.

## Acceptance criteria

- [ ] `SeedableRNG(seed=42)` produces deterministic sequences; two instances with the same seed yield identical values
- [ ] `DataGen(seed=42)` creates an RNG and stores it
- [ ] All four existing trend classes (`SinusoidalTrend`, `LinearTrend`, `WeekendTrend`, `StockTrend`) accept `rng=None` in `generate()` and use it for all randomness when provided
- [ ] Existing tests pass without modification (backward-compatible default behavior)
- [ ] New tests in `tests/test_random.py` verify seed determinism
- [ ] New tests verify that setting `DataGen(seed=42)` produces identical DataFrames across two runs

## Blocked by

None — can start immediately.

## User stories addressed

- 5. As a user who needs deterministic test datasets, I want to seed the entire generation pipeline so that I get identical output on every run.
