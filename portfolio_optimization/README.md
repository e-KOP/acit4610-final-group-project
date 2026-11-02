# Problem 2: Portfolio Optimization via Evolution Strategies

**Status: specification, data, and folder structure only.** All three required
ES variants are pending implementation; no portfolio experiments have been run.

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

From the repository root, run `python scripts/verify_data.py` to check the bundled
files. See the [root setup instructions](../README.md#5-reproduce-the-repository-setup),
[data sources](data/README.md), [module plan](portfolio/README.md), and
[validation checklist](tests/README.md). Single-run, batch, and plotting commands
will be added when implemented.
