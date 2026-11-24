# Bees Algorithm setting-selection pilot — reproducible output

Seeds: 100, 101, 102, 103, 104. Evaluation budget: 30000 per run.
All entries below were computed from the pilot-run JSONL in this folder.

## TSP: mean gap (%) averaged equally across tested instances

| Setting | Swap | Segment reversal |
| --- | ---: | ---: |
| A | 102.4 | 45.2 |
| B | 75.7 | 17.6 |
| C | 74.4 | 16.3 |

## Continuous: lowest mean error per function and dimension

| Function | D | Best setting (descriptive only) |
| --- | ---: | --- |
| ackley | 10 | B |
| ackley | 30 | C |
| rastrigin | 10 | B |
| rastrigin | 30 | B |
| rosenbrock | 10 | B |
| rosenbrock | 30 | B |
| sphere | 10 | A |
| sphere | 30 | B |

This pilot is descriptive. It does not establish statistical
significance or a universally best Bees Algorithm setting.
