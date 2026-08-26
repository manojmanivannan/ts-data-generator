# 04 — Doctest CI wiring

Type: task
Status: resolved
Claimed by: claude
Blocked by: 01, 02

## Question

How to run the core-flow + trend-composition doctests in CI (Q3=c / Q6=b). Decide:

- **Scope** — `--doctest-modules` applied to which modules (the core: `data_gen`, `utils.trends`,
  `utils.functions`), avoiding running illustrative-only doctests elsewhere.
- **Namespace** — doctests need `from ts_data_generator import ...` and pandas. Prefer a
  `conftest` doctest namespace / fixture that injects imports, over scattering
  `# doctest: +SKIP` or import boilerplate in every example. Decide the exact mechanism.
- **Hermeticity & speed** — ensure doctests are deterministic (the library is seedable) and don't
  slow CI meaningfully.

The **answer is the pytest `addopts` / `conftest` diff + a green CI run**. Scope follows the
inventory (01) and the doctest convention set by the style guide (02). This unblocks the pilot (07).

## Answer

**Resolved AFK** — the four open forks were put to the user (grilling round); all four recommended
choices accepted. The wiring diff lives in the working tree on branch `prototype/02-style-guide`
(same throwaway branch 02/03 cite; folds to `main` when pilot 07 lands it). It is **not** committed —
per project convention, commits happen only on user request.

**The diff (3 files):**

1. `pyproject.toml` — `[tool.pytest.ini_options]`:
   - `addopts = "-ra -q --doctest-modules"` (doctests collect on every local `pytest`, not CI-only).
   - `testpaths` extended to list the 3 core module files explicitly:
     `src/ts_data_generator/data_gen.py`, `src/ts_data_generator/utils/trends.py`,
     `src/ts_data_generator/utils/functions.py` (alongside `tests`, `tsdata/tests`).
     Only files in `testpaths` get doctest-collected, so the illustrative `>>>` blocks in
     `anomalies`, `schema/models`, `analyzers/converter`, `utils/registry`, `random` are never
     seen by pytest — no `--ignore` list to maintain. (Note: `pyproject.toml` also carries 03's
     uncommitted ruff-`D` config in the same working tree; 04's changes are the pytest block only.)
2. `conftest.py` (new, repo root — `tests/conftest.py` only covers `tests/`, not doctests from
   `src/`): an autouse `doctest_namespace` fixture injecting `pd` (pandas) and the
   `ts_data_generator` package. Explicit per-example imports are still written per §3; this is
   the safety net the ratified convention calls for.
3. `.github/workflows/test.yml` — `uv run -m pytest -vv tests` → `uv run -m pytest -vv`. The
   explicit `tests` path arg was making pytest ignore `testpaths`, so `--doctest-modules` would
   never have run in CI. Dropping it lets `testpaths` apply. This also brings `tsdata/tests` into
   CI (already green — verified), which the project intended (it was already in `testpaths`).

**Green run (proven on this branch):**

- `uv run -m pytest` → **596 passed**, including the 1 doctest collected from `data_gen.py`
  (`--collect-only` shows `src/ts_data_generator/data_gen.py: 1`). The existing `data_gen.py:111`
  construction doctest passes under the new harness.
- Namespace injection proven with a throwaway probe that used `pd` and `ts_data_generator` with no
  imports — passed, then deleted.

**Facts the resolution relies on (gathered, not asked):**

- Package is editable-installed → `from ts_data_generator import ...` resolves inside doctests.
- `utils/trends.py` and `utils/functions.py` have **no** `>>>` blocks today; only `data_gen.py:111`
  exists in-scope, so the harness is wired-but-mostly-empty until pilot 07 writes the real
  core-flow + trend-composition `>>>` blocks — which then light up automatically.
- The existing `data_gen.py:111` doctest predates the ratified convention (it relies on
  `Granularity` from module globals, no explicit import, no assertion). 04 keeps it passing as-is;
  **07 rewrites it** to the explicit-import + assertion form. Flagged so 07 doesn't treat it as
  already-conformant.
- `testpaths`-based scoping means adding a new illustrative `>>>` example in a non-core module
  **cannot** break CI — it isn't collected. Only the 3 listed files' doctests run.

**Does not graduate a ticket:** the "promoting anomaly `>>>` blocks to CI doctests" fog item stays
fog — Q6 left it optional and the destination's CI scope is the core flow; the harness being wired
makes it *possible* (rewrite those blocks to deterministic assertion-style + add their files to
`testpaths`) but not in scope here. Map's Not-yet-specified updated accordingly.