# Problem 2: Portfolio Optimization via Evolution Strategies

**Status: all three ES variants implemented and tested; the 450 required runs
are pending.** Data loading, evaluation, repair, feasibility checks, the
experiment runner, outputs and the command-line interface are implemented. The
solvers are verified on all 15 cases (see [section 6](#6-verification-and-known-limitations)).

## 1. How the search will work

```text
Read returns, standard deviations, and correlations -> construct covariance
    -> calculate a case's minimum return target
    -> initialize and repair weights -> evaluate variance
    -> recombine / mutate -> repair -> evaluate -> select survivors
    -> retain the best feasible allocation in a separate archive
    -> stop at 30,000 evaluations and return the archive best
```

## 2. Algorithm design

For mean returns `r`, standard deviations `s`, and correlations `C`, construct
`Sigma_ij = s_i * s_j * C_ij`. Minimize **variance** `w^T Sigma w`, with
`w_i >= 0`, `sum(w) = 1`, and `r^T w >= R_min`. Use decimal returns.

Repair every candidate before evaluating it:

1. Project onto the probability simplex: `q_i = max(z_i - theta, 0)`, where
   `theta` makes the weights sum to one.
2. If `r^T q < R_min`, choose asset `j` with maximum return and set
   `beta = (R_min - r^T q) / (r_max - r^T q)`,
   `w = (1-beta)*q + beta*e_j`. Otherwise use `w = q`.

| Component | (1+1)-ES | Population ES |
| --- | --- | --- |
| Initialization | Independent uniform [0,1] weights, then repair | Same for each of 10 parents |
| Step size | Scalar, initially `0.1/sqrt(n)` | Coordinate vector, initially `0.1/sqrt(n)` |
| Parents per child | Current parent | Two uniformly selected parents |
| Recombination | None | Arithmetic mean of weights; geometric mean of coordinate step sizes |
| Mutation | Scalar step size times independent standard normals | Adapt coordinate step sizes, then use fresh independent standard normals |
| Selection | Replace parent only for strictly lower variance | Best 10 from parents + offspring (plus) or offspring only (comma) |
| Offspring | 1 per trial | 70 per full batch |

For (1+1)-ES multiply the step size by `exp(1/3)` after a strict improvement and
by `exp(-1/12)` otherwise. For population ES use
`sigma'_i = sigma_recombined_i * exp(tau_prime*Z0 + tau*Zi)`, with
`tau_prime = 1/sqrt(2*n)` and `tau = 1/sqrt(2*sqrt(n))`.
Share `Z0` across a child's coordinates; all `Zi` are independent. Mutation uses
fresh normal draws. Clamp updated step sizes to `[1e-8, 1.0]` and store them with
the child.

All variants maintain a separate best feasible archive, including initialization.
In comma selection the archive is for reporting only and must not enter parent
selection. A partial last batch still updates the archive before stopping.

## 3. Instances and experiment parameters

| Dataset | Assets | Correlation records |
| --- | ---: | ---: |
| port1.txt | 31 | 496 |
| port2.txt | 85 | 3,655 |
| port3.txt | 89 | 4,005 |
| port4.txt | 98 | 4,851 |
| port5.txt | 225 | 25,425 |

With equal weights `u_i = 1/n`, calculate `R_eq = r^T u` and
`R_min(alpha) = (1-alpha)*R_eq + alpha*r_max` for **0.25, 0.50, 0.75**.
Case names run from `port1_alpha025` through `port5_alpha075`.

[configs/experiments.json](configs/experiments.json) records **15 cases x 3 variants
x seeds 0-9 = 450 runs**, each with **30,000 evaluations**. Count initialization
and every evaluated candidate, including rejected offspring. Use identical cases,
repair, seeds, and budgets for the three variants.

Parse 1-based correlation indices into Python's 0-based indices and mirror each
record into both halves of `C`. For `port1.txt`, check approximately:

| Check | Expected value |
| --- | ---: |
| Equal-allocation return | 0.003504064516129 |
| Equal-allocation variance | 0.001130937943724 |
| Minimum return at alpha=0.50 | 0.007184532258065 |

Every reported solution must have `w_i >= -1e-8`, `abs(sum(w)-1) <= 1e-8`,
and `r^T w >= R_min - 1e-8`.

## 4. Results and evaluation

See the [output plan](results/README.md). Use valid runs for variance statistics,
report the valid count out of ten, and average runtime across all ten runs.
Compare variance within the same dataset and target. Discuss variability,
convergence, runtime, stagnation, selection, adaptation, problem size, and repair.
Comma selection can worsen the current population best while the archive best
cannot worsen. These historical statistics do not establish future investment
performance.

## 5. Reproduce the project

## 5. Reproduce the project

Run every command from the **repository root** (Python 3.11+ for the figures).

```bash
python -m pip install -r requirements.txt
python scripts/verify_data.py                                  # check the five data files
python -m unittest discover -s portfolio_optimization/tests    # all portfolio tests

# One test case (written to portfolio_optimization/results/scratch/)
python -m portfolio_optimization.portfolio pilot --dataset port1 --alpha 0.50 --variant mu_plus_lambda --seed 0 --budget 30000

# The full required set: 15 cases x 3 variants x seeds 0-9 = 450 runs
python -m portfolio_optimization.portfolio full --confirm-450

# Validate saved records and build the summary table and convergence plot
python -m portfolio_optimization.portfolio summarize --runs portfolio_optimization/results/raw/portfolio_runs.jsonl
```

`--resume` continues an interrupted pilot or full run without repeating finished
runs; existing result files are never overwritten. See
`python -m portfolio_optimization.portfolio --help` for all options.

The solvers can also be called directly from Python:

```python
from portfolio_optimization.portfolio.data import load_portfolio
from portfolio_optimization.portfolio.evaluation import minimum_return_target
from portfolio_optimization.portfolio.one_plus_one import solve_one_plus_one
from portfolio_optimization.portfolio.population_es import solve_population

data = load_portfolio("portfolio_optimization/data/or_library/port1.txt")
target = minimum_return_target(data.returns, 0.50)
result = solve_one_plus_one(data.returns, data.covariance, target, seed=0)
result = solve_population(data.returns, data.covariance, target, seed=0,
                          selection="plus")      # or "comma"
print(result["best_variance"], result["best_return"])
```

See also the [data sources](data/README.md), [module overview](portfolio/README.md),
[output plan](results/README.md) and [validation checklist](tests/README.md).

## 6. Verification and known limitations

`tests/test_solver_integration.py` runs all **5 datasets x 3 alpha values x 3
variants** (seed 0, 1,000 evaluations) and checks every result independently with
the shared `evaluation` and `feasibility` functions: feasible weights, the return
constraint (including all alpha = 0.75 cases), exact budgets, recomputed variance
and return, archive histories equal to the running minimum of every evaluated
candidate, generation checkpoints, plus/comma survivor selection, reproducibility,
and acceptance by the experiment runner. `test_one_plus_one.py` and
`test_population_es.py` test the operators in isolation, including hand-calculated
recombination and self-adaptation with fixed random draws.

**Implementation choices where the specification leaves room**

| Topic | Choice |
| --- | --- |
| Parent choice for recombination | Two **different** parents, uniformly at random (without replacement) |
| What is stored after repair | The repaired weights (they are recombined and mutated later); step sizes are stored as adapted, they are not repaired |
| Ties in survivor selection | Stable sort: on equal variance, parents are kept before offspring, earlier offspring before later |
| Ties in (1+1)-ES | A child with **equal** variance is rejected (strictly lower required) and counts as a failure for the 1/5th rule |
| Budget smaller than 10 | Population initialization stops at the budget and the best evaluated parent is returned |
| Final partial batch | Evaluated and archived; no survivor selection follows, because the budget is used up |
| Variance in the search loop | Computed with NumPy (`w @ Sigma @ w`); repair and feasibility use the shared pure-Python functions. The runner recomputes the reported variance with `evaluation.portfolio_variance` |
| Random numbers | `numpy.random.default_rng(seed)`. With the same seed, plus and comma make identical draws until the first survivor selection (evaluations 1-80), so both start from the same population |
| Extra output | Population variants also return `population_best`: the best variance in the parent population at each generation (evaluations 10, 80, 150, ... 29,970). It shows that comma selection can lose its best parent while the archive cannot worsen |

**Observed limitations** (single pilot runs, seed 0; to be confirmed by the full
experiment)

- **(1+1)-ES step-size collapse.** The simplex projection pulls many mutated
  children back, so only about 16-20% of trials succeed, at or below the 1/5
  target, and the rule keeps shrinking the step size. It reaches the lower bound
  of 1e-8 after about 5,000 trials on port1 and 21,000-26,000 trials on port5;
  afterwards improvements are microscopic. The (1+1)-ES then keeps almost every
  asset in the portfolio (30 of 31 on port1, about 205 of 225 on port5), whereas
  the population variants find sparse portfolios (3-9 assets) with clearly lower
  variance.
- **Return target not always active.** For port5 at alpha = 0.25 the target is
  negative (-0.000137), and the lowest-variance portfolios found exceed it. For
  port1 the best portfolios sit exactly on the target, so the return repair
  shapes the search there.
- **Comma selection discards good parents.** In one port5 run the comma
  population's best variance got worse in 193 of 428 generations; the archive is
  unaffected.
- **Cross-platform reproducibility.** Runs are identical for the same seed on the
  same machine. NumPy's matrix products can differ in the last bits between
  platforms, which could change a trajectory; pilot results matched to every
  printed digit between the Windows and Linux machines used during development.
- **Runtime.** About 1-2 s per port1 run and 5-10 s per port5 run on a laptop;
  the pure-Python repair, not the variance, dominates the cost per evaluation.
