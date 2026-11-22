
# ACIT4610 Final Group Project: Bees Algorithm and Evolution Strategies

Study the Bees Algorithm (BA) on route planning and continuous optimization, and Evolution Strategies (ES) on constrained portfolio optimization.

**Status: Problem 1 implementation, experiments, and validation completed.**

The Bees Algorithm is implemented for six Travelling Salesman Problem (TSP) instances using swap and segment reversal neighborhoods, and four continuous benchmark functions at dimensions 10 and 30. Both implementations share the same search loop with exact objective evaluation-budget accounting.

All **200 required Problem 1 experiments** have been executed and their raw results committed. Summary tables and figures have been generated and independently verified.

The complete Problem 1 test suite contains **50 passing automated tests**, including 22 additional tests for independent result validation, experiment execution, statistical processing, and output reproduction.

Problem 2, Evolution Strategies for constrained portfolio optimization, remains to be implemented.

**Group number:** Group-8

**Group members:** Zhongye Xue, Syed Mohammad Abdur-Rahman Tirmizey, Jakob Andreas Amtedal, and Khoa Anh Huynh.

## 1. Project organization

The project follows the workflow:

```text
Read and validate original benchmark data
    -> implement and validate objective functions
    -> implement optimization algorithms
    -> execute independent seeds with fixed evaluation budgets
    -> save solutions and best-so-far histories
    -> generate statistical summaries and figures
    -> independently validate experimental results
    -> analyze and document performance
```

| Problem | Scope | Folder |
| --- | --- | --- |
| 1 | Bees Algorithm for TSP and continuous functions | [bees_optimization](bees_optimization/README.md) |
| 2 | (1+1)-ES, (mu+lambda)-ES, and (mu,lambda)-ES for portfolio variance minimization | [portfolio_optimization](portfolio_optimization/README.md) |

Each problem has its own Python package, configuration files, datasets, tests, and experimental results.

```text
.
├── README.md
├── requirements.txt
├── bees_optimization/
│   ├── README.md
│   ├── bees/                 # BA solver, experiments, output, validation
│   ├── configs/              # TSP and continuous experiment settings
│   ├── data/tsplib/          # Six original TSP benchmark datasets
│   ├── tests/                # Algorithm and experiment regression tests
│   └── results/
│       ├── raw/              # 200 saved experiment records and metadata
│       ├── tables/           # CSV and Markdown summaries
│       └── figures/          # Convergence, route, and distribution plots
├── portfolio_optimization/
│   ├── README.md
│   ├── portfolio/            # Planned ES implementation modules
│   ├── configs/              # Portfolio experiment specification
│   ├── data/or_library/      # Five original portfolio datasets
│   ├── tests/                # Portfolio validation checklist
│   └── results/              # Required portfolio output specification
├── scripts/
│   └── verify_data.py        # Original dataset integrity verification
├── docs/
│   ├── requirements.md       # Assignment requirements checklist
│   ├── development.md        # Implementation progress
│   └── ai_usage.md           # AI assistance documentation
└── report/                   # Group-authored submission report
```

## 2. Algorithm design

### Problem 1: Bees Algorithm

The Bees Algorithm uses a population of scout solutions, selected sites, neighborhood recruitment, and random exploration.

The search follows these steps:

1. Generate and evaluate the initial scout population.
2. Rank solutions by objective value.
3. Select elite and other promising sites.
4. Recruit neighborhood solutions around each selected site.
5. Retain the best solution from each site and its recruits.
6. Generate fresh random scouts to replenish the population.
7. Update the separately maintained global best-so-far solution.
8. Repeat until the exact evaluation budget is exhausted.

Every recruited neighbor is generated from the original selected site, rather than from the previously improved neighbor.

The global best-so-far solution is maintained separately from the current population. Every evaluated candidate counts toward the budget, including rejected solutions and newly generated scouts.

The shared implementation is located in `bees_optimization/bees/search.py`.

### TSP implementation

TSP solutions are permutations containing each city exactly once, with city 1 fixed at the beginning.

Two neighborhood operators are implemented:

- **Swap:** Exchange two randomly selected city positions, excluding the fixed starting city.
- **Segment reversal:** Reverse a randomly selected contiguous segment, excluding the fixed starting city.

The implementation uses TSPLIB EUC_2D distances, calculated by rounding each Euclidean edge distance separately:

```text
distance(i,j) = floor(sqrt((xi-xj)^2 + (yi-yj)^2) + 0.5)
```

The objective is the total tour length, including the final edge returning to the starting city.

Python's built-in `round()` is not used because its ties-to-even behavior differs from the required TSPLIB rounding convention.

Published optimal tour lengths are used only for performance evaluation, never to initialize or guide the search.

### Continuous optimization

The continuous BA implementation supports four benchmark functions:

| Function | Bounds per coordinate | Global minimum | Minimizer |
| --- | --- | ---: | --- |
| Sphere | [-5.12, 5.12] | 0 | All zeros |
| Rosenbrock | [-5, 10] | 0 | All ones |
| Rastrigin | [-5.12, 5.12] | 0 | All zeros |
| Ackley | [-32.768, 32.768] | 0 | All zeros |

Each solution is a real-valued vector of dimension 10 or 30.

Initialization samples every coordinate independently and uniformly within the permitted bounds.

Neighborhood search independently perturbs each coordinate by up to 10% of its allowed domain width. Modified coordinates are clipped to their bounds.

The perturbation radius remains fixed throughout optimization, without adaptive decay.

Known minimizing vectors are used for numerical testing only and are never inserted into the optimization process.

See [Problem 1](bees_optimization/README.md) for the complete definitions and implementation details.

### Problem 2: Evolution Strategies

Problem 2 minimizes portfolio variance subject to long-only allocation, budget, and minimum-return constraints.

Three Evolution Strategies are required:

- (1+1)-ES with scalar step-size adaptation.
- (mu+lambda)-ES with elitist population selection.
- (mu,lambda)-ES with offspring-only population selection.

All three variants must use common portfolio data loading, covariance calculation, objective evaluation, feasibility checking, and constraint repair.

The portfolio implementation and its 450 required experimental runs remain outstanding in the current project branch.

See [Problem 2](portfolio_optimization/README.md) for the detailed specification.

## 3. Instances and experiment parameters

The assignment requires 650 experimental runs in total.

| Experiment | Cases | Variants | Seeds per case/variant | Required runs |
| --- | ---: | ---: | ---: | ---: |
| TSP | 6 instances | 2 neighborhoods | 10 | 120 |
| Continuous BA | 4 functions x 2 dimensions | 1 | 10 | 80 |
| Portfolio ES | 5 datasets x 3 return targets | 3 | 10 | 450 |
| **Total** | | | | **650** |

Every run uses exactly **30,000 objective evaluations**, including initialization and rejected candidates.

The full project therefore requires 19,500,000 objective evaluations.

The experiment design uses seeds 0-9. These seeds are a project choice; the assignment requires ten independent runs per configuration.

### TSP instances

| Instance | Cities | Distance type | Optimal tour length |
| --- | ---: | --- | ---: |
| eil51 | 51 | EUC_2D | 426 |
| berlin52 | 52 | EUC_2D | 7,542 |
| st70 | 70 | EUC_2D | 675 |
| eil76 | 76 | EUC_2D | 538 |
| kroA100 | 100 | EUC_2D | 21,282 |
| ch150 | 150 | EUC_2D | 6,528 |

### Bees Algorithm experimental settings

The completed 200 Problem 1 experiments use the following provisional BA configuration, referred to as Setting B:

| Parameter | Value |
| --- | ---: |
| `n_scouts` | 10 |
| `n_selected` | 3 |
| `n_elite` | 1 |
| `n_elite_recruits` | 10 |
| `n_other_recruits` | 5 |
| `max_evaluations` | 30,000 |

Each full iteration evaluates 20 recruited neighbors and 7 fresh scouts, totaling 27 objective evaluations.

The settings were selected through preliminary pilot comparisons using seeds 100-104, separate from the final experimental seeds 0-9.

The pilot compared three BA configurations:

- Setting A: 30/10/3/10/5
- Setting B: 10/3/1/10/5
- Setting C: 6/2/1/5/3

The selected configuration remains provisional until the group confirms the original pilot evidence.

The BA solver functions retain their original defaults of 30/10/3/10/5 when called directly. The experiment runner instead loads the selected settings from the JSON configuration files and explicitly passes them to the solver.

The TSP implementation accepts both `swap` and `segment_reversal`, while `reverse` remains a compatible alias.

Experiment configurations are stored in:

- [TSP configuration](bees_optimization/configs/tsp.json)
- [Continuous configuration](bees_optimization/configs/continuous.json)
- [Portfolio configuration](portfolio_optimization/configs/experiments.json)

### Benchmark data

All eleven required original benchmark datasets are included.

The repository contains six TSPLIB instances and five OR-Library portfolio datasets.

Dataset sources, transformations, and SHA-256 checksums are documented in:

- [TSPLIB sources](bees_optimization/data/README.md)
- [OR-Library sources](portfolio_optimization/data/README.md)

The continuous benchmark functions are evaluated directly from their mathematical definitions and do not require external datasets.

## 4. Results and evaluation

### Preliminary TSP implementation results

Two initial single-seed experiments were reproduced on 8 November 2026 using the original default BA settings.

Both used `eil51`, seed 42, and exactly 30,000 objective evaluations.

The initial best tour length was 1,352, and the published optimum was 426.

| Neighborhood | Final best tour length | Gap to optimum |
| --- | ---: | ---: |
| Swap | 622 | 46.01% |
| Segment reversal | 468 | 9.86% |

These preliminary trials were used to verify the original implementation. They are separate from the completed experimental study using Setting B.

### Completed TSP experiments

The full TSP study includes six datasets, two neighborhoods, and ten independent seeds, totaling **120 runs**.

Mean percentage gaps to the published optimum:

| Instance | Swap mean gap (%) | Segment reversal mean gap (%) |
| --- | ---: | ---: |
| eil51 | 34.41 | 5.54 |
| berlin52 | 35.46 | 7.50 |
| st70 | 63.02 | 8.07 |
| eil76 | 47.21 | 11.13 |
| kroA100 | 108.79 | 22.98 |
| ch150 | 153.47 | 52.32 |

The optimality gap is calculated as:

```text
gap (%) = 100 * (tour_length - optimum) / optimum
```

Segment reversal produced a shorter final tour than swap in all 60 paired instance-seed comparisons.

The results show that segment reversal performs better than swap under the tested BA settings and evaluation budget.

Performance also deteriorates for larger TSP instances, particularly `ch150`, where the segment reversal neighborhood achieved a mean gap of 52.32%.

These findings describe performance under the tested configuration rather than establishing general superiority across other algorithms or parameter settings.

### Completed continuous experiments

The continuous study includes four benchmark functions, dimensions 10 and 30, and ten seeds per case, totaling **80 runs**.

Mean final objective values:

| Function | Dimension 10 | Dimension 30 |
| --- | ---: | ---: |
| Sphere | 0.4368 | 5.731 |
| Rosenbrock | 89.66 | 2431 |
| Rastrigin | 39.13 | 267.5 |
| Ackley | 6.216 | 10.58 |

All four functions have a global minimum of zero.

The experiments demonstrate improvement from initialization, but final objectives generally become worse as dimensionality increases.

The fixed neighborhood radius also limits fine-grained local search near a minimum. The results do not establish convergence to the theoretical global optimum.

### Saved experiment records

The following files contain the complete Problem 1 raw results:

- `bees_optimization/results/raw/tsp_runs.jsonl`
- `bees_optimization/results/raw/continuous_runs.jsonl`
- `bees_optimization/results/raw/metadata.json`

Each experimental record contains:

- Problem instance or benchmark function.
- Neighborhood or dimension.
- Random seed.
- BA configuration.
- Initial best objective.
- Final best objective and solution.
- Number of objective evaluations.
- Runtime in seconds.
- Compressed best-so-far history.

The metadata includes the experiment environment, source revision, configurations, and dataset checksums.

The recorded runtime measures the optimization call only; data loading is excluded.

### Statistical summaries

Results are aggregated over ten independent seeds.

The summary tables include best, mean, and sample standard deviation of final objective values, as well as initial objective and runtime statistics.

Sample standard deviation uses the `n - 1` convention.

Convergence curves are aligned by objective evaluation count, not by algorithm iteration. Compressed histories are forward-filled when constructing the shared evaluation grid.

Full-precision tables are saved as CSV, with human-readable Markdown versions also provided.

### Generated figures

Five required figures have been generated:

| Figure | Description |
| --- | --- |
| `tsp_convergence_berlin52.png` | Mean TSP convergence for both neighborhoods |
| `tsp_convergence_ch150.png` | Mean TSP convergence for the largest TSP instance |
| `berlin52_best_route.png` | Best recorded berlin52 route, including return edge |
| `rastrigin_d10_convergence.png` | Mean continuous convergence for Rastrigin, D=10 |
| `continuous_d30_boxplots.png` | Distribution of final objectives for all four functions at D=30 |

The figures are stored in `bees_optimization/results/figures/`.

See [Problem 1 results](bees_optimization/results/README.md) for the complete output inventory and reproduction instructions.

## 5. Installation and reproduction

### Requirements

Use **Python 3.11 or newer**.

The optimization algorithms, experiment runner, dataset validation utility, and most tests use the Python standard library.

Matplotlib is required for generating figures and running the complete test suite.

The current project dependency is pinned in `requirements.txt`.

### Clone and install

From the terminal:

```bash
git clone https://github.com/e-KOP/acit4610-final-group-project.git
cd acit4610-final-group-project

python -m venv .venv
python -m pip install -r requirements.txt
```

Activate the virtual environment before installing dependencies when using one.

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

On Linux or macOS:

```bash
source .venv/bin/activate
```

The completed Problem 1 experiment and validation implementation must be checked out from a branch containing those changes until they are merged into `main`.

### Verify the benchmark datasets

Run:

```bash
python scripts/verify_data.py
```

This verifies the eleven original benchmark files against their committed SHA-256 checksums.

It does not execute any optimization algorithm.

### Run all automated tests

From the repository root:

```bash
python -m unittest discover -s bees_optimization/tests -v
```

The complete Problem 1 test suite contains 50 automated tests.

All 50 passed on 22 November 2026.

### Reproduce a single TSP experiment

```bash
python -m bees_optimization.bees.experiments tsp --instances berlin52 --neighborhoods segment_reversal --seeds 1
```

This reproduces the recorded berlin52 segment-reversal experiment using seed 1.

Expected final tour length:

```text
7833
```

The corresponding gap to the published optimum is approximately 3.86%.

Subset experiments are written to `bees_optimization/results/scratch/`, preserving the committed full experiment results.

### Reproduce a continuous experiment

```bash
python -m bees_optimization.bees.experiments continuous --functions sphere --dimensions 10 --seeds 0
```

This runs one Sphere experiment at dimension 10 using the configured BA parameters.

### Regenerate tables and figures

```bash
python -m bees_optimization.bees.output
```

This reads the committed raw experiment records and regenerates the summary tables and figures without rerunning the optimization algorithms.

The generated files are written to the existing results directories.

### Rerun the entire Problem 1 study

```bash
python -m bees_optimization.bees.experiments all
```

This executes all 200 required Problem 1 experiments.

**Warning:** The full experiment command writes directly to `results/raw/` and can overwrite the existing committed raw records and metadata.

Use a separate working copy when reproducing the complete study independently.

## 6. Independent validation

The project includes an independent experiment validation module:

`bees_optimization/bees/validate_results.py`

Run it from the repository root:

```bash
python -m bees_optimization.bees.validate_results
```

The validator independently checks:

- All 120 TSP and 80 continuous records are present.
- Each configuration includes exactly ten unique seeds.
- Every run uses the configured 30,000 objective evaluations.
- Recorded BA parameters match the experimental configurations.
- Every saved TSP tour is a valid permutation starting at city 1.
- TSP tour lengths match independently calculated EUC_2D distances.
- Continuous solutions satisfy dimension and bound requirements.
- Continuous objective values match independent calculations.
- Initial and final objectives agree with the saved histories.
- Best-so-far histories contain correctly ordered evaluations and never worsen.
- Summary tables match the underlying raw records.
- Sample standard deviations and mean values are correctly calculated.
- Stored experiment configurations and TSPLIB checksums match their sources.

All 200 committed experimental records passed independent validation on 22 November 2026.

### Automated test coverage

| Test file | Coverage |
| --- | --- |
| `test_algorithm.py` | Core TSP Bees Algorithm behavior |
| `test_tsp_data.py` | TSPLIB parsing, distances, neighborhoods, and TSP regression results |
| `test_search.py` | Shared search behavior, recruitment, retention, and evaluation budgets |
| `test_continuous.py` | Benchmark functions, dimensions, bounds, and continuous search |
| `test_results.py` | Independent result calculations, corrupted-record detection, and full experiment validation |
| `test_experiment_pipeline.py` | Configuration handling, history compression, small experimental batches, convergence alignment, and output regeneration |

The original implementation contained 28 automated tests.

An additional 22 tests were implemented to verify the experimental results and processing pipeline, bringing the total to **50 tests**.

The additional tests deliberately introduce invalid records to verify that incorrect tours, objective values, histories, settings, and experiment coverage are rejected.

Experiment-pipeline regression tests also regenerate all required statistical tables and figures in temporary directories without modifying the committed experimental results.

### Validation limitations

Validation confirms internal consistency, correct numerical calculations, and reproducibility of the saved outputs.

It does not independently establish that the selected BA parameters are optimal or that the optimization algorithms converge to the global optimum.

The preliminary parameter-selection evidence remains subject to final group review.

## 7. Remaining project work

Problem 1 implementation, experiments, output generation, and automated validation are completed.

Remaining work includes:

- Confirm the BA parameter-selection pilot evidence.
- Complete the portfolio data loader, objective evaluation, and constraint repair.
- Implement all three required Evolution Strategies.
- Validate portfolio feasibility, numerical calculations, and evaluation budgets.
- Execute the 450 required portfolio experiments.
- Generate portfolio statistical summaries and convergence plots.
- Review the combined project implementation and documentation.
- Complete the group-authored submission report and final submission.

The implementation progress is tracked in [docs/development.md](docs/development.md).

The [submission checklist](docs/requirements.md) summarizes the assignment requirements.

The combined 3,000-7,500-word report must be written by the group in accordance with the course's AI-use restrictions. AI-produced code must be appropriately marked, and assistance must be disclosed.

The [AI-use record](docs/ai_usage.md) documents assistance during development.

## 8. Related repositories

Previous ACIT4610 assignments:

- [Assignment 1: Job Shop Scheduling Problem](https://github.com/e-KOP/acit4610-assignment-1-jssp)
- [Assignment 2: Capacitated Facility Location Problem](https://github.com/e-KOP/acit4610-assignment-2-cflp)
