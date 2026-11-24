# Python modules: bees

The TSP foundation was merged on 5 November 2026. Import the modules from the
repository root using `bees_optimization.bees`.

| Module | Responsibility | Status |
| --- | --- | --- |
| `tsplib.py` | TSPLIB loading, metadata checks, rounded distances, tour evaluation and validation | Implemented |
| `initialization.py` | Uniformly shuffled tours with city 1 fixed and scout populations | Implemented |
| `neighborhoods.py` | Swap and inclusive segment reversal with city 1 fixed | Implemented |
| `algorithm.py` | TSP adapter and compatible public TSP API | Implemented |
| `search.py` | Shared site selection, recruitment, retention, scouting, budget, and best record | Implemented |
| `continuous.py` | Uniform vectors, clipped perturbations, and continuous BA adapter | Implemented |
| `functions.py` | Four benchmark definitions and bounds | Implemented |
| `experiments.py` | Configuration loading, independent runs, timing, provenance, and the `tsp`/`continuous`/`all` command | Implemented |
| `output.py` | Summary tables and figures from the saved raw records | Implemented |
| `validate_results.py` | Independent validation of all saved records without rerunning the optimizer | Implemented |

There is no `__main__.py`; run each module with `python -m bees_optimization.bees.<module>`.
See the [Problem 1 README](../README.md#5-reproduce-the-project) for commands.
