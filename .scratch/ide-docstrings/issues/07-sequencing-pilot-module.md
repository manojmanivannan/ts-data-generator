# 07 — Execution sequencing & pilot module

Type: grilling
Status: resolved
Claimed by: claude
Blocked by: 02, 03, 04, 06

## Question

In what order does the bulk docstring + type-hint writing proceed, and which module is the
**pilot** that validates the full stack (style guide 02 + doctest CI 04 + ruff `D` 03 + slimmed
`api.md` 05 + typing strategy 06) end-to-end before rolling out?

- **Recommended pilot:** `data_gen.py` (`DataGen`) — the flagship class, the one users hover most,
  and the doctest core flow lives here, so it exercises every part of the stack.
- **Proposed sequence for the rest:** `utils.trends` → `utils.functions` → `anomalies` → `schema`
  → pre-built factory types (`Dimensions`/`Metrics`/`MultiItems`).
- **Batch size** — one module per PR, or group the smaller ones (`utils.functions` + `anomalies`)?

HITL — the user picks the pilot and batch cadence. Resolving this graduates the
"module-by-module writing" fog (map's Not-yet-specified) into a concrete sequenced worklist, which
is the hand-off point: the map is done, the "do" begins.

## Answer

Resolved in one grilling round (all four recommendations accepted). Two facts surfaced during
charting that reshaped the ticket's proposed plan before the decision:

- **Pilot must be a doctest-core module.** 04's `testpaths` scope doctest collection to
  `data_gen`, `utils.trends`, `utils.functions` only. A pilot outside that set would validate the
  style guide + ruff `D` + typing but *not* the doctest CI harness — so it wouldn't be a full-stack
  check. Candidates: `data_gen`, `trends`, `functions`.
- **The worklist is class/method-dominated, not function-dominated.** The red baseline is **143 D
  violations** (map's "~114" is slightly stale), of which **~90 are class/method-style** (61× D102
  public methods, 19× D107 `__init__`, 10× D105 magic methods) vs. only 1× D101/D103 class/function.
  So the pilot must exercise the class/method/property template, not just function docstrings.
- **Two coverage gaps in the ticket's proposed sequence, now fixed:**
  1. *"schema"* and *"pre-built factory types (Dimensions/Metrics/MultiItems)"* are the **same
     module** (`schema/models.py`) — the sequence double-counted it. Collapsed to one slot.
  2. Two D-enforced gray modules were **omitted**: `carriers.py` (13 D:
     `DimensionCarrier`/`DomainCarrier`/`NonExpandableCarrier`) and `analyzers/converter.py` (6 D:
     `SchemaConverter`). Added as a final batched slot.

### The sequenced do-phase worklist (the hand-off)

Each step = docstrings (clearing its D violations) + 06 typing edits (tighten returns, `DimensionFunction`
alias where it applies; zero `@overload`s) bundled, per 06's "typing folds into the per-module
worklist." Doctest-core modules carry a CI-green `Example` (04 harness).

1. **Pilot — `data_gen.py` (26 D, 1001 lines) [individual PR].** The flagship `DataGen` class —
   methods, `__init__`, properties, magic methods — plus the core generate-and-read `Example` doctest
   (CI-green). Typing: tighten loose returns. **This PR also folds `prototype/02-style-guide` →
   `main`**, carrying the 02 style guide (`docs/docstrings.md`), 03 ruff `D` config, and 04 doctest
   harness — landing the full config stack in one validated unit. Produces the `DataGen` summary lines
   for 05's `api.md` table (the table itself stays deferred to the trailing step). *Why data_gen, not
   the cheaper `functions`: ~63% of the work is class/method-style and only `data_gen` exercises that
   pattern + the doctest harness; a `functions` pilot would silently skip the dominant template.*

2. **`utils/trends.py` (51 D) [individual PR].** Trend classes + the trend-composition doctest
   (`SinusoidalTrend` + `random_choice`, CI-green). The single biggest workload, but deferred from
   pilot because it's a narrower class pattern than `DataGen` and a poor first validation. Doctest-core
   → individual PR. `data_gen`'s docs already cross-reference `Trends`, so this closes the pilot's own
   references early.

3. **`utils/functions.py` (6 D) [individual PR].** Functions + the `constant`-style doctest. Finishes
   the doctest-core trio. Doctest-core → individual PR.

4. **`anomalies/*` — `base` (1) + `point` (6) + `drift` (6) + `missing` (9) = 22 D [one batched PR].**
   Self-contained, not doctest-core → batched. Typing tightening.

5. **`schema/models.py` (19 D) [individual PR].** The factory types `Dimensions`/`Metrics`/`MultiItems`
   — the D102 getter bulk. Class+method heavy, central. Typing: applies the `DimensionFunction` alias
   (06); the latent `list`-acceptance on the `Dimensions` setter is a flagged cleanup handled here
   *as a cleanup, not a type widening* (per 06). This is the collapsed "schema" + "factory types" slot.

6. **Gray modules — `carriers.py` (13 D) + `analyzers/converter.py` (6 D) = 19 D [one batched PR].**
   Not doctest-core → batched. The two modules the ticket's proposed sequence dropped.

**Trailing step (not a PR in the sequence — 05's deferred execution):** `api.md` structural slim +
summary-table population. The `DataGen` summary lines come from the pilot; per-method lines come from
the bulk. Lands at the do-phase end, after the bulk produces the lines to copy (inventing them
earlier re-introduces drift, per 05).

**Batch cadence:** doctest-core modules = individual PRs (each carries a CI doctest that must go
green); `anomalies` and the gray pair = batched PRs; `schema/models` = its own PR. **~6 PRs** for the
do-phase, plus the trailing `api.md` slim.

### Implication for the map

This resolution **graduates three Not-yet-specified fog patches** — the non-pilot docstring writing,
the non-pilot type-hint tightening, and the `api.md` structural slim — into the concrete worklist
above (the hand-off). They are execution, not decisions, so they live as this worklist, not as new
decision tickets (the destination carries execution into the map *only* via this pilot ticket). The
optional "promote anomaly `>>>` blocks to CI doctests" fog stays — it's outside the core-flow CI
scope and remains a maybe. **08 (wire `ruff check` into CI) is now unblocked** — the last open
decision ticket on the route (the "enforcement" criterion of the destination); its activation-timing
decision (advisory-now vs. required-after-surface) interacts with when this worklist drives the
surface green. The map is one ticket from done.