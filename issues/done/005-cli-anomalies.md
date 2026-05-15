## Parent PRD

`issues/prd.md` — Problem Statement, Solution, Implementation Decisions (CLI: separate --anomalies flag)

## What to build

Add `--seed` and `--anomalies` flags to the `tsdata generate` CLI command. `--seed` sets the global seed on `DataGen`. `--anomalies` is repeatable and accepts anomaly specs keyed by metric name: `--anomalies "sales:PointAnomaly(prob=0.01,magnitude=5)+MissingData(prob=0.02)"`. For concept drifts, each `--anomalies` flag specifies one drift segment; sequences are built by repeating the flag for the same metric, applied in declaration order. The existing `--mets` flag is unchanged. Update the `generate` command's help text and examples. Ensure the JSON config file schema also supports `anomalies` as an optional top-level field.

## Acceptance criteria

- [ ] `--seed 42` produces deterministic output across runs
- [ ] `--anomalies "metric:PointAnomaly(prob=0.1,magnitude=5)"` injects point anomalies via CLI
- [ ] `--anomalies "metric:MissingData(prob=0.05)"` injects missing data via CLI
- [ ] `--anomalies "metric:MissingData(mode=burst,burst_probability=0.02,min_length=3,max_length=10)"` supports burst mode parameters
- [ ] `--anomalies "metric:ConceptDrift(start_index=100,transition_window=50,target_mean=50,target_std=5,hold_duration=200,restore=true)"` creates a drift via CLI
- [ ] Combining `--mets` and `--anomalies` for the same metric name links them correctly
- [ ] Repeating `--anomalies` for the same metric creates multiple anomaly specs applied in order
- [ ] `--config` JSON files support an `"anomalies"` array field
- [ ] Tests in `tests/test_cli.py` cover: --seed determinism, all three anomaly types via CLI, repeatable flag behavior, and config file integration

## Blocked by

- Blocked by `issues/002-anomaly-pipeline-point.md`
- Blocked by `issues/003-missing-data-random-burst.md`
- Blocked by `issues/004-concept-drift.md`

## User stories addressed

- 9. As a CLI-first user, I want to specify anomaly specs from the command line alongside my existing --mets and --dims flags.
