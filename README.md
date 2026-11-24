# ACIT4610 Final Group Project: Bees Algorithm and Evolution Strategies

The **Bees Algorithm (BA)** minimises the rounded tour length of six TSPLIB
instances and the value of four continuous benchmark functions, and three
**Evolution Strategies (ES)**, (1+1)-ES, (mu+lambda)-ES and (mu,lambda)-ES,
minimise **portfolio variance** subject to long-only, budget and minimum-return
constraints. Group number: **Group-8**. Group members: **Zhongye Xue, Syed
Mohammad Abdur-Rahman Tirmizey, Jakob Andreas Amtedal, Khoa Anh Huynh**.

Problem 1 uses one shared BA search loop for both TSP neighbourhoods and the
continuous functions; Problem 2 uses shared data loading, covariance, repair,
feasibility checks and evaluation counting for all three ES variants. Each
experiment pipeline saves raw records with provenance, checks them independently,
and generates summary tables and figures. All **650 required runs** were
completed with exactly 30,000 objective evaluations each: 200 BA runs, all
passing independent validation, and 450 ES runs with 450 valid final allocations.
Section 4 presents the results.

| Problem | Scope | Folder |
| --- | --- | --- |
| 1 | Bees Algorithm for TSP and continuous functions | [bees_optimization](bees_optimization/README.md) |
| 2 | (1+1)-ES, (mu+lambda)-ES and (mu,lambda)-ES for portfolio variance minimisation | [portfolio_optimization](portfolio_optimization/README.md) |

## 1. How the searches work

Both problems follow the same project workflow:

```text
Read and validate original benchmark data
    -> implement and validate objective functions
    -> implement optimization algorithms
    -> execute seeds 0-9 with exactly 30,000 objective evaluations
    -> save solutions and best-so-far histories
    -> generate statistical summaries and figures
    -> independently validate experimental results
    -> analyze and document performance
```

### Bees Algorithm

Example configuration: **berlin52**, **segment reversal**, seed **1**, Setting B
with **10 scouts, 3 selected sites, 1 elite site, 10 elite recruits and 5 recruits
per other selected site**: 27 evaluations per complete iteration, so
10 initial + 1,110 x 27 = 29,980, then 20 final recruits.

```text
Initialize and evaluate 10 scouts
    -> rank by objective; select 3 sites, the best 1 is elite
    -> recruit 10 neighbours at the elite site and 5 at each other selected site,
       always from the ORIGINAL site
    -> each site keeps the best of itself and its recruits
    -> replace the 7 unselected sites with fresh random scouts
    -> update the global best-so-far after every evaluation
    -> repeat until exactly 30,000 evaluations
```

### Evolution Strategies

Example configuration: `port1_alpha050`, **31 assets**, **R_min =
0.007184532258065**, seed **0**. The initial step size is `0.1 / sqrt(31) =
0.01796`.

```text
(1+1)-ES:   child = repair(parent + sigma * N(0, I))
            keep the child only if its variance is strictly lower
            sigma *= exp(1/3) after success, exp(-1/12) otherwise

(mu+lambda) / (mu,lambda), mu = 10, lambda = 70:
            two different random parents -> mean weights, geometric-mean step sizes
            -> self-adapt step sizes -> mutate -> repair -> evaluate
            plus: best 10 of parents + offspring;  comma: best 10 of offspring

All:        archive the best feasible allocation; return it after 30,000 evaluations
```

See section 1 of [Problem 1](bees_optimization/README.md#1-how-the-next-population-is-created)
and [Problem 2](portfolio_optimization/README.md#1-how-the-next-allocation-is-created)
for the full pipelines.

## 2. Algorithm design

| Block | BA: TSP | BA: continuous | ES: portfolio |
| --- | --- | --- | --- |
| Encoding | Permutation, city 1 fixed first | Real vector, D = 10 or 30 | Real weight vector, length n = 31-225 |
| Initialization | Uniform random permutations | Uniform within bounds | Uniform [0, 1], then repair |
| Variation | Swap or segment reversal around a selected site | +/-10% of domain width per coordinate, fixed radius | (1+1): scalar Gaussian mutation; population: recombination + self-adaptive mutation |
| Repair / validity | Every city exactly once | Clip to bounds | Simplex projection, then return repair |
| Evaluation | Rounded EUC_2D tour length with return edge | Unshifted function value | Variance `w^T Sigma w` |
| Replacement | Site keeps best of itself and recruits; fresh scouts elsewhere | Same | Strict improvement; plus or comma survivor selection |
| Best record | Global best-so-far | Same | Archive of the best feasible allocation |
| Termination | Exactly 30,000 evaluations | Same | Same |

Every evaluated candidate counts toward the budget, including initialization,
rejected candidates, fresh scouts and the final partial ES batch.

### Objectives and feasibility

```text
TSP:        minimise sum of d(i, i+1) over the closed tour,
            d(i,j) = floor(sqrt((xi-xj)^2 + (yi-yj)^2) + 0.5)
Continuous: minimise f(x), x within bounds; Sphere, Rosenbrock, Rastrigin, Ackley; f* = 0
Portfolio:  minimise w^T Sigma w,   Sigma_ij = s_i * s_j * C_ij
            subject to  w_i >= 0,  sum(w) = 1,  r^T w >= R_min
```

Python's built-in `round()` is not used for distances because its ties-to-even
behaviour differs from TSPLIB. Published optimal tour lengths and known
minimizers are used for evaluation and tests only, never inside the search. A
reported portfolio is feasible if `w_i >= -1e-8`, `abs(sum(w) - 1) <= 1e-8` and
`r^T w >= R_min - 1e-8`.

### Repair example

With mean returns 2%, 6%, 10% and `R_min = 4%`, the vector
`z = (0.7, 0.5, -0.1)` is projected to `q = (0.6, 0.4, 0.0)` with return 3.6%. The
return repair mixes in the highest-return asset with `beta = 0.0625`, giving
`w = (0.5625, 0.375, 0.0625)` and a return of exactly 4%. See
[Problem 2, section 2](portfolio_optimization/README.md#2-algorithm-design) for
the derivation and implementation choices, and
[Problem 1, section 2](bees_optimization/README.md#2-algorithm-design) for the
distance and neighbourhood examples.

## 3. Instances and experiment parameters

| Experiment | Cases | Variants | Seeds per case/variant | Required runs |
| --- | ---: | ---: | ---: | ---: |
| TSP | 6 instances | 2 neighbourhoods | 10 | 120 |
| Continuous BA | 4 functions x 2 dimensions | 1 | 10 | 80 |
| Portfolio ES | 5 datasets x 3 return targets | 3 | 10 | 450 |
| **Total** | | | | **650** |

Every run uses exactly **30,000 objective evaluations**, so the full project uses
**19,500,000 objective evaluations**. The experiments use seeds **0-9**; these
seeds are a project choice, as the assignment requires ten independent runs per
configuration.

| TSP instance | Cities | Distance type | Optimal tour length |
| --- | ---: | --- | ---: |
| eil51 | 51 | EUC_2D | 426 |
| berlin52 | 52 | EUC_2D | 7,542 |
| st70 | 70 | EUC_2D | 675 |
| eil76 | 76 | EUC_2D | 538 |
| kroA100 | 100 | EUC_2D | 21,282 |
| ch150 | 150 | EUC_2D | 6,528 |

| Portfolio dataset | Assets | Correlation records | R_min, alpha = 0.25 / 0.50 / 0.75 |
| --- | ---: | ---: | --- |
| port1 | 31 | 496 | 0.005344 / 0.007185 / 0.009025 |
| port2 | 85 | 3,655 | 0.003567 / 0.005643 / 0.007718 |
| port3 | 89 | 4,005 | 0.004048 / 0.005435 / 0.006822 |
| port4 | 98 | 4,851 | 0.004454 / 0.006034 / 0.007615 |
| port5 | 225 | 25,425 | -0.000137 / 0.001232 / 0.002602 |

All eleven original benchmark files are bundled unchanged (gzip decompression
only for TSPLIB); sources and SHA-256 checksums are in
[TSPLIB sources](bees_optimization/data/README.md) and
[OR-Library sources](portfolio_optimization/data/README.md). The continuous
functions need no dataset. Portfolio return targets are
`R_min(alpha) = (1-alpha)*R_eq + alpha*r_max` for alpha = 0.25, 0.50, 0.75.

| Algorithm | Settings | Configuration |
| --- | --- | --- |
| BA (Setting B) | `n_scouts` 10, `n_selected` 3, `n_elite` 1, `n_elite_recruits` 10, `n_other_recruits` 5 | [tsp.json](bees_optimization/configs/tsp.json), [continuous.json](bees_optimization/configs/continuous.json) |
| (1+1)-ES | sigma0 = 0.1/sqrt(n), 1/5th rule factors exp(1/3) and exp(-1/12), bounds [1e-8, 1] | [experiments.json](portfolio_optimization/configs/experiments.json) |
| (mu+lambda)-, (mu,lambda)-ES | mu 10, lambda 70, tau' = 1/sqrt(2n), tau = 1/sqrt(2 sqrt(n)), bounds [1e-8, 1] | [experiments.json](portfolio_optimization/configs/experiments.json) |

Setting B was selected through pilot comparisons on seeds 100-104, separate from
the reported seeds 0-9, against Setting A (30/10/3/10/5) and Setting C (6/2/1/5/3).
**The selection remains provisional until the group confirms the pilot
evidence.** The BA solver functions keep their original defaults of 30/10/3/10/5
when called directly; the experiment runner loads Setting B from the JSON files
and passes it explicitly. The TSP implementation accepts `swap` and
`segment_reversal`, with `reverse` as a compatible alias.

Runtime is the wall-clock time of the search call only; data loading is excluded.
Both metadata files record the source revision, environment and input checksums;
the portfolio metadata also records source-file and configuration hashes, and
`--resume` refuses to continue when any of them has changed.

## 4. Results and evaluation

**BA: 120 TSP and 80 continuous runs, all 200 validated; ES: 450 runs, 450 valid,
zero failures.** Each value summarises 10 independent runs with 30,000 evaluations
each. Lower is better for every objective.

- **TSP quality:** mean gap to the published optimum,
  `gap (%) = 100 * (tour_length - optimum) / optimum`.
- **Continuous quality:** mean final objective; the minimum of every function is 0.
- **Portfolio quality:** mean final archive-best variance over valid runs;
  compare only within the same dataset and return target.
- Sample standard deviations use the `n - 1` convention. Convergence curves are
  aligned by objective evaluation count, with compressed histories forward-filled.

### Problem 1: Bees Algorithm

| Instance | Swap mean gap (%) | Segment reversal mean gap (%) |
| --- | ---: | ---: |
| eil51 | 34.41 | 5.54 |
| berlin52 | 35.46 | 7.50 |
| st70 | 63.02 | 8.07 |
| eil76 | 47.21 | 11.13 |
| kroA100 | 108.79 | 22.98 |
| ch150 | 153.47 | 52.32 |

| Function | D = 10 | D = 30 |
| --- | ---: | ---: |
| Sphere | 0.4368 | 5.731 |
| Rosenbrock | 89.66 | 2431 |
| Rastrigin | 39.13 | 267.5 |
| Ackley | 6.216 | 10.58 |

![berlin52: mean best-so-far tour length for swap and segment reversal](bees_optimization/results/figures/tsp_convergence_berlin52.png)

- Segment reversal produced a shorter final tour than swap in all **60 of 60**
  paired instance-seed comparisons. The best berlin52 tour (seed 1) has length
  7,833, a gap of 3.86%.
- Gaps grow with instance size under the fixed budget, up to 52.32% on ch150 with
  segment reversal.
- Every continuous case improves strongly on its initial scouts, but final values
  become much worse from D = 10 to D = 30, and the fixed neighbourhood radius
  limits fine local search near a minimum.
- Two preliminary eil51 trials (8 November 2026, seed 42, original default
  settings, initial best 1,352) gave 622 (swap, 46.01%) and 468 (reversal, 9.86%).
  They verified the original implementation and are separate from the Setting B
  study.

Best, mean, standard deviation, initial objective and runtime for every case, the
other four figures and the discussion are in
[Problem 1, section 4](bees_optimization/README.md#4-results-and-evaluation).

### Problem 2: Evolution Strategies

Mean final variance at alpha = 0.50 over 10 runs (10/10 valid in every row):

| Case | Assets | (1+1)-ES | (mu+lambda)-ES | (mu,lambda)-ES |
| --- | ---: | ---: | ---: | ---: |
| port1_alpha050 | 31 | 1.524e-03 | 1.166e-03 | 1.166e-03 |
| port2_alpha050 | 85 | 3.714e-04 | 2.626e-04 | 2.678e-04 |
| port3_alpha050 | 89 | 4.692e-04 | 3.542e-04 | 3.492e-04 |
| port4_alpha050 | 98 | 7.247e-04 | 4.112e-04 | 4.305e-04 |
| port5_alpha050 | 225 | 7.266e-04 | 3.961e-04 | 3.773e-04 |

![port5_alpha050: mean archive-best variance against objective evaluations for the three ES variants](portfolio_optimization/results/figures/port5_alpha050_convergence.png)

- (mu+lambda)-ES reached a lower final variance than (1+1)-ES in all **150 of
  150** paired case-seed comparisons. Plus and comma are close: comma was lower
  in 84 of 150 pairs, within the run-to-run variation.
- The 1/5th rule shrinks the (1+1)-ES step size to its 1e-8 bound, leaving broad
  portfolios (on average 19.5 of 31 assets held on port1, 111 of 225 on port5)
  where the population variants find sparse ones (about 4 and 9-10 assets).
- Comma selection worsened the current population best in 29,038 of 64,200
  generations; plus selection never did. The archive best never worsens.

All 15 cases, the remaining observations and the discussion are in
[Problem 2, section 4](portfolio_optimization/README.md#4-results-and-evaluation).

**Discussion and conclusions:** the results describe the implemented algorithms
under the tested settings and a fixed 30,000-evaluation budget. They do not
establish general superiority over other algorithms or settings, convergence to
the global optimum, or future investment performance from historical statistics.

## 5. Reproduce the project

Use Python **3.11 or newer** with the pinned NumPy and Matplotlib versions in
[requirements.txt](requirements.txt). The BA algorithms, runner and data check use
the standard library; Matplotlib is needed for figures and the complete test
suites, and NumPy for Problem 2. Run every command from the **repository root**.
Until these changes are merged into `main`, check out the branch that contains
them.

```bash
git clone https://github.com/e-KOP/acit4610-final-group-project.git
cd acit4610-final-group-project
python -m venv .venv
source .venv/bin/activate            # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

# Check the eleven original benchmark files against their SHA-256 checksums
python scripts/verify_data.py

# Tests for both problems
python -m unittest discover -s bees_optimization/tests -v
python -m unittest discover -s portfolio_optimization/tests

# Problem 1: one run, then rebuild tables/figures and validate the 200 records
python -m bees_optimization.bees.experiments tsp --instances berlin52 --neighborhoods segment_reversal --seeds 1
python -m bees_optimization.bees.output
python -m bees_optimization.bees.validate_results

# Problem 2: one run, then validate records and rebuild the table and figure
python -m portfolio_optimization.portfolio pilot --dataset port1 --alpha 0.50 --variant mu_plus_lambda --seed 0 --budget 30000
python -m portfolio_optimization.portfolio summarize --runs portfolio_optimization/results/raw/portfolio_runs.jsonl

# Optional: rerun the complete studies (200 and 450 runs)
python -m bees_optimization.bees.experiments all
python -m portfolio_optimization.portfolio full --confirm-450
```

Validation includes **50 passing Problem 1 tests** (22 November 2026), independent
validation of all 200 BA records, and **124 Problem 2 tests**; see the
[BA](bees_optimization/tests/README.md) and [ES](portfolio_optimization/tests/README.md)
test documentation.

- The berlin52 command reproduces the recorded seed-1 run with final tour length
  **7833**. BA subset runs are written to `bees_optimization/results/scratch/`.
- `pilot` writes to `portfolio_optimization/results/scratch/`; its default budget
  is 300, so `--budget 30000` reproduces a recorded run.
- `bees.output` and `portfolio summarize` rebuild outputs from the saved records
  without rerunning the optimizers.
- **Warning:** `bees.experiments all` writes to `bees_optimization/results/raw/`
  and can overwrite the committed records; use a separate working copy. The
  portfolio `full` command never overwrites existing records and continues an
  interrupted run with `--resume`.

```text
.
├── README.md
├── requirements.txt
├── bees_optimization/
│   ├── bees/                 # BA solver, experiments, output, validation
│   ├── configs/              # TSP and continuous experiment settings
│   ├── data/tsplib/          # Six original TSP benchmark datasets
│   ├── tests/                # 50 algorithm and experiment tests
│   └── results/              # raw/ (200 records), tables/, figures/ (5)
├── portfolio_optimization/
│   ├── portfolio/            # Data, repair, feasibility, three ES variants, runner, CLI
│   ├── configs/              # Portfolio experiment settings
│   ├── data/or_library/      # Five original portfolio datasets
│   ├── tests/                # 124 data, operator, solver and pipeline tests
│   └── results/              # raw/ (450 records), tables/, figures/ (1)
├── scripts/verify_data.py    # Original dataset integrity verification
├── docs/                     # Requirements checklist, development log, AI-use record
└── report/                   # Group-authored submission report
```

### Remaining work and AI use

- Confirm the BA parameter-selection pilot evidence (Setting B).
- Review the combined implementation and documentation as a group.
- Write and check the combined 3,000-7,500-word report and complete the Inspera
  submission by 30 November 2026 at 12:00.

The report must be written by the group in accordance with the course's AI-use
restrictions; AI-produced code must be marked and its use disclosed. The
[AI-use record](docs/ai_usage.md) documents assistance during development,
[docs/development.md](docs/development.md) tracks implementation progress and
the [submission checklist](docs/requirements.md) summarises the assignment
requirements.

### Related repositories

- [Assignment 1: Job Shop Scheduling Problem](https://github.com/e-KOP/acit4610-assignment-1-jssp)
- [Assignment 2: Capacitated Facility Location Problem](https://github.com/e-KOP/acit4610-assignment-2-cflp)
