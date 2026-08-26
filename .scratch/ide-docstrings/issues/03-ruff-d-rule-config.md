# 03 — ruff `D`-rule config & scoping

Type: task
Status: resolved
Resolved by: claude
Blocked by: 02

## Question

Decide and apply the pydocstyle `D`-rule config so CI enforces the style guide (Q4=a):

- Which `D` rules to **select** (e.g. `D201`–`D4` coverage that matches the Google-style template).
- The **ignore-set** for baseline noise that doesn't fit this project (e.g. `D100`/`D104` for
  `__init__.py`/CLI entry, `D105` for dunder methods, `D107` for `__init__` where Args live on the
  class, as appropriate).
- `[tool.ruff.lint.per-file-ignores]` **scoping** so the rules lint the public surface but ignore
  `_*` internals (Q2=b) — e.g. ignore `D` for `**/_*.py` and internal submodules.

The choice follows directly from the style guide (02); the **answer is the `pyproject.toml` diff**,
verified green with `ruff check`. Note any public symbol the rules flag that genuinely needs a
docstring fix vs a rule ignore, so the execution phase knows the baseline.

## Answer

**Decision: the `pyproject.toml` `D`-rule config** — applied in this ticket (branch
`prototype/02-style-guide`). Verified by `ruff check` against the ratified style guide (02) and the
public-symbol inventory (01). Two judgment calls were ratified with the user (see Resolution).

**Config:**

- `[tool.ruff.lint] select` += `"D"` (pydocstyle — enforces `docs/docstrings.md`).
- Global `ignore` (Google-style + style-guide-sanctioned):
  - `D105` — magic methods need no docstring (style guide §1).
  - `D107` — `__init__` Args live on the class docstring, not `__init__` (style guide §6; ratified
    decision 4).
  - `D203` — conflicts with `D211`; Google style uses no blank line before the class docstring.
  - `D213` — conflicts with `D212`; Google style puts the summary on the first line.
- `[tool.ruff.lint.per-file-ignores]` — `"D"` ignored on internal modules (scope Q2=b; style guide
  §5): `_version`, `aggregator`, `cli`, `expand`, `plotting`, `random`, `exceptions`,
  `utils/__init__`, `utils/registry`, `schema/parser`, `schema/types`, `analyzers/__init__`,
  `core/**`, `data/**`, `transforms/**`.
- **Public surface (D enforced):** the package `__init__`, `data_gen`, `utils/functions`,
  `utils/trends`, `anomalies/*`, `schema/models`, `schema/__init__`, **plus the two gray modules
  enabled per the user's decision: `analyzers/converter` (SchemaConverter) and `carriers`
  (DimensionCarrier).**

**Scoping facts the execution phase (07+) must respect:**

- `schema/` public surface = `schema/models.py` + `schema/__init__.py` only (the package `__init__`
  exports only `Granularity, AggregationType, Metrics, Dimensions, MultiItems`, all from `models`).
  `schema/parser.py` (CLI spec-parsing) and `schema/types.py` (preset dataclasses) are **internal** —
  confirmed by `api.md`'s "Internal Architecture" section. Do not document them to the user standard.
- `carriers.dedupe_sort` already has a full docstring — no false positive from enabling `carriers`.
  The carrier generator-protocol methods (`send`/`throw`/`close`) do surface as D102; they're
  low-value (Generator ABC protocol, not user API) — one-line them during the carriers pass rather
  than full §4 treatment.

**The "verified green" criterion — re-framed (user decision: red baseline).** There is **no CI ruff
gate**: `ci.yaml` is tag-triggered release/publish only, and `test.yml` runs pytest. Adding `D`
breaks nothing in CI. Full `ruff check` is **not** green today, by design — the residual violations are
the documented docstring-gap **baseline** that 07+ clears. Today's config-based `ruff check`:

| Rule | Count | Category |
|---|---|---|
| D102 undocumented public method | 61 | genuine gap — mostly trend/anomaly **property getters** + DataGen methods + carrier getters; write per style guide §4 |
| D413 missing blank line after last section | 50 | **auto-fixable** — `ruff check --fix` as a prep commit before/early in 07, or per-module during rewrites |
| E501 line-too-long | 8 | **pre-existing, out of scope for 03** |
| F821 undefined-name | 6 | **pre-existing, out of scope — but a real bug; triage separately** |
| D101 undocumented public class | 1 | genuine gap |
| D301 escape-sequence-in-docstring | 1 | genuine — needs a raw docstring |
| D402 signature-in-docstring | 1 | genuine — drop the signature from the docstring |

`D105`/`D107` are suppressed (sanctioned ignores); internal modules are D-clean (verified). Note:
passing `--select D` on the CLI *overrides* the config `ignore` (so it re-shows D105/D107 and the
D203/D213 incompatibility warnings) — that is a diagnostic-only artifact; normal `ruff check` uses
the config and is clean.

**Headline correction to ticket 01:** the inventory undercounted the presence gap. It graded ~22
one-liners + ~7 missing on `DataGen` at the *class* level, but D102 fires per-getter — the 8 trend
classes' `amplitude`/`freq`/`phase`/`noise_level` property getters (~40) + anomaly methods (~14) have
no per-symbol docstrings. Per style guide §4 these are genuine gaps, so 07+'s scope is materially
larger than 01's headline implied.

**Newly surfaced → ticket 08:** the destination requires "CI enforces via scoped ruff D rules," but no
CI workflow runs ruff. 08 wires `ruff check` into CI, gated on the public surface passing D (the red
baseline is by design until 07+'s writing completes).

### Resolution

Config applied to `pyproject.toml`. `ruff check` (config-based) runs clean of incompatibility
warnings and correctly suppresses D105/D107 + all internal modules. Two decisions ratified with the
user: (1) **red-baseline activation** — full `D` now; the ~114 D violations are the 07+ worklist, not
errors to suppress; full green returns once docstrings are written. (2) **gray modules** —
`analyzers/converter` + `carriers` are public (D enforced); `schema/parser` + `schema/types` are
internal. Lands on `main` with the pilot (07); until then this branch is the reference 04/05 cite.