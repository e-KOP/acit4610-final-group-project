
# Problem 1: Experimental Results

## Status

The required Bees Algorithm experiments have been completed for both TSP and continuous optimization.

All results were generated using 30,000 objective evaluations per run, with seeds 0-9 and the parameter configuration recorded in `configs/`.

| Experiment | Configurations | Seeds | Runs |
| --- | ---: | ---: | ---: |
| TSP | 6 instances x 2 neighborhoods | 10 | 120 |
| Continuous | 4 functions x 2 dimensions | 10 | 80 |
| Total | 20 | 10 | 200 |

## Results structure

- `raw/tsp_runs.jsonl`: All 120 TSP experiment records.
- `raw/continuous_runs.jsonl`: All 80 continuous experiment records.
- `raw/metadata.json`: Experiment configuration, environment, source revision and input checksums.
- `tables/tsp_summary.csv`: Full-precision TSP statistics.
- `tables/continuous_summary.csv`: Full-precision continuous statistics.
- `tables/*.md`: Human-readable summary tables.
- `figures/`: Five generated figures.

Each raw record contains its configuration, seed, initial best objective, final solution, final objective, evaluation count, runtime and compressed best-so-far history.

The compressed history retains every improvement and the initial and final evaluations.

## Figures

| Figure | Description |
| --- | --- |
| `tsp_convergence_berlin52.png` | Mean best-so-far convergence for both TSP neighborhoods |
| `tsp_convergence_ch150.png` | Mean best-so-far convergence on the largest TSP instance |
| `berlin52_best_route.png` | Best recorded berlin52 route, including return edge |
| `rastrigin_d10_convergence.png` | Mean convergence for Rastrigin at D=10 |
| `continuous_d30_boxplots.png` | Final objective distributions for all four functions at D=30 |

## Reproduce the results

Run from the repository root.

Install the required dependencies:

```bash
python -m pip install -r requirements.txt
```

Verify the benchmark data:

```bash
python scripts/verify_data.py
```

Run all existing and additional automated tests:

```bash
python -m unittest discover -s bees_optimization/tests -v
```

Regenerate the summary tables and figures from the saved raw results:

```bash
python -m bees_optimization.bees.output
```

To rerun the entire experiment set:

```bash
python -m bees_optimization.bees.experiments all
```

**Warning:** The full experiment command writes to `results/raw/` and can overwrite the committed results and metadata. Use a separate working copy when reproducing the full experiment.

For a single experimental run, use the subset arguments. Subset runs are saved under `results/scratch/`.

## Independent result validation

Run:

```bash
python -m bees_optimization.bees.validate_results
```

The validator independently checks:

- Complete coverage of all 200 required runs and unique seeds.
- Exact evaluation budgets and recorded BA settings.
- Valid TSP tours and independently recalculated EUC_2D lengths.
- Continuous variable bounds and independently calculated objectives.
- Initial and final objective consistency.
- Monotonically non-increasing best-so-far histories.
- Full-precision summary statistics, including sample standard deviation.
- Experiment configuration provenance and TSPLIB input checksums.

The validation and experiment-pipeline tests are implemented in:

- `tests/test_results.py`
- `tests/test_experiment_pipeline.py`

All 50 automated tests passed on 22 November 2026.

## Interpretation

TSP performance is evaluated using tour length and percentage gap to the published optimum. Continuous performance is evaluated using the final objective value.

The two neighborhoods are evaluated under identical budgets and seeds. Continuous experiments compare dimensions 10 and 30.

Results should be interpreted in relation to the fixed evaluation budget, chosen BA parameters and neighborhood definitions. Parameter selection is documented as provisional until the group confirms the original pilot evidence.

Runtime measurements cover the optimization calls and exclude dataset loading. Regenerating figures does not rerun the optimizers.
