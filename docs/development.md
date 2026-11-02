# Development checklist

This is an implementation plan, not an experiment log or report draft.

- [x] Review the two previous assignment layouts and the complete portfolio brief.
- [x] Create separate folders for both required problems.
- [x] Bundle the eleven original benchmark files with source URLs and SHA-256 hashes.
- [x] Record required experiments and leave group-selected BA settings unresolved.
- [ ] Confirm the approved group number and member list.
- [ ] Implement TSPLIB and portfolio loaders with independent validation tests.
- [ ] Implement and validate TSP distances, four functions, and portfolio objectives.
- [ ] Choose BA site/recruitment settings and record retention/scouting decisions.
- [ ] Implement and test the two TSP neighborhoods and continuous BA.
- [ ] Implement and test common portfolio repair and all three ES variants.
- [ ] Add single-run commands; verify solutions and exact evaluation counting.
- [ ] Add batch commands, raw records, histories, and reproducibility metadata.
- [ ] Run small pilot cases in separate output folders and inspect failures.
- [ ] Pin dependencies and run all 650 required experiments.
- [ ] Generate every required table and figure from saved data.
- [ ] Update READMEs with tested commands, actual settings, and measured results.
- [ ] Have the group write and check its combined report, and complete submission.

Prefer one coherent change at a time, with tests for numerical invariants and
algorithm behavior. Do not add a general framework before the concrete problems
need it. Keep source files named for their responsibilities.
