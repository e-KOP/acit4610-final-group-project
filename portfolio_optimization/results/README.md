# Problem 2: Experimental Results

## Status

All required ES experiments have been completed: **450 runs, 450 valid final
allocations**, each with exactly 30,000 objective evaluations, seeds 0-9 and the
settings in `configs/experiments.json`. The records were produced by
`python -m portfolio_optimization.portfolio full --confirm-450` from a clean
source tree (`git_source_dirty: false` in the metadata).

| Experiment | Configurations | Seeds | Runs |
| --- | ---: | ---: | ---: |
| (1+1)-ES | 5 datasets x 3 alpha values | 10 | 150 |
| (mu+lambda)-ES | 5 datasets x 3 alpha values | 10 | 150 |
| (mu,lambda)-ES | 5 datasets x 3 alpha values | 10 | 150 |
| Total | 45 | 10 | 450 |

## Results structure

- `raw/portfolio_runs.jsonl`: all 450 run records.
- `raw/portfolio_runs.metadata.json`: configuration, environment, Git revision,
  source-file hashes, configuration hash and dataset checksums.
- `tables/portfolio_summary.csv`: full-precision summary, 45 rows.
- `tables/portfolio_summary.md`: human-readable summary table.
- `figures/port5_alpha050_convergence.png`: mean archive-best variance against
  evaluations for all three variants.
- `analysis/`: supplemental comparative tables, diagnostic plots and
  analysis metadata; see [analysis documentation](../analysis/README.md).
- `scratch/`: disposable pilot and partial runs; not committed.

Each raw record contains the case, dataset, asset count, alpha, target, variant,
settings, seed, budget, evaluation count, best weights, expected return, variance,
validity, runtime and compressed archive-best history. Population-variant records
also contain `population_best`, the best parent variance after each generation.

| Output | Content |
| --- | --- |
| Summary (45 rows) | Case, variant, asset count, target, best/mean/SD variance, valid-run count/rate, mean runtime |
| Convergence (1 plot) | port5_alpha050; mean archive-best variance across ten seeds against evaluations; all three variants |

Variance statistics use only valid runs. The valid-run count is reported out of
ten, and mean runtime uses all ten runs.

## Reproduce the results

Run from the repository root.

```bash
# Validate the saved records and rebuild the table and figure
python -m portfolio_optimization.portfolio summarize --runs portfolio_optimization/results/raw/portfolio_runs.jsonl

# Independently check the records, summary table and provenance (read-only)
python -m portfolio_optimization.portfolio.validate_results

# Regenerate supplemental analysis without replacing committed outputs
python -m portfolio_optimization.analysis --runs portfolio_optimization/results/raw/portfolio_runs.jsonl --out portfolio_optimization/results/scratch/analysis_review

# Rerun the full study (resume-safe; existing files are never overwritten)
python -m portfolio_optimization.portfolio full --confirm-450
```

`summarize` rejects incomplete or invalid record sets unless `--allow-partial` is
given; partial reports are written to `scratch/reports/`. To rerun the full study
independently, use a separate working copy, because `full` writes to
`raw/portfolio_runs.jsonl`.
