# Problem 1: Bees Algorithm for TSP and Continuous Optimization

**Status: TSP and continuous BA implemented.** Part A includes TSPLIB processing,
rounded distances, tour validation, both neighborhoods, and initialization.
Part B includes all four benchmark functions, their bounds, uniform initialization,
and clipped perturbations at dimensions 10 and 30. Both adapters use the same
search loop. All 28 automated tests pass; the full experiment set and output
pipeline remain unfinished.

## 1. How the TSP search works

```text
Initialize and evaluate scouts
    -> rank sites and select elite / other selected sites
    -> recruit neighbors and retain site solutions
    -> explore with fresh scouts
    -> update the best-so-far record
    -> repeat until 30,000 evaluations have been used
```

The implemented search ranks sites by increasing tour length. Every recruited
neighbor is generated from the original site, and the best of the site and its
recruits is retained. Fresh random scouts fill the remaining population slots.
The global best is stored separately. Use identical settings for both TSP moves.
Both columns below describe implemented behavior.

## 2. Algorithm design

| Block | TSP | Continuous functions |
| --- | --- | --- |
| Representation | Each city once; city 1 fixed first | Real vector of dimension 10 or 30 |
| Initialization | Uniformly shuffled permutations with city 1 fixed | Uniform coordinates within bounds |
| Neighbor | One random swap, or one random segment reversal; leave city 1 fixed | Independent uniform change in +/-10% of each coordinate's allowed range |
| Validity | Permutation remains valid; append city 1 only for displaying the route | Clip each perturbed coordinate to its bounds |
| Objective | Sum rounded edge lengths, including return edge | Evaluate the unshifted, noiseless function directly |
| Stopping | Exact evaluation budget, including rejected neighbors and fresh scouts | Same budget and counting rule |

For TSP use `floor(sqrt((xi-xj)^2 + (yi-yj)^2) + 0.5)` for **each edge**.
Do not use Python's ties-to-even `round()` as a replacement. Published optimal
tours may check distances but must never initialize or guide search.

| Function | Formula | Bounds per coordinate | Minimizer |
| --- | --- | --- | --- |
| Sphere | `sum(x_i^2)` | [-5.12, 5.12] | All zeros |
| Rosenbrock | `sum(100*(x_(i+1)-x_i^2)^2 + (1-x_i)^2)`, i = 1..D-1 | [-5, 10] | All ones |
| Rastrigin | `10*D + sum(x_i^2 - 10*cos(2*pi*x_i))` | [-5.12, 5.12] | All zeros |
| Ackley | `-20*exp(-0.2*sqrt(sum(x_i^2)/D)) - exp(sum(cos(2*pi*x_i))/D) + 20 + exp(1)` | [-32.768, 32.768] | All zeros |

All four minima are zero. Check each implementation at the minimizer and another
point against the [SFU definitions](data/README.md), allowing a small floating-point
tolerance. Known minimizing vectors must not be inserted into search.

## 3. Instances and experiment parameters

| Instance | Cities | Distance type | Optimal tour length |
| --- | ---: | --- | ---: |
| eil51 | 51 | EUC_2D | 426 |
| berlin52 | 52 | EUC_2D | 7,542 |
| st70 | 70 | EUC_2D | 675 |
| eil76 | 76 | EUC_2D | 538 |
| kroA100 | 100 | EUC_2D | 21,282 |
| ch150 | 150 | EUC_2D | 6,528 |

- [TSP configuration](configs/tsp.json): six instances x two neighborhoods x
  seeds 0-9 = **120 runs**.
- [Continuous configuration](configs/continuous.json): four functions x
  dimensions 10 and 30 x seeds 0-9 = **80 runs**.
- Each run uses **30,000 evaluations**, including initialization. Record the
  initial best, history, and final best solution. Complete the budget even when
  progress stalls or the known minimum is reached.
- The JSON files describe planned experiments and are not read by the solver.
  Their `null` BA fields still need confirmation for the full experiment set.

Current `bees_algorithm` function defaults:

| Parameter | Value |
| --- | ---: |
| `n_scouts` | 30 |
| `n_selected` | 10 |
| `n_elite` | 3 |
| `n_elite_recruits` | 10 |
| `n_other_recruits` | 5 |
| `max_evaluations` | 30,000 |

With these settings, a full iteration evaluates 65 recruits and 20 fresh scouts.
The last iteration may be partial. The TSP function accepts `swap` and
`segment_reversal`; `reverse` remains a compatible alias. Both adapters use
the same defaults.

## 4. Results and evaluation

The [output plan](results/README.md) lists all required tables and figures.
Two seed-42 `eil51` trials with the defaults above return lengths **622** (swap)
and **468** (segment reversal), both using exactly 30,000 evaluations. They were
reproduced on 8 November 2026; full repeated-run experiments and raw-record
exports remain pending. See the [root README](../README.md#4-results-and-evaluation).
TSP gap is `100 * (tour_length - optimum) / optimum`; lower is better.
For continuous functions the final objective is the error relative to zero,
apart from numerical rounding. Retain the corresponding tour or vector.

## 5. Reproduce the project

From the repository root, run `python scripts/verify_data.py` to check the bundled
files. See the [root setup instructions](../README.md#5-reproduce-the-repository-setup).
The root README also gives tested TSP and continuous Python commands. Run the
automated tests with `python -m unittest discover -s bees_optimization/tests -v`.
Batch and plotting commands are still pending. The [module map](bees/README.md)
and [validation checklist](tests/README.md) describe implemented and remaining work.

## 6. Continuous API and validation

```python
from bees_optimization.bees.continuous import continuous_bees

result = continuous_bees("rastrigin", dimension=30, seed=42)
```

The result contains `best_vector`, `best_value`, `initial_best`, `evaluations`,
and `history`. Initialization counts toward the budget; history starts after
initialization, then records every subsequent evaluation. Recruitment samples
from the original site and retains its best candidate. Every complete generation
replenishes unselected sites with fresh scouts. The perturbation radius is fixed
at 10% of each coordinate's domain width, with no adaptive decay.

Validation on 10 November 2026 covered all four functions at both dimensions,
seed 42, with 30,000 evaluations per case. All returned finite objectives,
in-bounds vectors, consistent objective values, and non-increasing histories.
These eight smoke checks are separate from the required 80-run experiment; they
do not establish convergence to the global optimum or complete the output pipeline.
