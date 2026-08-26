# 01 — Public-symbol inventory

Type: research
Status: resolved
Blocked by: —

## Question

What is the exact set of in-scope public symbols (per the destination's scope = everything a user
touches in the IDE)? Enumerate, grouped by module:

- `DataGen` — every public method + read/write property (`add_dimension`, `add_metric`,
  `add_multi_items`, `aggregate`, `normalize`, `denormalize`, `plot`, `to_granularity`,
  `head`, `tail`, `shape`, `data`, `granularity`, `start_datetime`/`end_datetime`, `dimensions`,
  `metrics`, `multi_items`, `trends`, `baselines`, `expand_dimensions`, `scale_variance`, …).
- `utils.trends` — `Trend` base + subclasses (`SinusoidalTrend`, `LinearTrend`, `ARNoiseTrend`,
  `MarkovTrend`, …) that users compose into metrics.
- `utils.functions` — carrier helpers users pass to `add_dimension`:
  `random_choice`, `ordered_choice`, `constant`, `random_int`, `random_float`, `auto_generate_name`.
- `anomalies` — `PointAnomaly`, `MissingData`, `ConceptDrift`, and the `Anomaly` base users subclass.
- `schema` — user-facing types (the converter/imputer entry points).
- Pre-built factory types passed to `DataGen.__init__`: `Dimensions`, `Metrics`, `MultiItems`
  (users construct these directly when not using the `add_*` helpers).

For **each** symbol record three states in a checklist table grouped by module:

1. **Docstring** — none / one-liner / full (has `Args`·`Returns`·`Raises`).
2. **Example** — present (and is it a runnable `>>>` doctest) / absent.
3. **Type hints** — fully annotated / missing return type / candidate for `@overload`.

This table is the scope + tracking artifact the execution phase works through. **Exclude `_*`
internals.** Resolve by calling the `research` skill; capture findings on a throwaway
`research/01-public-symbol-inventory` branch and leave a context pointer below.

## Answer

Resolved inline (research subagents were unreachable in this session — both the Explore and a
general-purpose/sonnet agent failed with model-access errors; the grilling skill puts fact-finding
on the agent, so the inventory was gathered directly from `src/ts_data_generator/`).

Findings: [research/01-public-symbol-inventory.md](../research/01-public-symbol-inventory.md) —
full per-symbol table grouped by module.

**Headline:** ~58 public symbols inventoried. Type hints are already strong (modern `|` unions +
return types everywhere; only 2 `@overload` candidates: `DataGen.__init__` and `Dimensions.__init__`).
The real gap is *descriptive*: ~22 one-liners + ~7 missing docstrings on `DataGen` (notably `.data`),
zero Examples on the 4 core methods (`add_dimension`/`add_metric`/`add_multi_items`/`aggregate`) and
on all 8 trend classes + 6 function helpers, and existing `>>>` examples (anomalies, schema) are not
run in CI. This confirms the destination's emphasis on descriptions + examples over type work.