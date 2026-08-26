# 04 — Doctest CI wiring

Type: task
Status: open
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