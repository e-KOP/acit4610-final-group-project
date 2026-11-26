# ES validation

Run from the repository root:

```bash
python -m unittest discover -s portfolio_optimization/tests
```

The suite contains **149 tests** in 12 files; all passed on 24 November 2026.

| File | Tests | Coverage |
| --- | ---: | --- |
| `test_data.py` | 12 | All five datasets; port1 checkpoints; a small manual example; incomplete files, duplicate pairs, invalid indices, values, diagonals, counts and non-finite inputs |
| `test_evaluation.py` | 9 | Hand-calculated return and variance; minimum-return targets; port1 checkpoints; invalid dimensions, alpha, empty and non-finite inputs |
| `test_repair.py` | 11 | Simplex projection (already valid, negative, zero, all-negative weights) and return repair (already feasible, hand-calculated, target at r_max, impossible target, all dataset targets); inputs not modified |
| `test_feasibility.py` | 10 | Final checks at tolerance 1e-8, independent of the search code: negative weights, budget sum, return target, tolerance, invalid inputs |
| `test_one_plus_one.py` | 11 | 1/5th rule factors and neutral rate, step-size clamp, known two-asset optimum, exact budget (including budget 1), every evaluation counted, archive never worsens, reproducibility |
| `test_population_es.py` | 14 | Recombination, self-adaptation and mutation with fixed draws; clamping; survivor selection and exact budgets with partial last batches. The (μ+λ)-ES population best never worsens. The (μ,λ)-ES population best can worsen while its archive best cannot |
| `test_solver_integration.py` | 14 | All 5 datasets x 3 alpha values x 3 variants at 1,000 evaluations, checked independently |
| `test_experiments.py` | 19 | All three variants; rejection of wrong budgets, variances, returns, infeasible weights and bad histories; saved records and resume; provenance sidecar; recovery from torn or tampered records |
| `test_output.py` | 8 | Partial and complete summaries, duplicates, wrong objectives, failed runs excluded from variance statistics, port5 plot, invalid JSON |
| `test_provenance.py` | 8 | Exact-byte SHA-256, identity of inputs and environment, changed code or data blocks resume, manifest disagreement, overwrite refusal |
| `test_results.py` | 25 | Independent result validator: OR-Library parser and port1 checkpoints, hand-calculated example, coverage, duplicates, constraints, recomputed values, histories, population histories, summary table, provenance, partial sets, read-only behaviour, and the committed 450 runs |
| `test_cli.py` | 8 | `pilot`, `full` and `summarize` dispatch, `--confirm-450` requirement, invalid budget, missing solver |

The checks cover: initialization and rejected candidates counting toward the
budget; the partial final batch contributing to the archive with an exact 30,000
stop; an archive that never worsens; and saved allocations that reproduce their
saved variance and return. Dataset checksums can be checked separately with
`python scripts/verify_data.py`.
