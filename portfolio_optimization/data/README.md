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
three port1 numeric checkpoints were checked at acquisition. A reusable project
parser and its tests remain to be implemented.

These third-party files retain their original authorship. This repository does
not apply a new software license to them. Consult the original source for usage
terms; public download availability is not a claim of a particular license.
