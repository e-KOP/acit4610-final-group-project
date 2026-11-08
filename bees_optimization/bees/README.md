# Python modules: bees

The TSP foundation was merged on 5 November 2026. Import the modules from the
repository root using `bees_optimization.bees`.

| Module | Responsibility | Status |
| --- | --- | --- |
| `tsplib.py` | TSPLIB loading, metadata checks, rounded distances, tour evaluation and validation | Implemented |
| `initialization.py` | Uniformly shuffled tours with city 1 fixed and scout populations | Implemented |
| `neighborhoods.py` | Swap and inclusive segment reversal with city 1 fixed | TSP implemented; continuous moves pending |
| `algorithm.py` | Site selection, recruitment, retention, scouting, budget, and best record | TSP implemented |
| `functions.py` | Four benchmark definitions and bounds | Planned |
| `experiments.py` | Configuration loading, independent runs, timing, and provenance | Planned |
| `output.py` | Per-run records, tables, and plots | Planned |
| `__main__.py` | Single-run, batch, and output commands | Planned |
