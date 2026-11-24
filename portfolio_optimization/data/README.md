# Benchmark data and sources

Original benchmark files were retrieved on **2 November 2026**. The manifest
records exact source URLs, byte counts, SHA-256 hashes, and transformations.
Run `python scripts/verify_data.py` from the repository root to verify them.

| Bundled file | Official download |
| --- | --- |
| [or_library/port1.txt](or_library/port1.txt) | [Original file](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/port1.txt) |
| [or_library/port2.txt](or_library/port2.txt) | [Original file](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/port2.txt) |
| [or_library/port3.txt](or_library/port3.txt) | [Original file](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/port3.txt) |
| [or_library/port4.txt](or_library/port4.txt) | [Original file](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/port4.txt) |
| [or_library/port5.txt](or_library/port5.txt) | [Original file](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/port5.txt) |

See [manifest.json](manifest.json) for provenance and checksums.

Files are byte-for-byte downloads with no normalization or preprocessing.
[OR-Library format and attribution](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/portinfo.html):
Chang, Meade, Beasley, and Sharaiha (2000), *Heuristics for cardinality constrained
portfolio optimisation*, Computers & Operations Research 27, 1271-1302.

The course problem uses long-only budget and minimum-return constraints; it does
not add cardinality constraints from the source paper. The five `portef` frontier
files are not required and are not included. Asset counts, pair coverage, and the
three port1 numeric checkpoints were checked at acquisition. The project parser
is `portfolio_optimization/portfolio/data.py`; its invariants are covered by
`portfolio_optimization/tests/test_data.py`.

## File format and field mapping

Each file is read as whitespace-separated tokens in this order:

```text
n
mean_return_1  std_dev_1
...
mean_return_n  std_dev_n
i  j  correlation_ij        (n(n+1)/2 lines, 1-based indices, i <= j, diagonal included)
```

| File field | Project variable | Notes |
| --- | --- | --- |
| `n` | `n_assets` | 31, 85, 89, 98, 225 |
| mean return | `r_i` | Weekly decimal return, used unchanged |
| standard deviation | `s_i` | Decimal, used unchanged |
| `i j correlation` | `C[i-1][j-1]` and `C[j-1][i-1]` | Mirrored into both halves of the matrix |
| (derived) | `Sigma_ij = s_i * s_j * C_ij` | Covariance used by the variance objective |

Example from `port1.txt`: the first line is `31`, asset 1 has mean return
`0.001309` and standard deviation `0.043208`, and the first correlation records
are `1 1 1.000000` and `1 2 .562289`. The file holds 31 asset lines and
`31 x 32 / 2 = 496` correlation records.

These third-party files retain their original authorship. This repository does
not apply a new software license to them. Consult the original source for usage
terms; public download availability is not a claim of a particular license.
