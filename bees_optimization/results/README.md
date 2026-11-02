# Required BA outputs

No results have been generated. Store future raw records, histories, tables, and
figures here; use `scratch/` only for disposable local experiments.

| Output | Required content |
| --- | --- |
| TSP per-run records (120) | Instance, neighborhood, settings, seed, initial best, final tour, length, gap %, runtime seconds, evaluation count |
| Continuous per-run records (80) | Function, dimension, settings, seed, initial best, final vector, objective, runtime seconds, evaluation count |
| Best-so-far histories | Evaluation count and best objective; retain initialization and final records |
| TSP summary (12 rows) | Instance, cities, optimum, neighborhood, best/mean/SD tour length, mean gap %, mean runtime |
| Continuous summary (8 rows) | Function, dimension, best/mean/SD final objective, mean runtime |
| TSP convergence (2 plots) | berlin52 and ch150; mean best-so-far across ten seeds, both neighborhoods, marked optimum |
| berlin52 route (1 plot) | Shortest valid route across all 20 runs; return leg; neighborhood, seed, length, gap, starting city |
| Rastrigin convergence (1 plot) | D=10; mean best-so-far across ten seeds against evaluations; label any transformed axis |
| Continuous boxplots (1 figure) | Four panels, one per function at D=30, final objectives across ten seeds |

All figures need labels, units where applicable, legends, and captions. Record
the source revision, input checksums, and environment with experiment outputs.
Align histories on evaluation counts before averaging, never on iteration number.
