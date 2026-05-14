## Parent PRD

`issues/prd.md` — Problem Statement, Solution, Implementation Decisions (ConceptDrift multi-segment, MissingData patterned mode)

## What to build

Extend two existing anomaly classes with their advanced modes. **MissingData** gains `mode="patterned"` accepting a `schedule` callable: `MissingData(mode="patterned", schedule=lambda ts: ts.weekday() == 6 and 2 <= ts.hour < 4)` — values are NaN whenever `schedule(timestamp)` returns True. **ConceptDrift** gains multi-segment support: pass multiple `DriftSegment` objects to define an arbitrary sequence of regime transitions (e.g., baseline → regime A → regime B → baseline). Segments execute sequentially with no gaps between them; each segment's `start_index` is relative to the previous segment's end.

## Acceptance criteria

- [ ] `MissingData(mode="patterned", schedule=fn)` sets NaN when the schedule function returns True
- [ ] Patterned mode composes with random and burst on the same metric (NaNs unioned)
- [ ] ConceptDrift with 3 segments transitions through all regimes in order
- [ ] Sequential segments have no gaps or overlaps in coverage
- [ ] With a fixed seed, patterned NaN positions and drift draws are deterministic
- [ ] Tests in `tests/test_anomalies.py` cover: schedule-based NaN injection, multi-segment drift sequencing, and combined advanced modes

## Blocked by

- Blocked by `issues/003-missing-data-random-burst.md`
- Blocked by `issues/004-concept-drift.md`

## User stories addressed

- 14. As a user modeling complex seasonal patterns, I want to define an arbitrary sequence of concept drifts.
- 15. As a user who wants patterned missing data, I want to specify that data is missing during specific recurring time windows.
