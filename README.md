# ACIT4610 Final Group Project: Bees Algorithm and Evolution Strategies

Study the Bees Algorithm (BA) on route planning and continuous functions, and
Evolution Strategies (ES) on constrained portfolio optimization.

**Status: repository scaffold and benchmark data only.** Algorithms, experiment
runners, tests of algorithm behavior, and results have not been implemented.
Group number and members: to be confirmed against the approved Canvas group.

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
`configs/`, `data/`, `tests/`, and `results/`. Package folders currently contain
responsibility maps, not placeholder algorithm implementations.

```text
.
├── README.md
├── requirements.txt
├── bees_optimization/
│   ├── README.md
│   ├── bees/                 # Planned BA, TSP, and function modules
│   ├── configs/              # TSP and continuous experiment specifications
│   ├── data/tsplib/          # Six original, decompressed .tsp files
│   ├── tests/                # Validation checklist
│   └── results/              # Required output inventory; no results yet
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

The problem READMEs describe the required representations, moves, constraints,
and selection rules. These are implementation specifications, not claims that
the algorithms are already available.

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
record the design. BA population, site-selection, and recruitment counts are
`null` until the group chooses them; configurations are not runnable yet.

All eleven required datasets are bundled. See the [TSPLIB sources](bees_optimization/data/README.md)
and [OR-Library sources](portfolio_optimization/data/README.md) for exact URLs and
checksums. Sphere, Rosenbrock, Rastrigin, and Ackley are evaluated from formulas;
they need no downloaded dataset.

## 4. Results and evaluation

**No experiments have been run.** The required tables, plots, and per-run records
are listed in the [BA output plan](bees_optimization/results/README.md) and
[ES output plan](portfolio_optimization/results/README.md).

Record seeds, settings, evaluation counts, runtime, initial and final best values,
best solutions, and best-so-far logs. Compare quality and variability under the
same budget. Use sample standard deviation (`n - 1`) as the project convention.
Define the timing scope and record dependency versions before benchmarking.
Keep pilot runs separate from the required experiments, and retain raw records.

## 5. Reproduce the repository setup

Use **Python 3.10 or newer**. The current integrity-check script uses only the
standard library; there are no third-party dependencies yet.
The setup utility was checked with Python **3.12.3**.

```bash
git clone https://github.com/e-KOP/acit4610-final-group-project.git
cd acit4610-final-group-project
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/verify_data.py
```

On Windows, activate with `.venv\Scripts\Activate.ps1`. The verifier checks all
eleven bundled files against committed SHA-256 hashes; it does not run a solver
or validate numerical algorithms. No network access is needed after cloning.

Commands for one optimization run, all experiments, and figure reproduction will
be added alongside their implementations. There is deliberately no working
solver command at this point. Pin the versions of numerical and plotting
libraries in `requirements.txt` when the group first uses them.

## 6. Build the project step by step

Start with the [development checklist](docs/development.md). The next task is
implementing and validating the data loaders and objective functions.

The [submission checklist](docs/requirements.md) maps the portfolio's shared
requirements. The combined report is written by the group and stored in
`report/`; the assignment does not permit AI-written report text. Keep the
[AI-use record](docs/ai_usage.md) current and mark AI-produced code.

Structure references: [assignment 1](https://github.com/e-KOP/acit4610-assignment-1-jssp)
and [assignment 2](https://github.com/e-KOP/acit4610-assignment-2-cflp).
