# Research 01 — Public-symbol inventory

Findings for [01 — Public-symbol inventory](../issues/01-public-symbol-inventory.md).
Scope = everything a user touches in the IDE (Q2=b). `_*` internals excluded.

Legend — Docstring: `✓full` (Args·Returns·Raises) · `~one-liner` · `✗none`.
Example: `✓>>>` runnable doctest · `~ill` illustrative only · `✗` absent.
Types: `✓` annotated · `?ret` missing return · `OL` @overload candidate.

## data_gen.py — `DataGen`

| Symbol | Docstring | Example | Types |
|---|---|---|---|
| `DataGen` (class) | ✓full (summary+Args+Example) | ✓>>> | ✓; `__init__` **OL** (lists vs `add_*`) |
| `.data` (property) | ✗none | ✗ | ✓ |
| `.shape` (property) | ~one-liner | ✗ | ✓ |
| `.head(n)` | ~one-liner | ✗ | ✓ |
| `.tail(n)` | ~one-liner | ✗ | ✓ |
| `.to_granularity` | ~one-liner | ✗ | ✓ |
| `.granularity` get/set | ~one-liner | ✗ | ✓ |
| `.start_datetime` / `.end_datetime` get/set | ✗none | ✗ | ✓ |
| `.expand_dimensions` get/set | ~one-liner | ✗ | ✓ |
| `.scale_variance` get/set | ~one-liner | ✗ | ✓ |
| `.dimensions` / `.metrics` / `.multi_items` / `.trends` / `.baselines` (properties) | ~one-liner | ✗ | ✓ |
| `.add_dimension` | ✓full (Args·Raises) | ✗ | ✓ |
| `.update_dimension` | ~one-liner | ✗ | ✓ |
| `.remove_dimension` | ~one-liner | ✗ | ✓ |
| `.add_metric` | ✓full (Args·Raises) | ✗ | ✓ |
| `.remove_metric` | ~one-liner | ✗ | ✓ |
| `.add_multi_items` | ✓full (Args·Raises) | ✗ | ✓ |
| `.remove_multi_item` | ~one-liner | ✗ | ✓ |
| `.aggregate` | ✓full (Args·Returns·Raises) | ✗ | ✓ |
| `.normalize` | ~one-liner | ✗ | ✓ |
| `.denormalize` | ~one-liner | ✗ | ✓ |
| `.plot` | ~one-liner | ✗ | ✓ |
| `.state` / `__repr__` / `__len__` | ✗none/dunder | ✗ | ✓ |

## utils/trends.py — trend classes (users compose into metrics)

| Symbol | Docstring | Example | Types |
|---|---|---|---|
| `Trends` (ABC) + `.name`/`.generate` | ✓full (Args·Returns) | ✗ | ✓ |
| `SinusoidalTrend` (+ props amplitude/freq/phase/noise_level) | ✓full (Args·Returns) | ✗ | ✓ |
| `LinearTrend` (+ props slope/offset/noise_level) | ✓full | ✗ | ✓ |
| `WeekendTrend` (+ props) | ✓full | ✗ | ✓ |
| `HolidayTrend` (+ props) | ✓full | ✗ | ✓ |
| `ARNoiseTrend` (+ props) | ✓full | ✗ | ✓ |
| `MarkovTrend` (+ props) | ✓full (summary+extended) | ✗ | ✓ |
| `StockTrend` (+ props) | ✓full (Args) | ✗ | ✓ |

## utils/functions.py — carrier helpers (passed to `add_dimension`)

| Symbol | Docstring | Example | Types |
|---|---|---|---|
| `constant` | ✓full (Args·Returns) | ✗ | ✓ |
| `random_choice` | ✓full | ✗ | ✓ |
| `random_int` | ✓full | ✗ | ✓ |
| `random_float` | ✓full | ✗ | ✓ |
| `ordered_choice` | ✓full | ✗ | ✓ |
| `auto_generate_name` | ✓full | ✗ | ✓ |

## anomalies/ — injectable anomalies (users construct/subclass)

| Symbol | Docstring | Example | Types |
|---|---|---|---|
| `Anomaly` (ABC) `.generate` | ✓full (Args·Returns) | ✗ | ✓ |
| `PointAnomaly` | ✓full (Args) | ~ill (>>>) | ✓ |
| `MissingData` | ✓full (Args) | ~ill (>>>) | ✓ |
| `ConceptDrift` (+ `DriftSegment`) | ✓full (Args) | ~ill (>>>) | ✓ |

## schema/models.py — enums + pre-built factory types (passed to `DataGen.__init__`)

| Symbol | Docstring | Example | Types |
|---|---|---|---|
| `Granularity` (enum) + `order`/`coarser_than`/`finer_than`/`resample_alias` | ~one-liner | ✗ | ✓ |
| `AggregationType` (enum) | ~one-liner | ✗ | ✓ |
| `Metrics` | ✓full (Args·Example) | ✓>>> | ✓ |
| `Dimensions` | ✓full (Args·Example) | ✓>>> | ✓; constructor **OL** candidate (str|list name) |
| `MultiItems` | ✓full (Args·Example) | ✓>>> | ✓ |

## schema/ — other user-facing

| Symbol | Docstring | Example | Types |
|---|---|---|---|
| `SchemaConverter` (analyzers/converter.py) | ✓full | ✓>>> (already) | ✓ |

## Gaps summary

**Totals:** ~58 public symbols inventoried.

- **No docstring (`✗none`):** ~7 — `DataGen.data`, `start_datetime`/`end_datetime` getters, `state`, `__repr__`/`__len__`, and a couple of dunder/property gaps. Notably `.data` — the most-hovered property — has none.
- **One-liners needing full treatment (`~`):** ~22 — the `DataGen` convenience methods + read/write properties (`head`, `tail`, `shape`, `to_granularity`, `granularity`, `expand_dimensions`, `scale_variance`, `update/remove_*`, `normalize`, `denormalize`, `plot`, the collection properties) + the `Granularity`/`AggregationType` enum methods.
- **Full Args/Raises but NO Example:** 4 core methods — `add_dimension`, `add_metric`, `add_multi_items`, `aggregate`. **These are the Q6=b doctest candidates** (core flow + trend composition).
- **No Examples anywhere on trends (8 classes) or functions (6 helpers)** — they have Args/Returns but users composing them get no copy-pasteable snippet. `random_choice`/`SinusoidalTrend` are exactly the trend-composition doctest targets (Q6=b).
- **Anomalies already have illustrative `>>>` examples** — promotable to CI (the fog item) once 04 wires doctest infra.
- **Type hints:** strong overall — nearly everything annotated with modern `|` unions and return types. **`@overload` candidates: 2** — `DataGen.__init__` (pass pre-built `Dimensions`/`Metrics`/`MultiItems` lists vs build via `add_*`) and `Dimensions.__init__` (`str | list[str]` name). No missing return types found on the public surface.
- **Existing `>>>` examples are NOT run in CI** (no `--doctest-modules`, no doctest namespace) — confirmed rot risk.

## Implication for the map

- The bulk work splits into three shapes: (1) flesh out the ~22 one-liners + ~7 missing on `DataGen`; (2) add Examples to the 4 core methods + the trend/function helpers (doctested per Q6=b); (3) add overloads to 2 constructors (Q8=c).
- `data_gen.py` as pilot (ticket 07's recommendation) exercises shapes (1), (2), and (3) all at once — good validation.