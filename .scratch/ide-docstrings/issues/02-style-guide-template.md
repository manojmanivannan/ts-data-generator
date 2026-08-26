# 02 — Style guide template (docs/docstrings.md)

Type: prototype
Status: resolved
Claimed by: claude
Blocked by: —

## Question

What is the canonical docstring template this project adopts? Draft `docs/docstrings.md` defining:

- **Section structure** — one-line summary, extended description, `Args`, `Returns`, `Raises`,
  `Example` (Google style; matches what already exists on the flagship methods).
- **When an `Example` is required vs optional** — required on the core flow (Q3=c/Q6=b:
  `DataGen` construct → `add_dimension`/`add_metric` → `.data`/`aggregate` + trend composition),
  optional/illustrative on the long tail.
- **Doctest vs illustrative convention** — `>>>` doctests (run in CI) for the core, plain `::`
  blocks elsewhere; how imports are handled in doctests (see 04's namespace decision).
- **Property convention** — document the getter; note setter behavior in the description.
- **Module-level docstring** convention for each public module.
- **Type-hint / `@overload` convention** (Q8=c) — when an overload earns a docstring, how the
  public overload is documented vs the impl.

Include **2–3 worked examples** to react to: a flagship method (`add_dimension` or `aggregate`),
a read/write property (`granularity`), and a standalone function (`random_choice`). "How should it
look" is the key question → prototype ticket. Link the draft as an asset from this ticket.

## Answer

**Asset (prototype, throwaway):** [`docs/docstrings.md`](../../../docs/docstrings.md) on branch
`prototype/02-style-guide` (commit `63253b4`). Clearly marked DRAFT at the top — not ratified; it
is the artifact to react to, not the final guide.

**What the draft settles (the proposed standard):**

1. **Section structure** — Google indented form; one-line summary mandatory on every public symbol;
  extended description mandatory on core flow, recommended elsewhere; `Returns` mandatory on
  non-`None` returns, omitted on `-> None`; `Raises` only for exceptions the symbol *itself* raises
  on documented failure modes (not transitive), with the `aggregate`-re-raises-`AggregationError`
  exception called out.
2. **`Example` required vs optional** — table mapping the core generate-and-read flow + trend
  composition + all 8 trends + 6 carriers to *required runnable `>>>` doctests*; properties and
  long-tail methods to *optional illustrative* (`::` blocks). An unrun `>>>` is a broken promise —
  don't write one unless CI runs it.
3. **Doctest convention** — imports live *in the example* (real `from ts_data_generator import …`
  the user types), with the `conftest` namespace (ticket 04) injecting `pd` + package root;
  every doctest passes `seed=`/`rng=` and asserts on shape/type/membership/rounded scalar, never on
  a random value or a full DataFrame print. Trend-composition doctests assert on frame structure.
4. **Property convention** — getter docstring is the hover for both get and set; describes the value
  *and* the assign-time side effect (regeneration, validation); setters carry no docstring (ruff `D`
  ignores them — ticket 03).
5. **Module-level docstring** — one-line summary + 1–3 sentences naming the public symbols a user
  imports; per-module guidance for `data_gen`, `utils/functions`, `utils/trends`, `anomalies`,
  `schema`; `_*` modules skip it.
6. **`@overload` convention** — overload only when it changes IDE hover in a way one union signature
  cannot (return type narrowed by input); the *public-facing* docstring lives on the real body (the
  one ruff `D` lints); impl `@overload` stubs get a one-liner or none; default to a single union
  signature to avoid two-signature maintenance.

**Worked examples (drawn from real source, all verified runnable & deterministic):**
`DataGen.add_dimension` (flagship method), `DataGen.granularity` (read/write property), and
`random_choice` (standalone function). Verified by execution: `carrier.domain == ['a','b','c']`,
`dg.granularity` round-trips `'5min'`→`'h'`, `df.shape[0] > 0`.

**Faithfulness corrections caught while prototyping** (facts the execution phase must respect):
- `Granularity` is **not** exported from the top-level package (`__all__ = ["DataGen","__version__"]`);
  import it from `ts_data_generator.schema`. Doctests must show this real path.
- `add_metric` takes `trends: list[Trends] | set[Trends]`, **not** a `baseline=` kwarg. A flat
  deterministic baseline is `LinearTrend(offset=100.0, slope=0)` (noise_level defaults to 0).

**Open questions left for the user (grilling, before ratification):**

1. **Namespace vs explicit imports (§3)** — keep explicit per-example imports *and* the `conftest`
  namespace (current draft), or rely on the namespace alone and drop the boilerplate for brevity?
  Overlaps ticket 04's namespace decision.
2. **Doctest scope for trends/carriers (§2)** — does each of the 8 trends + 6 carriers get its own
  runnable CI doctest, or is one combined trend-composition doctest enough with the rest
  illustrative? This sets the size of ticket 04's CI doctest scope.
3. **`Returns` on `-> None`** — confirm we omit the section entirely (draft) rather than
  `Returns: None`.
4. **Package `__init__` docstrings** — one module docstring on `schema/__init__.py` and
  `anomalies/__init__.py` only, or one per public submodule too?

These four are grilling questions for the user; resolving them is the gate between this prototype
and ratification. Once answered, the draft lands on `main` and ticket 03 wires ruff `D` against it.

### Resolution (user signed off — all four recommended choices ratified)

1. **Doctest imports** = explicit per-example imports *and* the `conftest` namespace (inject `pd` +
   package root). Examples read correctly standalone and in the IDE hover. → Constrains ticket 04's
   namespace mechanism.
2. **Doctest scope** = one combined trend-composition doctest (`SinusoidalTrend`/`LinearTrend` +
   `random_choice` → `add_metric`) runs in CI; the other 7 trends and 5 carriers get illustrative
   `::` blocks. → Sets ticket 04's CI doctest scope (small: core flow + one trend-composition).
3. **`Returns` on `-> None`** = omit the section entirely; the annotation communicates None.
4. **Package docstrings** = one module docstring on the package `__init__.py` naming exported
   symbols; no extra per-submodule docstrings. → Constrains ticket 03's `D`-rule scoping (the
   `__init__.py` files need `D100`, submodules' module docstrings are not separately required).

The draft on `prototype/02-style-guide` (commit `e0adf0c`) is the ratified primary-source artifact.
It lands on `main` when the pilot (07) folds it in; until then 03/04/05 cite this branch.