# 07 — Execution sequencing & pilot module

Type: grilling
Status: open
Blocked by: 02, 03, 04, 06

## Question

In what order does the bulk docstring + type-hint writing proceed, and which module is the
**pilot** that validates the full stack (style guide 02 + doctest CI 04 + ruff `D` 03 + slimmed
`api.md` 05 + typing strategy 06) end-to-end before rolling out?

- **Recommended pilot:** `data_gen.py` (`DataGen`) — the flagship class, the one users hover most,
  and the doctest core flow lives here, so it exercises every part of the stack.
- **Proposed sequence for the rest:** `utils.trends` → `utils.functions` → `anomalies` → `schema`
  → pre-built factory types (`Dimensions`/`Metrics`/`MultiItems`).
- **Batch size** — one module per PR, or group the smaller ones (`utils.functions` + `anomalies`)?

HITL — the user picks the pilot and batch cadence. Resolving this graduates the
"module-by-module writing" fog (map's Not-yet-specified) into a concrete sequenced worklist, which
is the hand-off point: the map is done, the "do" begins.