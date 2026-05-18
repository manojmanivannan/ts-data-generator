## Parent PRD

`issues/prd.md` — Problem Statement, Solution, Implementation Decisions (Optional dependency extras)

## What to build

Add `[holidays]` and `[all]` optional dependency extras to `pyproject.toml`. The `[holidays]` extra depends on the `holidays` library. The `[all]` extra includes both `[imputer]` (existing) and `[holidays]` (new). Update the README to document the new extras. Ensure `HolidayTrend` lazily imports `holidays` at call time (not at module import) so that importing `ts_data_generator` does not fail when `holidays` is not installed.

## Acceptance criteria

- [ ] `pip install "ts-data-generator[holidays]"` installs the `holidays` library
- [ ] `pip install "ts-data-generator[all]"` installs both `scipy` and `holidays`
- [ ] `pip install ts-data-generator` does NOT install `holidays`
- [ ] Importing `ts_data_generator` without `holidays` installed succeeds
- [ ] README documents `[holidays]` and `[all]` extras
- [ ] Existing `[imputer]` extra continues to work

## Blocked by

- Blocked by `issues/006-holiday-trend.md`

## User stories addressed

- 16. As a user installing the library, I want to install all optional features with a single `pip install "ts-data-generator[all]"` command.
