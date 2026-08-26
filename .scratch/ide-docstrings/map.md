# Wayfinder Map — IDE-friendly docstrings & type hints for ts-data-generator

## Destination

Every user-facing symbol in ts-data-generator gives a useful answer in the IDE: a Google-style
docstring (one-line summary + extended description + `Args`/`Returns`/`Raises` + a runnable
`Example` on the core flow), complete and tightened type hints with `@overload` where it improves
hover, and a written style guide that CI enforces via scoped ruff `D` rules. The core
generate-and-trend-composition flow is doctested in CI, and `docs/api.md` is slimmed to a
conceptual guide so it no longer drifts from the canonical docstrings.

The map is **done** when the standard, scope, enforcement, typing strategy, and sequencing are all
decided — leaving only the mechanical per-module docstring/typing writing (the "do" phase that
follows, sequenced by ticket 07). This effort carries execution into the map *only* via the pilot
ticket (07); every other ticket resolves a decision.

## Notes

- **Domain:** synthetic time-series generation. Vocabulary (dimension, metric, trend, anomaly,
  multi-item, granularity, carrier, `expand_dimensions`, baseline) lives in `docs/concepts.md` —
  consult it before naming things in docstrings.
- **Tracker:** local-markdown (this `.scratch/ide-docstrings/` directory). Frontier = open,
  unblocked, unclaimed tickets in `issues/`, first by number.
- **Toolchain:** linter = ruff (`E,W,F,I,B,UP,D` — `D` added by ticket 03, scoped to the public
  surface via `per-file-ignores`; red-baseline until 07+ writes the docstrings); runner = pytest
  (`-ra -q`, `--doctest-modules` on the 3 core modules, wired by 04). Docstring style = Google.
  **CI ruff gate = advisory** (wired by 08): `test.yml` runs `ruff check src/ts_data_generator` with
  `continue-on-error: true` — the 114-violation D baseline surfaces without blocking; flip to
  required (one-line `continue-on-error` removal) once the 07+ surface is D-green.
- **Skills every session should consult:** `grilling` + `domain-modeling` by default; `prototype`
  for ticket 02; `research` for ticket 01.
- **Foundations (settled in charting — not tickets):**
  1. Q1=b — docstrings + style guide; no docs-site pipeline migration.
  2. Q2=b — scope = everything a user touches in the IDE, not `_*` internals.
  3. Q3=c — doctested for the core DataGen flow, illustrative elsewhere.
  4. Q4=a — `docs/docstrings.md` guide + scoped ruff `D` rules (per-file ignores for internals).
  5. Q5=a — docstrings canonical per-method reference; slim `api.md` to a conceptual guide.
  6. Q6=b — doctests = core generate-and-read flow + trend composition (`SinusoidalTrend` + `random_choice`).
  7. Q7=c — port `api.md` prose for descriptions; write fresh minimal runnable examples for `Example` blocks.
  8. Q8=c — full type-hint audit: add `@overload`, tighten unions, complete return types across the public surface.

## Decisions so far

<!-- one line per closed ticket: gist + link. Empty until tickets resolve. -->

- [01 — Public-symbol inventory](issues/01-public-symbol-inventory.md) — ~58 public symbols; type hints already strong, the real gap is ~22 one-liners + 7 missing docstrings on `DataGen` and zero Examples on the 4 core methods + 8 trends + 6 functions; only 2 `@overload` candidates.
- [02 — Style guide template](issues/02-style-guide-template.md) — Google-style template ratified on branch `prototype/02-style-guide` (`docs/docstrings.md`, commit `e0adf0c`): explicit+namespace doctest imports, one combined trend-composition doctest (+rest illustrative), omit `Returns` on `-> None`, package `__init__`-only module docstrings; prototype is the primary-source artifact 03/04/05 cite. Caught: `Granularity` imports from `ts_data_generator.schema` (not top-level); `add_metric` takes `trends` not `baseline=`.
- [03 — ruff `D`-rule config & scoping](issues/03-ruff-d-rule-config.md) — full `D` selected (Google-style ignores `D105`/`D107`/`D203`/`D213`); `per-file-ignores` for internals; gray modules `analyzers/converter` + `carriers` enabled (D enforced), `schema/parser` + `schema/types` internal; **red-baseline strategy** — the ~114 D violations are the 07+ worklist, full green returns once docstrings are written. Corrects 01: presence gap is ~61 D102 (per-getter), not ~7. Surfaced 08 (no CI ruff gate).
- [04 — Doctest CI wiring](issues/04-doctest-ci-wiring.md) — `--doctest-modules` in `addopts` + the 3 core module files (`data_gen`, `utils.trends`, `utils.functions`) listed in `testpaths` (testpaths-scoping keeps illustrative `>>>` elsewhere out of CI); root `conftest.py` injects `pd` + `ts_data_generator` into `doctest_namespace`; `test.yml` drops its explicit `tests` arg so `testpaths` applies (also pulls `tsdata/tests` into CI — already green). Green run proven (596 passed). Diff on `prototype/02-style-guide` working tree, uncommitted, folds to `main` via pilot 07. Unblocks one of 07's four blockers.
- [05 — api.md slimming boundary](issues/05-api-md-slimming-boundary.md) — `api.md` becomes the Python-surface orientation page; mental model deferred to `concepts.md` via one cross-link; per-method prose (`Configuration Methods` + `Retrieval/Aggregation` sections) and `Internal Architecture` section removed, replaced with a `DataGen`-only one-line-per-method summary table grouped by workflow stage, rows linking to the source file on GitHub (path-only blob URL, no line numbers); `DataGen Class` section slimmed to intro + `__init__` signature + one-line properties map; lifecycle script trimmed to the core flow (construct → `add_dimension` → `add_metric` → `.data` → `.aggregate`). Execution deferred to the do-phase — table one-liners are copied from finalized docstring summaries, so it lands after pilot 07.
- [06 — Type-hint audit strategy](issues/06-type-hint-audit-strategy.md) — **tighten, don't enumerate: zero `@overload`s.** Shape-difference bar (overload only when two modes have different *argument shapes* and collapsing misleads hover; "different value type in one slot" is below it) dissolves both research-01 candidates — `Dimensions.__init__` (`str|list[str]`) and `DataGen.__init__` (pre-built lists vs `add_*` is a usage pattern, not a signature variant). Instead: named alias `DimensionFunction = int|str|float|Generator` on `Dimensions`+`MultiItems` (scalar-vs-generator branches; setter's dead `list` acceptance flagged as a latent cleanup, not added to the type); tighten loose return types where unambiguous (`dict`→`dict[str, Any]`, etc.), leave honest unions. mypy/pyright CI gate deferred — out of scope (separate effort). Typing edits are do-phase execution folded into the per-module worklist 07 sequences; unblocks 07.
- [07 — Execution sequencing & pilot module](issues/07-sequencing-pilot-module.md) — **pilot = `data_gen.py`** (the only doctest-core module that exercises the class/method template — ~90 of 143 D violations are class/method-style — plus the core-flow doctest); do-phase sequence = `data_gen` → `utils/trends` → `utils/functions` → `anomalies/*` (batched) → `schema/models` (the collapsed "schema"+"factory types" slot; `Dimensions`/`Metrics`/`MultiItems`) → `carriers` + `analyzers/converter` (batched; the two gray D-enforced modules the proposed plan dropped); ~6 PRs — doctest-core modules individual, `anomalies` + gray pair batched; the pilot PR also folds `prototype/02-style-guide` → `main` carrying the 02/03/04/**08** config stack; `api.md` slim is the trailing do-phase step. Graduates the three execution fog patches into the worklist hand-off; unblocks 08 (the last open decision).
- [08 — Wire `ruff check` into CI](issues/08-ruff-ci-gate.md) — **advisory gate now, flip later**: `test.yml` runs `ruff check src/ts_data_generator` with `continue-on-error: true` (scoped to the package — whole-repo `ruff check .` rejected as test-noise; 499 test `D102` out of scope); the 114-violation D baseline surfaces without blocking, flip to required is a one-line `continue-on-error` removal at do-phase end. Cleared the 14 non-D errors: fixed the 6× `F821` (`Any` undefined in `schema/models.py` — real latent bug, added to `typing` import), `E501`-ignored internal `cli.py` (argparse help/example strings), folded the 2 package-surface docstring E501s into the pilot + step 5. Verified: 116 = 114 D + 2 deferred E501, F821 clean, pytest green. **The map's last decision — the enforcement criterion is wired; frontier empty, map done.** The working-tree diff folds to `main` via the pilot PR (joining 02/03/04); the advisory→required flip is the trailing do-phase enforcement step alongside the `api.md` slim.

## Not yet specified

- **Promoting the existing anomaly `>>>` blocks to CI doctests.** Q6 left this optional; 04's
  harness is now wired, so this is *possible* (rewrite those blocks to deterministic assertion-style
  + add their files to `testpaths`) — but still optional and outside the destination's core-flow CI
  scope, so it stays fog rather than graduating.
- **(Graduated to the 07 worklist — hand-off, not a ticket.)** The non-pilot module-by-module
  docstring writing, the non-pilot type-hint tightening (06 strategy attached), and the `api.md`
  structural slim + summary-table population all graduated from fog into the concrete sequenced
  do-phase worklist recorded in [07's resolution](issues/07-sequencing-pilot-module.md). They are
  execution, not decisions, so they live as that worklist — the hand-off point where the map ends and
  the "do" begins — not as new decision tickets.

## Out of scope

- Migrating the docs site to mkdocstrings / auto-generating `api.md` from docstrings (Q1=b; `api.md`
  stays hand-written conceptual per Q5=a).
- Documenting internal `_*` pipeline helpers (Q2=b — the user never hovers over them).
- Slimming the per-area docs pages (`/trends`, `/anomalies`, `/dimensions`) to a conceptual +
  point-to-docstring shape (surfaced by 05's summary-table-scope decision). The destination fixes
  scope at `api.md` + IDE docstrings; these pages are a separate effort if pursued, not a
  resumption.
- Adding a mypy/pyright typing-correctness CI gate (decided in 06). The destination is docstrings +
  hints *for hover*, enforced by ruff `D` (03/08); a type-correctness gate is a separate quality
  dimension off this route. If pursued, it's a fresh effort (its own map) — and 06's audit is the
  prerequisite input either way.