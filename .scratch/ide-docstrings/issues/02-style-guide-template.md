# 02 — Style guide template (docs/docstrings.md)

Type: prototype
Status: open
Blocked by: —

## Question

What is the canonical docstring template this project adopts? Draft `docs/docstrings.md` defining:

- **Section structure** — one-line summary, extended description, `Args`, `Returns`, `Raises`,
  `Example` (Google style; matches what already exists on the flagship methods).
- **When an `Example` is required vs optional** — required on the core flow (Q3=c/Q6=b:
  `DataGen` construct → `add_dimension`/`add_metric` → `.data`/`aggregate` + trend composition),
  optional/illustrative on the long tail.
- **Doctest vs illustrative convention** — `>>>` doctests (run in CI) for the core, plain `::`
  blocks elsewhere; how imports are handled in doctests (see 04's namespace decision).
- **Property convention** — document the getter; note setter behavior in the description.
- **Module-level docstring** convention for each public module.
- **Type-hint / `@overload` convention** (Q8=c) — when an overload earns a docstring, how the
  public overload is documented vs the impl.

Include **2–3 worked examples** to react to: a flagship method (`add_dimension` or `aggregate`),
a read/write property (`granularity`), and a standalone function (`random_choice`). "How should it
look" is the key question → prototype ticket. Link the draft as an asset from this ticket.