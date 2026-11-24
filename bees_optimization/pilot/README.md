# Bees Algorithm setting-selection pilot (supplemental)

This pilot documents the group's selection of **Setting B** for both required
Problem 1 parts. It is **not** part of the official 200-run experiment dataset.
The pilot was originally conducted on 20 November 2026 and re-run on
24 November 2026 by a group member using the committed BA implementation.
The following rounded numbers were supplied by that member. The script
`run_pilot.py` regenerates run-level records and summaries independently.

## Protocol

- Three settings, shown as **scouts / selected / elite / elite recruits / other recruits**:
  - **A:** 30 / 10 / 3 / 10 / 5
  - **B:** 10 / 3 / 1 / 10 / 5
  - **C:** 6 / 2 / 1 / 5 / 3
- Seeds **100–104** (five per case), separate from official seeds 0–9.
- Exactly **30,000 objective evaluations** per run, with identical seed lists
  for each setting.
- TSP: six TSPLIB instances, **both** swap and segment-reversal neighborhoods.
- Continuous: four functions at dimensions 10 and 30.
- Total: **300 pilot runs** (180 TSP; 120 continuous), distinct from the 200
  official Problem 1 runs.

## Reproduced pilot observations

TSP segment-reversal **mean gap (%)**, averaged over five seeds per instance:

| Setting | eil51 | berlin52 | st70 | eil76 | kroA100 | ch150 | Mean of six instances |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 8.7 | 11.7 | 22.8 | 26.1 | 72.4 | 129.8 | 45.2 |
| B | 5.5 | 5.9 | 8.7 | 12.6 | 18.8 | 54.2 | 17.6 |
| C | 6.8 | 8.2 | 9.0 | 11.0 | 18.4 | 44.6 | 16.3 |

TSP **swap** mean gap across the same six instances: A **102.4%**, B
**75.7%**, C **74.4%**.

For the continuous benchmarks, **B achieved the lowest mean final error in six
of eight** function/dimension cases: Sphere D=30, Rosenbrock D=10 and D=30,
Rastrigin D=10 and D=30, and Ackley D=10. A performed best on Sphere D=10;
C performed best on Ackley D=30 by a small margin.

**Interpretation:** Setting A was markedly worse in this pilot. B and C were
closer: C had the lower TSP mean, influenced strongly by ch150, while B
performed better on the three smallest TSP instances and most continuous
cases. The group fixed **B** as a common setting for both parts because it
performed best on most continuous cases and was competitive on TSP.

The pilot is small (five seeds), with no formal significance analysis. It
**does not** establish that B is universally best or that the B–C difference is
statistically significant. Differences in how settings distribute evaluations
across sites and iterations are plausible mechanisms, not confirmed causes.

## Reproduce (does not overwrite official results)

Run from the repository root:

```powershell
# Optional quick check: 6 runs at 100 evaluations each
python -m bees_optimization.pilot.run_pilot --smoke

# Full independent pilot: 300 runs at 30,000 evaluations each
python -m bees_optimization.pilot.run_pilot
```

The full run writes only to
`bees_optimization/results/scratch/ba_pilot_full/` (ignored by Git), including:

- `pilot_runs.jsonl`: per-run records with settings, seed, results and histories
- `tsp_by_instance.csv`: mean tour length and gap by setting, instance and move
- `continuous_by_case.csv`: mean error by setting, function and dimension
- `pilot_summary.md`: regenerated aggregate comparisons
- `pilot_metadata.json`: seeds, settings, budget, cases and total run count

If an output directory already exists, the script refuses to overwrite it.
For a new run, supply another **unused** location under `results/scratch/` using
`--out bees_optimization/results/scratch/ba_pilot_repeat`.

The original experiment configuration JSON files and the 200 official raw
results are intentionally unchanged; their hashes and metadata refer to the
original saved experiment. The old `selection_note` in the configuration JSON
is a historical provenance field and is not modified to reflect the later
verification of the pilot.
