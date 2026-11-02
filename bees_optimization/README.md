# Problem 1: Bees Algorithm for TSP and Continuous Optimization

**Status: specification, data, and folder structure only.** Both Part A and
Part B are required. No BA implementation or numerical results exist yet.

## 1. How the search will work

```text
Initialize and evaluate scouts
    -> rank sites and select elite / other selected sites
    -> recruit neighbors and retain site solutions
    -> explore with fresh scouts
    -> update the best-so-far record
    -> repeat until 30,000 evaluations have been used
```

Implement the BA of Pham and colleagues as covered in lectures. The group still
needs to choose the site counts, recruitment counts, and exact retention policy.
Use identical BA settings for the two TSP neighborhoods.

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
- `null` BA settings are unresolved group decisions, not usable defaults.

## 4. Results and evaluation

The [output plan](results/README.md) lists all required tables and figures.
TSP gap is `100 * (tour_length - optimum) / optimum`; lower is better.
For continuous functions the final objective is the error relative to zero,
apart from numerical rounding. Retain the corresponding tour or vector.

## 5. Reproduce the project

From the repository root, run `python scripts/verify_data.py` to check the bundled
files. See the [root setup instructions](../README.md#5-reproduce-the-repository-setup).
Search, batch, and plotting commands will be documented when implemented.
The [module plan](bees/README.md) and [validation checklist](tests/README.md)
define the next implementation steps.
