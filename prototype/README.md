# PROTOTYPE (throwaway) — expand_dimensions core mechanics

> Throwaway. Lives on branch `prototype/expand-dimensions-48`, off main.
> Answers ticket #48. Not production code.

## Run

```
uv run python prototype/run.py
```

Keystrokes: `[1]` expand · `[2]` aggregation · `[3]` anomaly · `[4]` determinism · `[5]` error case · `[q]` quit.

## Question

Does a global `expand_dimensions` flag work as designed — one row per
(timestamp × Cartesian product of all explicit-list dimensions' distinct
values), each combination carrying its own independently-regenerated,
reproducible metric series — and do aggregation and the auto-emit
`<metric>_anomaly` column fall out correctly per series?

## What it exercises (against the REAL DataGen pipeline)

- **`expand_logic.py`** — the pure, liftable logic: domain recovery +
  validation, per-combination deterministic seeding, Cartesian-product
  expansion, timestamp-first row ordering. This is the bit worth keeping.
- **`run.py`** — the throwaway TUI shell over it, driving real `Dimensions`,
  `Metrics`, trends, `PointAnomaly`, and `aggregate_dataframe`.

### Domain recovery / validation

A dimension's expandable domain is recovered exactly when its generator is
introspectable via `gi_code.co_qualname` + frame locals
(`random_choice` / `ordered_choice` / `constant`); opaque generators
(`itertools.cycle` wrapping a static list) fall back to **sampling with a
cap**. `random_int` / `random_float` are rejected outright (range generators —
enumerating ranges risks silent row-count explosion), even when the range is
small.

> ⚠ Open design point surfaced for the production feature: the sampling
> fallback for opaque generators is heuristic. The real implementation should
> decide between (a) requiring an explicit domain declaration, (b) the
> introspection path only, or (c) the sampling-with-cap approach. See the
> resolution on #48.