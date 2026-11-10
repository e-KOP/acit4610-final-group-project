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
| `experiments.py` | Configuration loading, independent runs, timing, and provenance | Planned |
| `output.py` | Per-run records, tables, and plots | Planned |
| `__main__.py` | Single-run, batch, and output commands | Planned |
