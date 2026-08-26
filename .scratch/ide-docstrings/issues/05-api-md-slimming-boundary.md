# 05 — api.md slimming boundary

Type: grilling
Status: open
Blocked by: 01, 02

## Question

Which sections of `docs/api.md` stay and which go, now that docstrings become the canonical
per-method reference (Q5=a)? Decide the boundary:

- **Keep** the conceptual guide: the mental model (how dimensions/metrics/trends relate), the
  quickstart, and the import/cheatsheet orientation.
- **Remove** the per-method prose that the docstrings now hold authoritatively (the long
  Parameters/Examples blocks currently duplicated in `api.md`).
- **Link strategy** — how `api.md` points readers to the canonical reference (e.g. "full signature
  and examples in the docstring / source," possibly with a generated summary table).

HITL — the user weighs in on what stays, since `api.md` is the published docs site's most-read
page and the slimming is a judgment call. Resolving this is what stops the docstring ↔ `api.md`
drift permanently.