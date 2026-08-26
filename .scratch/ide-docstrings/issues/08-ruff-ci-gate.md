# 08 — Wire `ruff check` into CI

Type: task
Status: open
Blocked by: 07

## Question

The destination requires "a written style guide that **CI enforces** via scoped ruff `D` rules." The
`D` config now exists (ticket 03, applied), but **no CI workflow runs ruff at all** — `ci.yaml` is
tag-triggered release/publish only, and `test.yml` runs pytest. So today the style guide is enforced
only by a developer's local `ruff check`, not by CI. Wire `ruff check` into CI and decide the
activation timing:

- **Mechanism** — add a `ruff check` step to `test.yml` (the PR/push-gated workflow) alongside
  pytest. Decide the exact invocation (e.g. `uv run ruff check .`).
- **Activation timing (the real decision).** With the red-baseline strategy (03, Q1=A), `ruff check`
  is intentionally red on ~114 D gaps until 07+ writes the docstrings. Options:
  - (a) Add the ruff step **now as advisory** (non-blocking / `continue-on-error` or a separate
    workflow) so CI surfaces docstring debt without failing PRs; flip it to a required gate once the
    public surface passes D.
  - (b) Add the ruff step **only after 07+ completes the surface**, directly as a required gate (CI
    stays green throughout; no advisory phase).
- **Scope of the gate** — `ruff check .` (whole repo) vs. scoped to `src/ts_data_generator`. Note
  the 14 pre-existing non-D errors (8 E501, 6 F821 — F821 is a real undefined-name bug, surfaced in
  03) must be cleared before a required gate can go green; decide whether that cleanup is part of
  this ticket or a prerequisite.

The **answer is the CI workflow diff + the activation-timing decision**, verified by a green CI run
on the advisory config (or, for option b, a dry-run showing the surface is green). This ticket is
the missing piece between "the config exists" (03) and "CI actually enforces it" (the destination).