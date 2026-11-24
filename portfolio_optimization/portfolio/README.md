# Python package: portfolio

All modules are implemented. Run everything from the repository root; see the
[Problem 2 README](../README.md#5-reproduce-the-project) for commands.

| Module | Responsibility |
| --- | --- |
| `data.py` | Load asset statistics, reconstruct correlations and covariance |
| `evaluation.py` | Expected return, variance, and case target calculation |
| `repair.py` | Simplex projection and return-target repair |
| `feasibility.py` | Independent checks of final weight and return constraints |
| `one_plus_one.py` | (1+1)-ES with scalar 1/5th success-rule adaptation; shared `Archive` and `repair` helpers |
| `population_es.py` | (mu+lambda)- and (mu,lambda)-ES: recombination, self-adaptation, mutation, plus/comma survivor selection |
| `experiments.py` | Required cases, seeds, budgets, independent checks, and run records |
| `output.py` | Summaries and convergence plot from saved records |
| `__main__.py` | `pilot`, `full`, and `summarize` commands |

## Solver interface

```python
solve_one_plus_one(returns, covariance, min_return, seed, max_evaluations=30000)
solve_population(returns, covariance, min_return, seed, selection, max_evaluations=30000)
```

`returns` (length n) and `covariance` (n x n) may be Python sequences or NumPy
arrays; they are converted once. `selection` is `"plus"` or `"comma"`. Both return
a dictionary:

| Key | Content |
| --- | --- |
| `best_weights` | Archive best feasible allocation (list of n floats) |
| `best_variance`, `best_return` | Its variance and expected return |
| `feasible` | Whether any feasible allocation was found (always true with the shared repair) |
| `evaluations` | Exactly `max_evaluations` |
| `initial_best` | Archive best after initialization (1 evaluation for (1+1)-ES, 10 for population ES) |
| `history` | `[evaluation, archive best variance]` after every evaluation |
| `population_best` | Population ES only: `[evaluation, best parent variance]` at initialization and after each full generation |

## How the solvers work

**Shared by all three.** One evaluation is one variance calculation of an
already repaired candidate; initialization and rejected candidates count. The
`Archive` counts evaluations, stops exactly at the budget, and keeps the best
allocation that passes `feasibility.is_feasible`. Every candidate is repaired with
`repair.repair_weights` before it is evaluated.

**(1+1)-ES.** One parent from uniform [0, 1] weights, repaired. Each trial adds
`sigma * N(0, 1)` to every weight, repairs, and replaces the parent only if the
child's variance is strictly lower. `sigma` starts at `0.1 / sqrt(n)`, is
multiplied by `exp(1/3)` after a success and `exp(-1/12)` otherwise, and is kept in
`[1e-8, 1]`. One success in five trials leaves `sigma` unchanged:
`exp(1/3) * exp(-1/12)^4 = 1`.

**Population ES (mu = 10, lambda = 70).** Ten parents initialized as above, each
with step-size vector `0.1 / sqrt(n)`. Each child: two different random parents;
weights averaged, step sizes combined by geometric mean; step sizes adapted by
`exp(tau' * Z0 + tau * Zi)` with one shared `Z0`, `tau' = 1 / sqrt(2n)`,
`tau = 1 / sqrt(2 sqrt(n))`, clamped to `[1e-8, 1]`; then fresh normal mutation and
repair. **Plus** keeps the best 10 of parents and offspring, **comma** the best 10
of the offspring only. With 30,000 evaluations: 10 initial + 428 generations x 70
+ a final partial batch of 30.

Implementation choices are listed in the
[Problem 2 README](../README.md#2-algorithm-design); observed behaviour of the
450 runs is in [section 4](../README.md#4-results-and-evaluation).