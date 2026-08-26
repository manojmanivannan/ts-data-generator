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
  (`-ra -q`, no `--doctest-modules` yet). Docstring style = Google. **No CI ruff gate today**
  (`ci.yaml` is release-only; `test.yml` runs pytest) → ticket 08 wires it in.
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

## Not yet specified

- **Module-by-module docstring + example writing (non-pilot).** The bulk execution. Can't be
  sharply ticketed per module until the pilot (07) validates the full stack end-to-end; one patch
  that graduates into a sequenced worklist once the pilot is done.
- **Promoting the existing anomaly `>>>` blocks to CI doctests.** Q6 left this optional; 04's
  harness is now wired, so this is *possible* (rewrite those blocks to deterministic assertion-style
  + add their files to `testpaths`) — but still optional and outside the destination's core-flow CI
  scope, so it stays fog rather than graduating.
- **Whether to add a mypy/typing CI gate.** Sub-decision inside 06's typing strategy; defer until
  06 settles the overload/union work.

## Out of scope

- Migrating the docs site to mkdocstrings / auto-generating `api.md` from docstrings (Q1=b; `api.md`
  stays hand-written conceptual per Q5=a).
- Documenting internal `_*` pipeline helpers (Q2=b — the user never hovers over them).