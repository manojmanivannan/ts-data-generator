# 08 — Wire `ruff check` into CI

Type: task
Status: resolved
Claimed by: claude
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

## Answer

Resolved in one grilling round (all three decisions taken on recommendation). The enforcement
criterion of the destination is now wired.

### Decisions

- **Q1 = (a) — advisory now, flip later.** A `ruff check` step is added to `test.yml` with
  `continue-on-error: true`, so the intentional 114-violation D baseline surfaces on every PR
  without blocking. The mechanism is wired *now* (this task's job); the flip to a required gate is a
  one-line `continue-on-error` removal performed at do-phase end, once the 07+ worklist drives
  `src/ts_data_generator` D-green. Chosen over (b) so every do-phase PR gets honest ruff signal in CI
  rather than relying on the developer's local `ruff check`, and so the destination's "CI enforces"
  criterion lands as a one-line edit rather than a fresh piece of work after the surface is done.
- **Q2 = (a) — gate scoped to `src/ts_data_generator`.** The destination enforces scoped `D` on the
  *public package surface* (Q4=a, Q2=b), not on tests. `ruff check .` (whole repo) was rejected: it
  pulls in 1054 errors, of which 499 are `D102` on test methods and 70 are test-file style noise —
  neither the public surface nor the intended baseline. Test linting (E/W/F/I/B/UP on `tests/`,
  `tsdata/tests/`) is a useful-but-separate concern, out of scope for this effort.
- **Q3 = (A) — fix the bug + the unwrappable noise now; fold the two docstring E501s into their
  do-phase steps.** The 14 non-D errors are not part of the intended D baseline and must not clutter
  the advisory signal forever:
  - **6× `F821`** (`Undefined name 'Any'` in `schema/models.py`) — a real latent bug: `Any` used in
    annotations but never imported. Fixed now by adding `Any` to the `typing` import. One line, no
    reason to wait for do-phase step 5.
  - **7× `E501`** in internal `cli.py` — argparse `description`/`help` prose and unwrappable
    example metric-spec strings; `cli.py` is an internal `D`-ignored module with no do-phase home.
    Added `"E501"` to its per-file-ignores entry.
  - **2× package-surface `E501`** (`data_gen.py:257` docstring summary, `models.py:212` illustrative
    `>>>` example) — folded into the do-phase steps that rewrite those docstrings anyway: the pilot
    (step 1) owns `data_gen.py:257`, step 5 owns `models.py:212`. Avoids editing do-phase files
    twice; they clear naturally. They show as a transient 2-stray-E501 in the advisory output until
    those steps land — honest signal, both in files actively being docstring'd.

### Mechanism (applied to the working tree on `prototype/02-style-guide`)

- `.github/workflows/test.yml` — new `Run ruff check 🧹 (advisory)` step before pytest:
  `continue-on-error: true` + `uv run ruff check src/ts_data_generator`. The comment records the
  flip instruction (remove `continue-on-error` to make it required once the surface passes `D`).
- `pyproject.toml` — `"src/ts_data_generator/cli.py" = ["D", "E501"]`.
- `src/ts_data_generator/schema/models.py` — `from typing import TYPE_CHECKING, Any, NamedTuple`.

### Verified signal

`uv run ruff check src/ts_data_generator` now reports **116 errors = 114 D (the intentional
baseline: 61 D102, 50 D413, 1 D402, 1 D301, 1 D101) + 2 E501 (the deferred docstring lines)**.
`F821` passes clean; the `cli.py` E501 noise is gone. `pytest` still green (596 passed, exit 0). The
advisory gate's only red is the D baseline the do-phase clears — the flip to required needs zero
further cleanup beyond the two folded E501s the pilot/step 5 already own.

### Implication for the map

This is the **last open decision ticket** — the map's "enforcement" criterion is decided, and the
frontier is empty; the map is done. The working-tree diff folds to `main` via the **pilot PR (07,
step 1)**, which now carries the **02/03/04/08** config stack (08 joining the fold 07's resolution
originally listed as 02/03/04). The **advisory→required flip** is a trailing do-phase action — the
one-line `continue-on-error` removal — performed once the 07+ worklist drives the surface D-green;
it records as the enforcement step at the do-phase end, alongside the trailing `api.md` slim (05).