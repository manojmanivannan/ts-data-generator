## Parent PRD

`issues/prd.md` — Problem Statement, Solution, Implementation Decisions (HolidayTrend)

## What to build

Implement `HolidayTrend` in `trends.py`. When the `holidays` library is installed, `HolidayTrend(country="US", effect=50, pre_window=3, post_window=2, direction="up")` automatically resolves major holidays for the given country. When `holidays` is not installed, accept a user-provided list of date strings via the `dates` parameter: `HolidayTrend(dates=["2024-01-01", "2024-12-25"], effect=50)`. The effect ramps linearly: 0 at `holiday - pre_window` days, peaking at `effect` on the holiday, returning to 0 at `holiday + post_window` days. Multiple overlapping holiday windows sum their effects. The trend composes additively with other trends via `+`.

## Acceptance criteria

- [ ] `HolidayTrend(country="US", effect=50, pre_window=3, post_window=2)` resolves US federal holidays for the date range
- [ ] Linear ramp: value at `holiday - 1` day ≈ `effect * (1/pre_window)` for upward direction
- [ ] `HolidayTrend(dates=["2024-01-01"], effect=50)` works without `holidays` installed
- [ ] Graceful error when `holidays` is not installed and no `dates` are provided
- [ ] Overlapping holiday windows sum their effects correctly
- [ ] `direction="down"` produces negative ramps
- [ ] Accepts `rng` parameter like other trends (for any future randomness)
- [ ] Tests in `tests/test_generator.py` cover: ramp shape correctness, fallback dates, direction, and window overlap

## Blocked by

- Blocked by `issues/001-rng-foundation.md`

## User stories addressed

- 6. As a retail data scientist generating sales forecasts, I want a holiday trend that boosts values on major holidays with configurable pre-holiday and post-holiday ramp windows.
- 10. As a library user who doesn't want to install holidays, I want HolidayTrend to accept a user-provided list of dates as a fallback.
- 11. As a user running experiments across multiple locales, I want to specify a country code and have it automatically resolve the correct holidays including moving holidays like Easter.
