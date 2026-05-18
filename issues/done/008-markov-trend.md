## Parent PRD

`issues/prd.md` — Problem Statement, Solution, Implementation Decisions (MarkovTrend)

## What to build

Implement `MarkovTrend` in `trends.py` as a discrete-state Markov chain noise model. Define states (list of names), corresponding `values` (list of floats, one per state), and either `stickiness` (probability of staying in current state, all transitions equally likely) or a full N×N `transition_matrix` (Python API only). At each timestamp, sample the next state from the transition probabilities, then output `state_value + N(0, noise_std)`. Initialize from a random state (or first state in the list). The trend composes additively with other trends via `+`.

## Acceptance criteria

- [ ] `MarkovTrend(states=["low", "high"], values=[10, 100], stickiness=0.9, noise_std=5)` produces mostly sticky state transitions
- [ ] `MarkovTrend(states=["low", "high"], values=[10, 100], transition_matrix=[[0.7, 0.3], [0.2, 0.8]])` accepts explicit matrix
- [ ] `stickiness=0.95` produces long runs in the same state; `stickiness=0.5` produces frequent switching
- [ ] With a fixed seed via `rng`, state sequence and output are deterministic
- [ ] Output values match `state_value + noise` for the current state at each timestamp
- [ ] Tests in `tests/test_generator.py` cover: stickiness behavior, explicit matrix, seed determinism, state value correctness, and transition frequency

## Blocked by

- Blocked by `issues/001-rng-foundation.md`

## User stories addressed

- 7. As a quant generating synthetic asset prices, I want a discrete Markov chain noise model where I can define states and transition probabilities, so that my data exhibits realistic regime-switching behavior.
