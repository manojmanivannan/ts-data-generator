## Parent PRD

`issues/prd.md` — Problem Statement, Solution, Implementation Decisions (ARNoiseTrend)

## What to build

Implement `ARNoiseTrend` in `trends.py` as a pure numpy autoregressive noise model of order p: `value[t] = sum(coefficients[i] * value[t-i-1]) + N(0, noise_std)`. Users provide explicit `coefficients` (list of floats, length determines order) or a `decay` parameter that auto-generates stable coefficients ensuring roots inside the unit circle. The trend needs a warm-up period of `order` steps to initialize the lag buffer before the actual timestamp range. The trend composes additively with other trends via `+`.

## Acceptance criteria

- [ ] `ARNoiseTrend(coefficients=[0.5, -0.2], noise_std=0.5)` produces order-2 AR noise
- [ ] `ARNoiseTrend(decay=0.8, order=3, noise_std=0.5)` auto-generates stable coefficients
- [ ] Auto-generated coefficients guarantee stationarity (roots inside unit circle)
- [ ] Output exhibits serial correlation consistent with the specified coefficients
- [ ] With a fixed seed via `rng`, output is deterministic
- [ ] Warm-up period produces the correct number of output values (no fewer than timestamps)
- [ ] Tests in `tests/test_generator.py` cover: explicit coefficients, auto-generation, seed determinism, and autocorrelation properties

## Blocked by

- Blocked by `issues/001-rng-foundation.md`

## User stories addressed

- 8. As a time series researcher, I want autoregressive noise with configurable order and coefficients, so that residuals in my synthetic data exhibit realistic serial correlation.
