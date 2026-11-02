# Planned Python package: portfolio

Create modules as their behavior is implemented; this directory has no solver yet.

| Module | Responsibility |
| --- | --- |
| `data.py` | Load asset statistics, reconstruct correlations and covariance |
| `evaluation.py` | Expected return, variance, and case target calculation |
| `repair.py` | Simplex projection and return-target repair |
| `feasibility.py` | Independent checks of final weight and return constraints |
| `one_plus_one.py` | Single-parent ES with scalar 1/5 success-rule adaptation |
| `population_es.py` | Shared recombination and self-adaptation, explicit plus/comma selection |
| `experiments.py` | Required cases, seeds, budgets, and run records |
| `output.py` | Summaries and convergence plot from saved records |
| `__main__.py` | Single-run, batch, and output commands once implemented |
