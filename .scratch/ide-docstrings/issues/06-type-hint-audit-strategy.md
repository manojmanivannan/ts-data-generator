# 06 — Type-hint audit strategy

Type: grilling
Status: resolved
Claimed by: claude
Blocked by: 01

## Question

For the full type-hint audit (Q8=c), decide the strategy across the public surface (use the
inventory from 01):

- **Overloads** — which signatures get `@overload`? Candidates: `DataGen.__init__` constructor
  variants (passing pre-built `Dimensions`/`Metrics`/`MultiItems` lists vs. building via `add_*`),
  and the pre-built `Dimensions`/`Metrics`/`MultiItems` factory constructors. Decide which earn an
  overload for hover vs. which are fine as a single union signature.
- **Union tightening** — which `int | float | str | list | dict | Generator`-style unions should be
  narrowed or split for clarity at the call site.
- **Missing return types** — where across the public surface are return annotations absent or
  `Any` that should be concrete.
- **CI gate** — whether to add a mypy (or pyright) typing gate; this is the deferred sub-decision
  (see map's Not-yet-specified). Default: add a non-strict public-surface gate if cheap, else defer.

HITL — overload choices are judgment calls (extra overloads are maintenance cost) the user should
make. The answer is a typing-strategy decision + the overload list, not the full edits.

## Answer

Strategy resolved across two grilling rounds (all recommendations accepted): **tighten, don't
enumerate.** The audit adds *zero* `@overload`s; the two research-01 candidates dissolve under the
threshold the user set. The typing work is aliasing one union + parameterizing loose return types —
mechanical do-phase execution folded into the per-module worklist the pilot (07) sequences, not a
per-site decision.

**1. `@overload` threshold (the meta-rule).** Adopt a **shape-difference bar**: add an overload only
when two usage modes have genuinely different *argument shapes* (different param types/counts — not
just different members of one union) AND collapsing them into one signature is *misleading* at the
hover. "Different value *type* in the same slot" (e.g. `str | list[str]`) is **below** the bar.
Rationale: the destination is useful IDE hover, not an exhaustively enumerated surface; overloads
carry sync/maintenance cost (a second signature, ruff `D` docstrings on each per ticket 02), so they
earn their place only when a single union would *lie* about the call.

**2. Overload candidates — both rejected (zero overloads).**
- `Dimensions.__init__` (`name: str | list[str]`, single- vs multi-column): the param shape is
  identical — one slot, two union members; constructor returns `None` either way. Below the
  shape-difference bar. The single-vs-multi behavior is already documented in `generate()` (it
  branches on `isinstance(self._name, list)`); `.name` honestly returns `str | list[str]`. Keep the
  single signature; let the docstring carry the semantics.
- `DataGen.__init__` (pre-built `list[Dimensions]`/`Metrics`/`MultiItems` vs build via `add_*`): the
  two "modes" are the *same signature* — mode 1 is `DataGen(...)` with the three list args defaulted to
  `None`, mode 2 is the same call with them filled in. "Build via `add_*`" is a *usage pattern*
  (methods called after construction), not a *signature variant*; there is no second shape to
  overload to. Overloading would duplicate the signature to express what optional-with-default params
  already say. Keep the single signature; the incremental-build pattern is a docstring/`Example`
  concern (02's guide + 07's pilot).

**3. Union tightening — `function: int | str | float | Generator`.** Introduce a **named alias**
`DimensionFunction = int | str | float | Generator` (same alias reused on `MultiItems.function`),
with a docstring naming the two semantic branches: scalar (`int | str | float` = "constant value")
vs `Generator` (= "value-producing generator"; the `utils/functions.py` helpers all return
`DimensionCarrier[T]`, a `Generator` subclass). Replaces the inline union on both classes — a
vocabulary gain (per domain-modeling) and no duplication. Not overloads: identical param shape, so
below the Q1 bar. Finding: the `.function` *setter* accepts `list` too
(`isinstance(value, (int, str, float, Generator, list))`), but `next()` on a plain list raises
`TypeError` — that `list` branch is dead/misleading at runtime, and the type correctly omits it.
Tightening must **not** add `list`; the setter's `list` acceptance is a latent cleanup, not a typing
change (flagged for the do-phase editor of `schema/models.py`, not a separate decision).

**4. Missing / loose return types.** Research 01 found *no absent* return annotations on the public
surface, but several *loose* ones (`to_json() -> dict` unparameterized; unparameterized `list`/`dict`
on some properties/collections). Bar: **tighten where unambiguous** — parameterize the cheap,
certain ones (`to_json() -> dict[str, Any]`, known-element `list[...]`); leave genuinely-ambiguous
unions (e.g. `.name -> str | list[str]`, an *honest* union, not loose) as-is. No full
generic-parameterization everywhere — match the destination (useful hover), don't over-engineer. This
is mechanical do-phase work; the strategy decision is just the bar.

**5. CI typing gate (mypy/pyright) — deferred, ruled out of scope.** No type-checker config exists in
the repo today (confirmed). The destination is docstrings + hints *for hover*, enforced by ruff `D`
(tickets 03/08). A type-*correctness* gate is a different quality dimension off this route: adding it
imports a second enforcement regime and a new red baseline to clear. The audit (this ticket) already
improves the hints. Deferred to a **separate effort** (its own map) if pursued — and recorded in the
map's **Out of scope** so it's an explicit scoping decision, not a dangling "maybe." This retires the
"Whether to add a mypy/typing CI gate" fog item.

**Implication for the map:** 07's pilot validates the typing stack as "alias + return-type
tightening" rather than "overloads" (research 01's shape-(3) framing refines to this). No new ticket:
the typing edits are do-phase execution folded into the same per-module worklist the pilot graduates,
alongside the docstring writing. Unblocks 07 (its last blocker).