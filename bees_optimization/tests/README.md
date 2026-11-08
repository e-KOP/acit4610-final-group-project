# TSP tests and remaining validation

Run from the repository root:

```bash
python -m unittest discover -s bees_optimization/tests -v
```

`test_algorithm.py` contains **six passing tests**, checked on 8 November 2026:
site selection, recruitment with both moves, a complete 1,000-evaluation swap
run, evaluation history, partial iterations, and an invalid neighborhood value.
These tests also check selected tour-validity and objective-consistency cases.
They do not yet cover every parameter boundary or the complete benchmark suite.

Expand coverage against the following requirements as development proceeds:

- TSPLIB NAME, TYPE=TSP, DIMENSION, EDGE_WEIGHT_TYPE=EUC_2D, and
  NODE_COORD_SECTION; exact row count and unique expected city IDs.
- Rounded Euclidean distances, symmetry, diagonal zeros, and return-edge inclusion.
- Every output tour contains every city once and starts with city 1.
- Both moves preserve permutations and keep the first city fixed.
- Each continuous function agrees with SFU at its minimizer and another point.
- Continuous initialization and neighbors remain within their declared bounds.
- Every evaluated candidate counts, including initialization, rejection, and scouts.
- Incomplete final iteration stops at exactly 30,000 evaluations.
- Best-so-far values never increase; saved solution reproduces the saved objective.
- Fixed seed reproduces numerical outcomes; complete required case/seed coverage.

Dataset checksums can also be checked with the root `scripts/verify_data.py` utility.
