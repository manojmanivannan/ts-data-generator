# 06 — Type-hint audit strategy

Type: grilling
Status: open
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