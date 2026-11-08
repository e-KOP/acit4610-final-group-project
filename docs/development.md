# Development checklist

This is an implementation plan, not an experiment log or report draft.

- [x] Review the two previous assignment layouts and the complete portfolio brief.
- [x] Create separate folders for both required problems.
- [x] Bundle the eleven original benchmark files with source URLs and SHA-256 hashes.
- [x] Record required experiments and leave group-selected BA settings unresolved.
- [x] Confirm Group-8 and record all four members in the README.
- [x] Implement TSPLIB loading, rounded distances, and tour validation.
- [x] Implement both TSP neighborhoods, scout initialization, and core BA.
- [x] Add six automated TSP tests and reproduce seed-42 eil51 trials with both moves.
- [x] Document current TSP defaults and retention/scouting behavior.
- [ ] Broaden TSPLIB, distance, neighborhood, and parameter-boundary tests.
- [ ] Implement the portfolio loader, objectives, and independent validation tests.
- [ ] Implement and validate all four continuous functions and continuous BA.
- [ ] Confirm BA experiment settings and connect JSON configuration to the runner.
- [ ] Implement and test common portfolio repair and all three ES variants.
- [ ] Add a reusable single-run CLI with runtime and file exports; a tested TSP Python example is available.
- [ ] Add batch commands, raw records, histories, and reproducibility metadata.
- [ ] Run small pilot cases in separate output folders and inspect failures.
- [ ] Pin dependencies and run all 650 required experiments.
- [ ] Generate every required table and figure from saved data.
- [ ] Update READMEs with tested commands, actual settings, and measured results.
- [ ] Have the group write and check its combined report, and complete submission.

Prefer one coherent change at a time, with tests for numerical invariants and
algorithm behavior. Do not add a general framework before the concrete problems
need it. Keep source files named for their responsibilities.
