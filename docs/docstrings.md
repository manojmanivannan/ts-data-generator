<!--
Docstring & type-hint style guide for ts-data-generator. Canonical reference ratified in
wayfinder ticket 02 and enforced in CI via scoped ruff D rules (ticket 08 / #70).
-->

# Docstring & type-hint style guide

This is the canonical reference for how every **user-facing** symbol in
`ts_data_generator` is documented and typed. Docstrings are the source of truth
for per-method reference (`docs/api.md` is slimmed to a conceptual guide — see
ticket 05). Vocabulary (dimension, metric, trend, anomaly, multi-item,
granularity, carrier, `expand_dimensions`, baseline) is defined in
[`concepts.md`](concepts.md); use those terms, do not invent synonyms.

**Scope.** Everything a user touches in the IDE: the public surface of
`DataGen`, `utils.trends`, `utils.functions`, `anomalies`, `schema`, and the
pre-built factory types (`Dimensions`, `Metrics`, `MultiItems`). **Internal
`_*` helpers and `_*` modules are out of scope** — they are never linted by the
`D` rules (ticket 03) and need not be documented to this standard.

## 1. Section structure (Google style)

Every public symbol's docstring follows this shape. Sections are omitted when
they have nothing to say — but a public callable without an `Args`/`Returns`
section is almost always a gap, not an omission.

```
"""<One-line summary — imperative mood, fits one IDE hover line, ends with a period.>

<Extended description: 1–4 sentences. Explain *why* the behaviour exists and
the non-obvious mechanics, not a restatement of the signature. Reference the
relevant concept from concepts.md by name.>

Args:
    name: <type-led prose; start with the type's natural article. Wrap at
        col 88. Indent continuation lines by 4 under the param name.>
    another: <If the arg accepts several types, name each and what it means
        for behaviour.>

Returns:
    <Type first, then shape/semantics. For DataFrames name the columns and
    the index.>

Raises:
    ExceptionType: <The precise condition that triggers it. One bullet per
    exception type.>

Example:
    <Runnable `>>>` doctest for the core flow (see §3); plain `::` block
    elsewhere.>
"""
```

Rules:

- **One-line summary is mandatory** on every public symbol (property, method,
  function, class, module). It is what the IDE hover shows first.
- **Extended description** is mandatory on the core flow (§2) and recommended
  elsewhere; omit only for genuinely trivial accessors.
- `Args`, `Returns`, `Raises` use the Google indented form (param name, colon,
  space, description, 4-space continuation indent). **Not** Sphinx `:param:`.
- `Returns` is mandatory on anything non-`None`-returning. `-> None` callables
  omit `Returns`.
- `Raises` lists only exceptions the symbol *itself* raises on documented
  failure modes — not transitive ones from delegates, unless the contract makes
  them part of the surface (e.g. `aggregate` re-raises `AggregationError`).
- `Example` — see §2/§3.

## 2. When an `Example` is required vs optional

| Surface | `Example` required? | Form |
|---|---|---|
| Core generate-and-read flow: `DataGen` construct → `add_dimension`/`add_metric`/`add_multi_items` → `.data` / `aggregate` | **Yes** | runnable `>>>` doctest |
| Trend composition: `SinusoidalTrend` + `random_choice` passed to `add_metric` | **Yes** | runnable `>>>` doctest |
| The 8 trend classes, the 6 `utils.functions` carriers | **Yes** (one each) | runnable `>>>` doctest |
| Read/write properties (`granularity`, `data`, `shape`, …) | Optional — illustrative | `::` block or short `>>>` (see §4) |
| Long-tail methods (`normalize`, `denormalize`, `plot`, `to_granularity`, `head`, `tail`) | Optional — illustrative | `::` block |
| Pre-built factory types (`Dimensions`, `Metrics`, `MultiItems`) | Optional | `::` block |

The core-flow doctests are **run in CI** (ticket 04); everything else is
illustrative and never executed. Do not put a runnable `>>>` block on a symbol
unless you intend CI to run it — an unrun `>>>` reads as a broken promise.

## 3. Doctest vs illustrative convention

**Doctest** (core flow only — the set CI runs, per ticket 04):

```python
Example:
    >>> from ts_data_generator import DataGen
    >>> from ts_data_generator.schema import Granularity
    >>> from ts_data_generator.utils.functions import random_choice
    >>> from ts_data_generator.utils.trends import LinearTrend
    >>> dg = DataGen(
    ...     start_datetime="2024-01-01",
    ...     end_datetime="2024-01-02",
    ...     granularity=Granularity.HOURLY,
    ...     seed=42,
    ... )
    >>> dg.add_dimension("region", random_choice(["north", "south"]))
    >>> dg.add_metric("sales", {LinearTrend(offset=100.0, slope=0)})
    >>> df = dg.data
    >>> df.shape[0] > 0
    True
```

Convention:

- **Imports live in the example, not the module top.** Each doctest is
  self-contained: it shows the real `from ts_data_generator import ...` the
  user types. (The `conftest` doctest namespace from ticket 04 injects `pandas`
  as `pd` and the package root; explicit per-example imports are still written
  so the example reads correctly standalone and in the IDE.)
- **Deterministic.** Every doctest passes `seed=` (or an explicit `rng=`) so
  output is reproducible. Never assert on a random *value* — assert on shape,
  type, membership, or a rounded scalar you have fixed.
- **Assert cheaply.** `df.shape[0] > 0`, `isinstance(...)`, `"x" in df.columns`,
  `round(value, 2) == 1.23`. Avoid printing full DataFrames — column order and
  float formatting drift.
- **Trend composition** doctests build the trend, pass it to `add_metric`, and
  assert on the generated frame's structure, not on trend internals.

**Illustrative** (everything else): a plain reST literal block, *not* executed:

```python
Example:
    Roll two dimensions into a Cartesian product via ``expand_dimensions``::

        dg = DataGen(..., expand_dimensions=True)
        dg.add_dimension("region", random_choice(["north", "south"]))
        dg.add_dimension("product", random_choice(["a", "b"]))
        # .data now has one row per (timestamp x region x product)
```

The `::` opens a literal block; no `>>>` prefixes, no CI execution. Use it when
the example is load-bearing for understanding but not worth a hermetic test.

## 4. Property convention

Read/write properties document the **getter** as the primary docstring; the
setter's behaviour is described in the extended description, not duplicated.

```python
@property
def granularity(self) -> str:
    """Time-step spacing of the generated series, as a string (e.g. ``"5min"``).

    Returns the granularity's string value (the ``Granularity`` enum's
    ``.value``). Assigning to this property re-binds the granularity and
    regenerates the data; pass a ``Granularity`` member or a pandas-style
    offset string (``"h"``, ``"D"``). A string that ``Granularity`` cannot
    parse raises ``ValueError``.

    Example:
        >>> dg = DataGen(start_datetime="2024-01-01",
        ...              end_datetime="2024-01-02", seed=1)
        >>> dg.granularity
        '5min'
        >>> dg.granularity = "h"
        >>> dg.granularity
        'h'
    """
```

Rules:

- The property docstring is what the IDE shows on hover for both get and set —
  describe the value *and* the assign-time side effect (regeneration, validation).
- Type the getter's return annotation (`-> str`), not `-> Any`.
- Read-only properties (`data`, `shape`, `head`/`tail` are methods) describe
  only the value; `data` documents the returned DataFrame's columns and index
  in `Returns`.
- Setters carry no docstring of their own (ruff `D` ignores them — ticket 03).

## 5. Module-level docstring

Every public module opens with a module docstring:

```python
"""<One-line summary of what the module provides to users.>

<1–3 sentences on how the pieces relate and where the user enters. Name the
public symbols a user imports from this module.>
"""
```

- `data_gen.py` → names `DataGen` and the entry-point flow.
- `utils/functions.py` → names the carrier helpers and the CLI-shorthand link.
- `utils/trends.py` → names `Trend` + subclasses and the composition model.
- `anomalies/` → names the `Anomaly` base + built-ins.
- `schema/` → names the user-facing types and the converter/imputer entry points.

Internal `_*` modules skip this (out of scope).

## 6. Type-hint & `@overload` convention

Type hints are already strong across the surface (modern `|` unions, return
types present). The audit (ticket 06) tightens the remaining cases; this guide
fixes the *convention*:

- **Annotate everything public**, including return types. No bare `-> Any` on
  the public surface unless the value is genuinely dynamically typed — then
  explain why in `Returns`.
- **`@overload` earns its place only when it changes what the IDE hover shows
  in a way a single union signature cannot.** Overloads are maintenance cost:
  two signatures must be kept in sync. Default to one union signature.
- **The public overload carries the docstring**; impl overloads (`@overload`
  variants and the real body) get a one-line private docstring or none, per
  ticket 06's decision. Example shape:

  ```python
  @overload
  def __init__(self, *, dimensions: list[Dimensions], ...) -> None: ...
  @overload
  def __init__(self, *, start_datetime: str, ...) -> None: ...
  def __init__(self, dimensions=None, ..., ) -> None:
      """<full Google docstring on the real body — the one ruff D lints.>"""
  ```
- **Union tightening:** prefer a single `X | Y` signature over an overload when
  the return type and behaviour are the same regardless of which branch. Split
  into overloads only when the return type *narrowed by input* differs (that is
  what makes hover better).

## Worked examples

The three examples below are the reference shapes the execution phase (ticket
07 pilot) copies. They are drawn from the real source so they are faithful.

### Flagship method — `DataGen.add_dimension`

```python
def add_dimension(
    self,
    name: str,
    function: int | float | str | list[Any] | dict[Any, float] | Generator[Any, None, None],
    domain: list[Any] | None = None,
    expand: bool | None = None,
    weights: dict[Any, float] | None = None,
) -> None:
    """Add a new dimension column.

    ``function`` is stored as a domain-carrying carrier so the
    ``expand_dimensions`` path can read its value domain with no generator
    introspection. Scalars and static lists are converted to carriers at
    construction; a ``{value: weight}`` dict becomes a weighted carrier.

    Args:
        name: Unique column name for the dimension.
        function: An infinite generator (carrier or plain), a static value
            (int, float, str, list), or a dict of ``{value: weight}`` which is
            converted to a carrier with explicit weights.
        domain: Explicit value domain for an opaque custom/pre-built generator
            whose domain the engine cannot see structurally (the ``domain=``
            escape hatch). Cannot be supplied to a carrier that already carries
            a domain, and cannot override the non-expandable range / auto-name
            rejection.
        expand: Per-dimension override for ``expand_dimensions``. ``None``
            (default) inherits the global flag; ``True`` forces this dimension
            into the Cartesian product even when the global flag is off;
            ``False`` opts it out — it regenerates one value per timestamp
            within each series instead.
        weights: Optional mapping of dimension values to scale multipliers for
            multivariate dimension expansion.

    Raises:
        DimensionError: If a dimension with this name already exists.
        ValidationError: If ``function`` is not a supported type, or ``domain=``
            is misused (supplied to a carrier, or to a non-expandable range /
            auto-name generator).

    Example:
        >>> from ts_data_generator import DataGen
        >>> from ts_data_generator.utils.functions import random_choice
        >>> dg = DataGen(start_datetime="2024-01-01",
        ...              end_datetime="2024-01-02", seed=0)
        >>> dg.add_dimension("region", random_choice(["north", "south"]))
        >>> "region" in dg.data.columns
        True
    """
```

### Read/write property — `DataGen.granularity`

See §4 (the `granularity` example *is* the worked example for properties).

### Standalone function — `random_choice`

```python
def random_choice(
    iterable: Iterable[T], rng: RNGProtocol | None = None,
) -> DimensionCarrier[T]:
    """Yield a random element from the iterable at each time step.

    The carrier's ``.domain`` is the iterable's distinct values and
    ``.expandable`` is ``True``, so a dimension built from it participates in
    ``expand_dimensions`` without generator introspection.

    Args:
        iterable: The collection to choose from.
        rng: Optional RNG for deterministic generation. When omitted, the
            process-global ``random`` is used (non-deterministic).

    Returns:
        A :class:`~ts_data_generator.carriers.DimensionCarrier` whose ``.domain``
        is the sorted-distinct elements and ``.expandable`` is ``True``;
        ``next()`` yields a random element.

    Example:
        >>> from ts_data_generator.utils.functions import random_choice
        >>> carrier = random_choice(["a", "b", "c"])
        >>> carrier.domain
        ['a', 'b', 'c']
        >>> next(carrier) in {"a", "b", "c"}
        True
    """
```

---

**Ratified decisions (ticket 02, signed off by the user):**

1. **Doctest imports** — keep explicit per-example imports *and* the `conftest`
   namespace (inject `pd` + package root). Examples read correctly standalone
   and in the IDE hover.
2. **Doctest scope** — one combined trend-composition doctest
   (`SinusoidalTrend`/`LinearTrend` + `random_choice` → `add_metric`) runs in
   CI; the other 7 trends and 5 carriers get illustrative `::` blocks. Sets
   ticket 04's CI doctest scope.
3. **`Returns` on `-> None`** — omit the section entirely; the annotation
   communicates None.
4. **Package docstrings** — one module docstring on the package `__init__.py`
   (naming exported symbols); no per-submodule docstrings beyond what each
   public symbol already carries.