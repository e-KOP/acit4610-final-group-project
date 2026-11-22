
# Problem 1: Bees Algorithm for TSP and Continuous Optimization

**Status: Implementation, experiments, and validation completed.**

Part A implements the Bees Algorithm (BA) for the Travelling Salesman Problem (TSP), including TSPLIB processing, rounded distances, tour validation, and two neighborhood operators.

Part B implements the same BA search framework for four continuous benchmark functions at dimensions 10 and 30.

The complete experiment set consists of **200 runs**, each using exactly 30,000 objective evaluations. Raw results, summary tables, convergence plots, and route visualizations are included in the repository.

All **50 automated tests passed on 22 November 2026**, including independent validation of the saved experiments and regression tests for the experiment and output pipelines.

## 1. How the Bees Algorithm works

```text
Initialize and evaluate scout population
    -> rank solutions by objective value
    -> select elite and other selected sites
    -> recruit neighbors around selected sites
    -> retain the best solution at each selected site
    -> generate fresh random scouts
    -> update the global best-so-far solution
    -> repeat until 30,000 evaluations are exhausted
```

The algorithm minimizes the objective function.

Each recruited neighbor is generated from the original selected site, rather than from the previously improved neighbor. The best solution among the original site and its recruits is retained.

Unselected population slots are replaced by fresh random scouts. A separate global best-so-far record preserves the best solution encountered throughout the search.

The same search implementation is shared between TSP and continuous optimization, while the representation, initialization, objective function, and neighborhood operator differ.

## 2. Algorithm design

| Component | TSP | Continuous functions |
| --- | --- | --- |
| Representation | Permutation of cities, with city 1 fixed first | Real-valued vector of dimension 10 or 30 |
| Initialization | Uniform random permutations | Independent uniform coordinates within bounds |
| Neighborhood | Random swap or segment reversal | Independent uniform perturbation of every coordinate |
| Neighborhood size | One swap or one segment reversal | +/-10% of each coordinate's domain width |
| Validity | Every city appears exactly once | Coordinates clipped to permitted bounds |
| Objective | Total rounded tour length, including return edge | Unshifted benchmark function value |
| Stopping | Exact objective evaluation budget | Same evaluation counting rule |

### TSP distance calculation

For every pair of cities, use the TSPLIB EUC_2D convention:

```text
distance(i,j) = floor(sqrt((xi-xj)^2 + (yi-yj)^2) + 0.5)
```

Distances are rounded individually before summation.

Python's built-in `round()` must not replace this calculation because it uses ties-to-even rounding.

Published optimal tour lengths are used for evaluating results, never for initializing or guiding the search.

### Continuous benchmark functions

| Function | Definition | Bounds per coordinate | Global minimizer |
| --- | --- | --- | --- |
| Sphere | `sum(x_i^2)` | [-5.12, 5.12] | All zeros |
| Rosenbrock | `sum(100*(x_(i+1)-x_i^2)^2 + (1-x_i)^2)` | [-5, 10] | All ones |
| Rastrigin | `10*D + sum(x_i^2 - 10*cos(2*pi*x_i))` | [-5.12, 5.12] | All zeros |
| Ackley | `-20*exp(-0.2*sqrt(sum(x_i^2)/D)) - exp(sum(cos(2*pi*x_i))/D) + 20 + exp(1)` | [-32.768, 32.768] | All zeros |

All four functions have a global minimum of zero.

The implementations are checked against their known minimizers and additional numerical test cases. Known minimizing vectors are never inserted into the search.

See [benchmark data and sources](data/README.md).

## 3. Instances and experiment parameters

### TSP datasets

| Instance | Cities | Distance type | Optimal tour length |
| --- | ---: | --- | ---: |
| eil51 | 51 | EUC_2D | 426 |
| berlin52 | 52 | EUC_2D | 7,542 |
| st70 | 70 | EUC_2D | 675 |
| eil76 | 76 | EUC_2D | 538 |
| kroA100 | 100 | EUC_2D | 21,282 |
| ch150 | 150 | EUC_2D | 6,528 |

The full experiment design is recorded in:

- [TSP configuration](configs/tsp.json): 6 instances x 2 neighborhoods x 10 seeds = **120 runs**.
- [Continuous configuration](configs/continuous.json): 4 functions x 2 dimensions x 10 seeds = **80 runs**.

Both experiments use seeds 0-9.

Each run uses exactly **30,000 objective evaluations**, including initialization, recruited neighbors, rejected candidates, and fresh scouts.

The budget is completed even when the best objective stops improving.

### Bees Algorithm parameters

The full experiments use the following provisional parameter configuration, referred to as Setting B:

| Parameter | Experimental value |
| --- | ---: |
| `n_scouts` | 10 |
| `n_selected` | 3 |
| `n_elite` | 1 |
| `n_elite_recruits` | 10 |
| `n_other_recruits` | 5 |
| `max_evaluations` | 30,000 |

Each complete iteration evaluates 20 recruited neighbors and 7 fresh scouts, totaling **27 evaluations**.

These settings were selected following preliminary experiments comparing three configurations using pilot seeds 100-104. The final experiment seeds 0-9 were kept separate from the pilot seeds.

The parameter selection remains provisional until the group confirms the pilot evidence.

The Python solver functions retain their original default parameters:

`30/10/3/10/5`

However, the completed experiment runner loads the selected experimental settings from the JSON configuration files and explicitly passes them to the solver.

Therefore, the original function defaults should not be confused with the settings used in the committed 200 experiments.

The TSP implementation supports `swap` and `segment_reversal`, with `reverse` retained as a compatible alias.

## 4. Results and evaluation

All required Problem 1 experiments were executed and their results committed on 20 November 2026.

The raw records contain the seed, configuration, initial objective, final objective, best solution, evaluation count, runtime, and compressed best-so-far history.

### TSP results

Mean percentage gaps to the published optimal tour lengths:

| Instance | Swap mean gap (%) | Segment reversal mean gap (%) |
| --- | ---: | ---: |
| eil51 | 34.41 | 5.54 |
| berlin52 | 35.46 | 7.50 |
| st70 | 63.02 | 8.07 |
| eil76 | 47.21 | 11.13 |
| kroA100 | 108.79 | 22.98 |
| ch150 | 153.47 | 52.32 |

Segment reversal achieved a lower final tour length than swap in all 60 paired instance-seed comparisons.

The results also show increasing difficulty for larger TSP instances, especially ch150, under the fixed evaluation budget.

The percentage optimality gap is calculated as:

```text
gap (%) = 100 * (tour_length - optimum) / optimum
```

The earlier seed-42 eil51 trials, which used the original default BA settings, produced tour lengths of 622 for swap and 468 for reversal. These preliminary trials are separate from the completed experiments using Setting B.

### Continuous optimization results

Mean final objective values over ten seeds:

| Function | Dimension 10 | Dimension 30 |
| --- | ---: | ---: |
| Sphere | 0.4368 | 5.731 |
| Rosenbrock | 89.66 | 2431 |
| Rastrigin | 39.13 | 267.5 |
| Ackley | 6.216 | 10.58 |

All continuous functions have a theoretical global minimum of zero.

The experiments demonstrate improvement over initialization, but also highlight the difficulty of higher-dimensional optimization using a fixed perturbation radius.

These results describe performance under the selected algorithm configuration and evaluation budget; they do not establish convergence to the global minimum.

### Generated outputs

The [results directory](results/README.md) contains:

- 120 TSP raw experiment records.
- 80 continuous raw experiment records.
- Full-precision CSV summary tables.
- Human-readable Markdown summary tables.
- Two TSP convergence plots.
- One berlin52 best-route visualization.
- One Rastrigin D=10 convergence plot.
- One continuous D=30 boxplot figure.
- Experiment metadata, including source revision and input checksums.

Summary statistics include best, mean, sample standard deviation, initial objective, and average runtime.

Convergence histories are aligned by objective evaluation count rather than iteration number.

## 5. Reproduce the experiments

Run all commands from the repository root.

### Install dependencies

Use a compatible Python version (Python 3.11 or newer) and install:

```bash
python -m pip install -r requirements.txt
```

### Verify original datasets

```bash
python scripts/verify_data.py
```

This verifies the original six TSPLIB datasets and five OR-Library datasets using stored checksums.

### Run the complete automated test suite

```bash
python -m unittest discover -s bees_optimization/tests -v
```

All 50 tests passed on 22 November 2026.

### Run a single TSP experiment

```bash
python -m bees_optimization.bees.experiments tsp --instances berlin52 --neighborhoods segment_reversal --seeds 1
```

This reproduces the recorded berlin52 segment-reversal run with seed 1 and a final tour length of 7,833.

Subset experiments are saved under `results/scratch/`, preserving the committed full experiment records.

### Run a continuous experiment

```bash
python -m bees_optimization.bees.experiments continuous --functions sphere --dimensions 10 --seeds 0
```

### Regenerate summary tables and figures

```bash
python -m bees_optimization.bees.output
```

This regenerates the tables and figures from the saved raw records without rerunning the optimizer. It writes to the repository's existing results directories.

### Rerun all 200 experiments

```bash
python -m bees_optimization.bees.experiments all
```

**Warning:** The full experiment command writes to `results/raw/` and can overwrite the committed raw experiment files and metadata. Use a separate working copy if independently rerunning the full study.

## 6. Independent validation

The project includes an independent validation module:

`bees/validate_results.py`

Run:

```bash
python -m bees_optimization.bees.validate_results
```

The validator checks:

- All 120 TSP and 80 continuous records.
- Complete configuration and seed coverage.
- Absence of duplicate experimental records.
- Exact evaluation budgets and BA settings.
- Valid TSP permutations and independently recalculated tour lengths.
- Continuous solution bounds and independently recalculated objectives.
- Consistency of initial and final objectives.
- Ordered, non-increasing best-so-far histories.
- Full-precision statistical summary tables.
- Configuration provenance and original TSPLIB dataset checksums.

All 200 committed records passed these checks on 22 November 2026.

### Automated testing

The test suite contains 50 tests:

| Test file | Coverage |
| --- | --- |
| `test_algorithm.py` | Original TSP Bees Algorithm behavior |
| `test_tsp_data.py` | TSPLIB parsing, distance matrices, neighborhoods, and regression tests |
| `test_search.py` | Shared BA search, recruitment, budgets, and parameter boundaries |
| `test_continuous.py` | Continuous objectives, dimensions, bounds, and deterministic behavior |
| `test_results.py` | Independent result calculations, integrity checks, invalid-record detection, and full experiment validation |
| `test_experiment_pipeline.py` | Configuration, history compression, small experiment batches, convergence alignment, and output regeneration |

The additional validation tests include deliberately invalid records to confirm that incorrect tours, objectives, histories, settings, and experiment coverage are rejected.

The experiment-pipeline tests also regenerate all required figures and statistical tables in temporary directories without modifying the committed experimental results.

See [test documentation](tests/README.md).

## 7. Continuous API

```python
from bees_optimization.bees.continuous import continuous_bees

result = continuous_bees(
    "rastrigin",
    dimension=30,
    seed=42
)

print(result["best_value"])
print(result["best_vector"])
print(result["evaluations"])
```

The result contains:

- `best_vector`: Best continuous solution.
- `best_value`: Best objective value.
- `initial_best`: Best initial scout objective.
- `evaluations`: Number of evaluated candidates.
- `history`: Best-so-far objective history.

Initialization contributes to the evaluation budget.

History starts after initial population evaluation and then records every subsequent objective evaluation in the solver's in-memory result. The experiment runner compresses this history before saving it.

The continuous neighborhood radius remains fixed at 10% of each coordinate's allowed domain width, with no adaptive decay.

The full experiments and independent validation establish reproducibility and internal consistency of the reported results, not a guarantee of finding the global optimum.
