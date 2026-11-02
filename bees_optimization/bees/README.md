# Planned Python package: bees

Create modules as their behavior is implemented; this directory has no solver yet.

| Module | Responsibility |
| --- | --- |
| `data.py` | Load and validate original TSPLIB coordinates and metadata |
| `tsp.py` | Rounded distances, tour objective, tour validation |
| `functions.py` | Four benchmark definitions and bounds |
| `neighborhoods.py` | Swap, segment reversal, continuous perturbation and clipping |
| `bees_algorithm.py` | Site selection, recruitment, retention, scouting, budget, best record |
| `experiments.py` | Load configuration and run the required independent seeds |
| `output.py` | Per-run records, summary tables, convergence and solution plots |
| `__main__.py` | Single-run, batch, and output commands once implemented |
