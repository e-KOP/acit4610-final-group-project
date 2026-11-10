# ACIT4610 Final Group Project: Bees Algorithm and Evolution Strategies

Study the Bees Algorithm (BA) on route planning and continuous functions, and
Evolution Strategies (ES) on constrained portfolio optimization.

**Status: TSP and continuous Bees Algorithm implemented.** Both use a shared
search loop with exact evaluation budgets. TSP includes validated TSPLIB loading
and both neighborhoods; continuous search supports Sphere, Rosenbrock, Rastrigin,
and Ackley at dimensions 10 and 30. All 28 automated tests pass, and all eight
continuous cases passed single-seed 30,000-evaluation smoke checks. Portfolio ES,
batch runners, saved experiment records, and figures remain to be implemented.

**Group number:** Group-8

**Group members:** Zhongye Xue, Syed Mohammad Abdur-Rahman Tirmizey,
Jakob Andreas Amtedal, and Khoa Anh Huynh.

## 1. How the project is organized

```text
Read and validate original benchmark data
    -> implement and check objectives and representations
    -> implement the required search algorithms
    -> run independent seeds with exact evaluation budgets
    -> save solutions and best-so-far histories
    -> reproduce summary tables and figures
```

| Problem | Scope | Folder |
| --- | --- | --- |
| 1 | BA for TSP (swap and segment reversal) and four continuous functions | [bees_optimization](bees_optimization/README.md) |
| 2 | (1+1)-ES, (mu+lambda)-ES, and (mu,lambda)-ES for portfolio variance | [portfolio_optimization](portfolio_optimization/README.md) |

Each problem follows the earlier assignments' layout: a small Python package,
`configs/`, `data/`, `tests/`, and `results/`. The `bees/` folder contains the
TSP and continuous implementations; the `portfolio/` folder contains its module plan.

```text
.
├── README.md
├── requirements.txt
├── bees_optimization/
│   ├── README.md
│   ├── bees/                 # TSP, continuous functions and moves, shared BA
│   ├── configs/              # TSP and continuous experiment specifications
│   ├── data/tsplib/          # Six original, decompressed .tsp files
│   ├── tests/                # Numerical, input, budget, and regression tests
│   └── results/              # Output plan; raw experiment records not yet saved
├── portfolio_optimization/
│   ├── README.md
│   ├── portfolio/            # Planned ES, objective, and repair modules
│   ├── configs/              # Portfolio experiment specification
│   ├── data/or_library/      # Five original portfolio files
│   ├── tests/                # Validation checklist
│   └── results/              # Required output inventory; no results yet
├── scripts/verify_data.py    # Offline byte-integrity check only
├── docs/                    # Requirements, development steps, AI-use record
└── report/                  # Location for the group's own combined report
```

## 2. Algorithm design

The [Problem 1 README](bees_optimization/README.md) documents the implemented TSP
and continuous search. The [Problem 2 README](portfolio_optimization/README.md)
specifies the ES work still to be implemented.

The TSP search ranks sites by tour length, recruits neighbors from each original
selected site, retains the best of that site and its recruits, and fills the
remaining population slots with fresh scouts. A separate best-so-far record
includes initialization. Every evaluated candidate counts toward the budget.

Keep data loading, evaluation, variation, search, experiment orchestration,
and output generation separate. Add modules when implementing their behavior;
avoid unused abstractions and duplicate shared logic within each problem.

## 3. Instances and experiment parameters

| Experiment | Cases | Variants | Seeds per case/variant | Runs |
| --- | ---: | ---: | ---: | ---: |
| TSP | 6 instances | 2 neighborhoods | 10 | 120 |
| Continuous BA | 4 functions x 2 dimensions | 1 | 10 | 80 |
| Portfolio ES | 5 datasets x 3 return targets | 3 | 10 | 450 |
| **Total** | | | | **650** |

Every required run uses **30,000 objective evaluations**, including initialization
and rejected candidates: **19,500,000 evaluations** for the complete project.
Stop exactly at the budget, allowing an incomplete final iteration or batch.

The initial project seed choice is **0-9**, matching assignment 2. The specification
requires ten independent seeds; it does not prescribe these particular integers.
Use the same list for compared variants. JSON files under each `configs/` folder
record the planned full experiment design. Their BA fields remain `null` and are
not loaded by the current solver. The TSP function currently defaults to 30
scouts, 10 selected sites, 3 elite sites, 10 recruits per elite site, and 5 per
other selected site. Both trial runs below use these defaults. Confirm and wire
the experiment configurations before running the full study. Both `segment_reversal`
and the original `reverse` name are accepted by the TSP function. Continuous BA
uses the same default site and recruitment counts.

All eleven required datasets are bundled. See the [TSPLIB sources](bees_optimization/data/README.md)
and [OR-Library sources](portfolio_optimization/data/README.md) for exact URLs and
checksums. Sphere, Rosenbrock, Rastrigin, and Ackley are evaluated from formulas;
they need no downloaded dataset.

## 4. Results and evaluation

Two **single-seed trials**, reproduced on 8 November 2026 with the TSP code from
commit `d8a02d9`, give the following results. Both use `eil51`, seed **42**, the
defaults above, and exactly **30,000 evaluations**. The initial best length is
1,352 and the published optimum is 426.

| Neighborhood | Final best tour length | Gap to optimum |
| --- | ---: | ---: |
| Swap (`swap`) | 622 | 46.01% |
| Segment reversal (`reverse`) | 468 | 9.86% |

These trials do not establish repeated-run performance and are not the required
120-run TSP experiment. Raw trial records are not yet committed; the command
below reproduces the lengths. Full tables, plots, and per-run records remain
pending; see the [BA output plan](bees_optimization/results/README.md) and
[ES output plan](portfolio_optimization/results/README.md).

Record seeds, settings, evaluation counts, runtime, initial and final best values,
best solutions, and best-so-far logs. Compare quality and variability under the
same budget. Use sample standard deviation (`n - 1`) as the project convention.
Define the timing scope and record dependency versions before benchmarking.
Keep pilot runs separate from the required experiments, and retain raw records.

## 5. Reproduce the repository setup

Use **Python 3.10 or newer**. The BA implementations, tests, and integrity-check
script use only the standard library. The checks below pass with Python **3.12.3**.

```bash
git clone https://github.com/e-KOP/acit4610-final-group-project.git
cd acit4610-final-group-project
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/verify_data.py
python -m unittest discover -s bees_optimization/tests -v
```

On Windows, activate with `.venv\Scripts\Activate.ps1`. The verifier checks all
eleven bundled files against committed SHA-256 hashes; it does not run a solver
or validate numerical algorithms. No network access is needed after cloning.

Run the two `eil51` trials from the repository root (Bash):

```bash
python - <<'PY'
from bees_optimization.bees.tsplib import (
    load_tsplib, validate_tsplib, create_distance_matrix, validate_tour,
)
from bees_optimization.bees.algorithm import bees_algorithm

metadata, coordinates = load_tsplib("bees_optimization/data/tsplib/eil51.tsp")
validate_tsplib(metadata, coordinates)
matrix = create_distance_matrix(coordinates)
for neighborhood in ("swap", "reverse"):
    result = bees_algorithm(
        matrix, neighborhood=neighborhood, seed=42, max_evaluations=30000,
    )
    validate_tour(result["best_tour"], len(coordinates))
    print(neighborhood, "length:", result["best_length"],
          "evaluations:", result["evaluations"])
PY
```

In PowerShell, save the Python block to a local script and run it with `python`.
The function returns the best tour, best length, initial best, evaluation count,
and history in memory. History starts after evaluating the initial population
(evaluation 30 with default settings), then records every subsequent evaluation.
Runtime measurement, file exports, batch commands, and plot reproduction remain
pending. Pin numerical and plotting dependency versions when introduced.

Run one continuous case from the repository root:

```bash
python - <<'PY'
from bees_optimization.bees.continuous import continuous_bees

result = continuous_bees("sphere", dimension=10, seed=42)
print("initial:", result["initial_best"], "best:", result["best_value"])
print("evaluations:", result["evaluations"])
print("vector:", result["best_vector"])
PY
```

Use `sphere`, `rosenbrock`, `rastrigin`, or `ackley`, with dimension `10` or `30`.
The result also contains `history` with the same evaluation indexing as TSP.
Each coordinate is initialized uniformly, perturbed independently by up to 10%
of its domain width, and clipped to its bounds. The neighborhood radius stays
fixed throughout the run. Known minimizers are used only in objective tests.
The 80-run continuous experiment remains pending; smoke checks are not the full study.

## 6. Build the project step by step

Start with the [development checklist](docs/development.md). Next steps are
reproducible experiment output and the Portfolio ES data, objective, and repair
foundations.

The [submission checklist](docs/requirements.md) maps the portfolio's shared
requirements. The combined report is written by the group and stored in
`report/`; the assignment does not permit AI-written report text. Keep the
[AI-use record](docs/ai_usage.md) current and mark AI-produced code.

Structure references: [assignment 1](https://github.com/e-KOP/acit4610-assignment-1-jssp)
and [assignment 2](https://github.com/e-KOP/acit4610-assignment-2-cflp).
