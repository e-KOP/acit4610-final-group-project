# Validation to implement

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

No algorithm tests exist yet. Dataset checksums can already be checked with the
root `scripts/verify_data.py` utility.
