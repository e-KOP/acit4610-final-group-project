# Benchmark data and sources

Original benchmark files were retrieved on **2 November 2026**. The manifest
records exact source URLs, byte counts, SHA-256 hashes, and transformations.
Run `python scripts/verify_data.py` from the repository root to verify them.

| Bundled file | Official download |
| --- | --- |
| [tsplib/eil51.tsp](tsplib/eil51.tsp) | [Original file](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/eil51.tsp.gz) |
| [tsplib/berlin52.tsp](tsplib/berlin52.tsp) | [Original file](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/berlin52.tsp.gz) |
| [tsplib/st70.tsp](tsplib/st70.tsp) | [Original file](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/st70.tsp.gz) |
| [tsplib/eil76.tsp](tsplib/eil76.tsp) | [Original file](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/eil76.tsp.gz) |
| [tsplib/kroA100.tsp](tsplib/kroA100.tsp) | [Original file](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/kroA100.tsp.gz) |
| [tsplib/ch150.tsp](tsplib/ch150.tsp) | [Original file](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/ch150.tsp.gz) |

See [manifest.json](manifest.json) for provenance and checksums.

Only gzip decompression was applied; coordinates and original text are unchanged.
The files use EUC_2D. Headers, row counts, and unique city IDs were checked at
acquisition. Distance calculation and tour validation are now implemented in
`bees_optimization/bees/tsplib.py`; parser, distance, and tour invariants are
covered by `bees_optimization/tests/test_tsp_data.py`.

References: [TSPLIB](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/),
[optimal lengths](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/TSP-BEST.html),
[format and distance rules](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/tsp95.pdf).

Continuous functions require no dataset. Use the SFU definitions:
[Sphere](https://www.sfu.ca/~ssurjano/spheref.html),
[Rosenbrock](https://www.sfu.ca/~ssurjano/rosen.html),
[Rastrigin](https://www.sfu.ca/~ssurjano/rastr.html), and
[Ackley](https://www.sfu.ca/~ssurjano/ackley.html).

These third-party files retain their original authorship. This repository does
not apply a new software license to them. Consult the original source for usage
terms; public download availability is not a claim of a particular license.
