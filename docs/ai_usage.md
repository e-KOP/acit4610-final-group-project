# AI assistance record

Maintain this factual development record as the project changes. It is not text
for the submission report; the group must write its own disclosure.

| Date | Tool | Scope | Code affected | Human review |
| --- | --- | --- | --- | --- |
| 2026-11-02 | OpenAI Codex | Repository structure, technical documentation, experiment specification files, benchmark acquisition, checksum verification utility | `scripts/verify_data.py` (entire file) | Pending group review |
| 2026-11-10 | OpenAI Codex | Review TSP; extract shared BA loop; implement continuous objectives and search; add numerical and behavioral tests; update technical documentation | Under `bees_optimization/`: `bees/search.py` extracted and adapted from the group's TSP loop; `bees/algorithm.py` adapter; new `bees/functions.py`, `bees/continuous.py`; validation additions in `bees/tsplib.py`, `bees/neighborhoods.py`; new `tests/test_continuous.py`, `tests/test_search.py`, `tests/test_tsp_data.py` | Pending group review |

| 2026-11-20 | Claude (Anthropic) | Pilot scripts for choosing BA settings (local only); Problem 1 experiment runner with per-run checks, raw-record export, compressed histories and metadata; summary tables and the five required figures | `bees_optimization/bees/experiments.py`, `bees_optimization/bees/output.py` (entire files) | Built step by step and run by Jakob; group review pending |

| 2026-11-22 | OpenAI ChatGPT | Independent validation of 200 Problem 1 results, verification of objectives, histories, configurations and statistical summaries; experiment-runner regression tests, history compression, convergence alignment and output regeneration | `bees_optimization/bees/validate_results.py`, `bees_optimization/tests/test_results.py`, `bees_optimization/tests/test_experiment_pipeline.py` | Reviewed and tested by group member; 50 automated tests passing |

No optimization algorithm, experiment result, or submission-report prose was
generated during setup. Benchmark file contents come from the named original
sources, not AI. The initial verification utility is AI-generated and marked in
its file header. Update this log and code markings for subsequent assistance.

The approximate AI-produced percentage of the eventual project code has not
been calculated; the group should assess it at submission time.
