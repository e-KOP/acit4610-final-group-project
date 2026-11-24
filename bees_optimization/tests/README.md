# BA validation

Run from the repository root:

```bash
python -m unittest discover -s bees_optimization/tests -v
```

All **50 tests** passed on 22 November 2026. The first 28 (the four original
files) passed on 10 November 2026 using Python 3.12.3 and the standard library;
the experiment-layer tests were added with the runner and validator.

| File | Tests | Coverage |
| --- | ---: | --- |
| `test_algorithm.py` | 6 | Original six TSP tests: selection, recruitment, execution, history, partial iterations, invalid neighborhood |
| `test_tsp_data.py` | 8 | Six datasets; malformed TSPLIB input; rounded distances and closed tours; swap and reversal; invalid matrices; seed-42 full-budget regression results |
| `test_search.py` | 5 | Independently counted objective calls and observed minima; rejected evaluations; original-site recruitment; boundary population settings; invalid count types and ranges in both adapters |
| `test_continuous.py` | 9 | Four functions at minimizers and nonoptimal points; configuration bounds; independent perturbations and clipping; domain preservation; deterministic runs at dimensions 10 and 30 |
| `test_results.py` | 15 | Independent result calculations, integrity checks, deliberately invalid records, and full validation of the 200 committed records |
| `test_experiment_pipeline.py` | 7 | Configuration, history compression, small experiment batches, convergence alignment, and regeneration of all tables and figures in temporary directories |

The full-budget TSP regression retains eil51 lengths 622 for swap and 468 for
segment reversal at seed 42 with the original default settings. Dataset
integrity can be checked separately with `python scripts/verify_data.py`, and
the saved records with `python -m bees_optimization.bees.validate_results`.
