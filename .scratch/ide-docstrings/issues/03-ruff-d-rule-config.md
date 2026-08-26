# 03 — ruff `D`-rule config & scoping

Type: task
Status: open
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