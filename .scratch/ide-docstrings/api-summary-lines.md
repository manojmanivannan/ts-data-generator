# DataGen summary lines for the `api.md` table (handoff → #69)

Hand-off artifact from pilot #63. One-line-per-symbol gists for the `DataGen`
public surface, **copied from the finalized `data_gen.py` docstring summary
lines** (extracted via AST so they cannot drift from the source). #69 populates
the `api.md` summary table from these; the table itself stays deferred to that
trailing slim (per #05/#63).

Convention (from #05): the table is `DataGen`-only (methods + properties),
grouped by workflow stage. Each row's method name links to the source file on
GitHub as a **path-only blob URL, no line numbers** (line numbers drift on
every docstring edit; file paths rarely move). Every `DataGen` row shares one
target — `src/ts_data_generator/data_gen.py` — so it is one per-file link
repeated, hand-maintained, near-zero drift.

Symbols without a docstring summary are marked `[crafted]` — they are either a
plain attribute (`.data`, no docstring by design) or a dunder (D105-ignored per
style guide §1, no docstring). Their one-liners are written here from behavior,
not copied from a docstring.

## Class

| symbol | summary |
|---|---|
| `DataGen` | Generate synthetic time series data with dimensions, metrics, and trends. |

## Properties — knobs & read-outs

| symbol | summary |
|---|---|
| `data` | [crafted] The generated, timestamp-indexed DataFrame; regenerated whenever configuration changes. |
| `state` | Current pipeline state: `CONFIGURED` → `GENERATED` → `NORMALIZED`. |
| `granularity` | Time-step spacing of the generated series, as a string (e.g. `"5min"`). |
| `expand_dimensions` | Whether per-combination Cartesian-product expansion is enabled. |
| `scale_variance` | Std. dev. of the log-normal factor scaling metric slices across combinations. |
| `start_datetime` | Start bound of the generated time range. |
| `end_datetime` | End bound of the generated time range. |
| `dimensions` | Mapping of dimension name to `Dimensions` instance. |
| `metrics` | Mapping of metric name to `Metrics` instance. |
| `multi_items` | Mapping of comma-joined names to `MultiItems` instance. |
| `trends` | Nested mapping: `{metric_name: {trend_name: trend_instance}}`. |
| `baselines` | Clean (anomaly-free) baseline `DataFrame`s keyed by metric name. |

## Configure — methods

| symbol | summary |
|---|---|
| `to_granularity` | Set the data granularity. |
| `add_dimension` | Add a new dimension column. |
| `update_dimension` | Update an existing dimension's generator function. |
| `remove_dimension` | Remove a dimension and its column from the data. |
| `add_metric` | Add a new metric column composed of one or more trends. |
| `remove_metric` | Remove a metric and its column from the data. |
| `add_multi_items` | Add a group of linked columns generated from a single function. |
| `remove_multi_item` | Remove a multi-item group and its columns. |

## Retrieve / transform / visualize — methods

| symbol | summary |
|---|---|
| `shape` | Return the (rows, columns) shape of the generated data. |
| `head` | Return the first *n* rows of generated data. |
| `tail` | Return the last *n* rows of generated data. |
| `aggregate` | Aggregate data to a coarser granularity. |
| `normalize` | Apply normalization to numeric columns in place. |
| `denormalize` | Reverse the last normalization in place. |
| `plot` | Plot numeric columns using matplotlib. |

## Dunders (user-facing)

| symbol | summary |
|---|---|
| `__len__` | [crafted] Number of rows in the generated data. |
| `__repr__` | [crafted] Debug representation listing configured dimensions, metrics, and multi-items. |