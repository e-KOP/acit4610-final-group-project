# Required ES outputs

No results have been generated. Store future records, histories, tables, and
figures here; use `scratch/` only for disposable local experiments.

| Output | Required content |
| --- | --- |
| Per-run records (450) | Case, dataset, alpha, target, variant, settings, seed, best weights, expected return, variance, validity, runtime seconds, evaluation count |
| Best-so-far histories | Evaluation count and archive best variance, including initialization and final partial batch |
| Summary (45 rows) | Case, variant, asset count, target, best/mean/SD variance, feasible-run count/rate, mean runtime |
| Convergence (1 plot) | port5_alpha050; mean archive best variance across ten seeds against evaluations; all three variants |

Variance statistics use only valid runs. Report valid runs out of ten and use
all ten runs for mean runtime. Mark incomplete batches explicitly; do not invent
missing measurements. Label axes, units, variants, and captions consistently.
Record source revision, data checksums, and environment with the outputs.
