# Problem 2 comparative analysis (read-only)

This folder compares the three ES variants using the **saved** run records. It
never runs an optimizer for the reported results, never changes the raw JSONL,
and lives outside the folders covered by the experiment provenance check
(`portfolio/`, `tests/`, `configs/`, `data/`), so adding it cannot affect a
running or resumed experiment.

```bash
# Final analysis (requires all 450 runs)
python -m portfolio_optimization.analysis --runs portfolio_optimization/results/raw/portfolio_runs.jsonl

# Preliminary analysis of an incomplete or pilot file (every output is labelled PRELIMINARY)
python -m portfolio_optimization.analysis --runs PATH --out DIR --allow-partial

# Tests
python -m unittest discover -s portfolio_optimization/analysis/tests -v
```

Outputs go to `portfolio_optimization/results/analysis/` (or `--out`). The SHA-256
of the runs file is checked before and after, with CRLF normalized to LF
before hashing for cross-platform consistency. The checksum is recorded
in `analysis_metadata.json`.

## Outputs

| File | Content |
| --- | --- |
| `variant_summary.{csv,md}` | Per case and variant: valid runs; best, mean, median, SD and coefficient of variation of variance; mean runtime; assets held; effective number of assets; runs with the return constraint active; evaluations to reach 99% of the improvement; last improvement; improvement in the second half of the budget; for population ES, generations in which the population best got worse and the final population-vs-archive gap |
| `paired_comparisons.{csv,md}` | Per case, for plus vs comma, plus vs (1+1), comma vs (1+1): seed-by-seed wins, median and geometric-mean variance ratio, exact sign test and exact Wilcoxon signed-rank p-values |
| `mean_ranks.{csv,md}` | Mean rank of each variant over all cases and seeds (1 = lowest variance) |
| `convergence_all_cases.png` | Mean archive-best variance vs evaluations for all 15 cases (the required plot covers only port5_alpha050) |
| `relative_excess_boxplots.png` | Final variance as % above the best run of any variant, per case, so cases with different scales can be compared |
| `sparsity.png` | Assets held in the final allocation, per dataset, alpha and variant |
| `population_vs_archive_port5.png` | One seed of port5_alpha050: archive best vs current population best for (μ+λ)-ES and (μ,λ)-ES |
| `step_size/` | Optional (1+1)-ES step-size diagnostic: per-seed CSV and plot (see below) |

## Definitions and cautions

- **Paired runs.** Variants share the same seeds, cases, repair and budget, so the
  runs for one seed are compared directly (paired), which removes case-to-case
  differences in scale.
- **Statistical tests.** With 10 seeds the smallest possible two-sided p-value is
  2/1024 = 0.002 for both tests. 45 comparisons are made, so individual p-values
  are descriptive; consistent direction across cases (wins, ratios, ranks)
  carries more weight than any single test.
- **Held assets.** Weight above 1e-8. **Effective number of assets** is 1 / sum(w^2):
  k for k equal weights, close to 1 when one asset dominates.
- **Return constraint active.** Final return within 1e-10 (relative) of the target.
- **Stagnation measures** come from the saved archive history, which stores every
  change of the best-so-far value; they describe the archive, not the step size.

## Optional step-size diagnostic

The saved records contain no step sizes, so the (1+1)-ES step-size collapse
cannot be measured from them. `step_size.py` re-runs the **unchanged** (1+1)-ES for
one case and chosen seeds, observing each step-size update through a wrapper,
and writes a CSV and a plot to `results/analysis/step_size/`. With `--runs`, each
re-run is compared with the official record for the same seed; identical best
variance and weights confirm that the diagnostic observed exactly the official
run. It is a diagnostic, not part of the official dataset:

```bash
python -m portfolio_optimization.analysis.step_size --dataset port1 --alpha 0.5 --runs portfolio_optimization/results/raw/portfolio_runs.jsonl
python -m portfolio_optimization.analysis.step_size --dataset port5 --alpha 0.5 --runs portfolio_optimization/results/raw/portfolio_runs.jsonl
```