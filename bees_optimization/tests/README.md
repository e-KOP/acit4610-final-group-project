# BA validation

Run from the repository root:

```bash
python -m unittest discover -s bees_optimization/tests -v
```

All **28 tests** pass on 10 November 2026 using Python 3.12.3 and the standard library.

| File | Coverage |
| --- | --- |
| `test_algorithm.py` | Original six TSP tests: selection, recruitment, execution, history, partial iterations, invalid neighborhood |
| `test_tsp_data.py` | Six datasets; malformed TSPLIB input; rounded distances and closed tours; swap and reversal; invalid matrices; seed-42 full-budget regression results |
| `test_search.py` | Independently counted objective calls and observed minima; rejected evaluations; original-site recruitment; boundary population settings; invalid count types and ranges in both adapters |
| `test_continuous.py` | Four functions at minimizers and nonoptimal points; configuration bounds; independent perturbations and clipping; domain preservation; deterministic runs at dimensions 10 and 30 |

The full-budget TSP regression retains eil51 lengths 622 for swap and 468 for
segment reversal at seed 42. Additional manual smoke checks cover all eight
continuous function/dimension combinations at 30,000 evaluations each. These
checks do not replace the required multi-seed experiments.

Remaining validation concerns the experiment layer: configuration loading,
per-run exports, runtime provenance, complete case/seed coverage, and plots
recomputed from saved results. Dataset integrity can be checked separately with
`python scripts/verify_data.py`.
