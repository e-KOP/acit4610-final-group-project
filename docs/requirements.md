# Portfolio requirements checklist

Source: the user-supplied `Portfolio 2026.pdf`, ACIT 4610 Final Group Project 2026,
12 pages. This file summarizes requirements; the original brief remains the
authority. It is not a submission report. The course PDF is not redistributed here.

## Shared requirements (pages 1-2)

- [ ] Use the pre-approved Canvas group; record group number and all names.
- [ ] Provide one shareable GitHub repository with a separate folder per problem.
- [ ] Share the repository and grant the instructor access. The specified window
  was week 44, **26 October-1 November 2026**; confirm this has been handled.
- [ ] Provide weekly group updates with each member's percentage contribution,
  activity list, and planned next-week activities. Actual implementation
  improvement is not mandatory in every weekly update.
- [ ] Supply clean Python code, inline algorithm explanations, dependency versions,
  installation steps, data loading, and executable reproduction scripts/notebooks.
- [ ] Produce a combined **3,000-7,500-word PDF** covering both problems, with group
  number, names, and repository link. Do not put source code in the report.
- [ ] Submit **one group submission through Inspera by 30 November 2026 at 12:00**.
  The brief says code will be downloaded immediately after the deadline.
- [ ] Follow the course AI rules: AI may assist code under university guidance;
  **AI must not write the report**. Mark AI-produced code and disclose use,
  purpose, and an approximate AI-generated percentage of total code in the report.

Repository creation does not itself share the link with the instructor, assign
collaborators, send weekly updates, or submit anything to Inspera.

## Problem 1 (pages 3-7)

- [ ] Implement BA for both TSP neighborhoods and continuous functions.
- [ ] Meet the [design, instance, and parameter requirements](../bees_optimization/README.md).
- [ ] Complete the [validation checklist](../bees_optimization/tests/README.md).
- [ ] Complete 120 TSP and 80 continuous runs and every [required output](../bees_optimization/results/README.md).
- [ ] Document site selection, elite recruitment, local search, retention, scouting,
  stopping, representations, moves, bounds, and exact settings.
- [ ] Discuss initial-to-final improvement, convergence, variability, unsuccessful
  cases, neighborhood differences, larger instances, higher dimensions, and what
  changes or remains shared between discrete and continuous BA.

## Problem 2 (pages 8-12)

- [ ] Implement all three ES variants with common repair and validation.
- [ ] Meet the [design, target, and parameter requirements](../portfolio_optimization/README.md).
- [ ] Complete the [validation checklist](../portfolio_optimization/tests/README.md).
- [ ] Complete 450 runs and every [required output](../portfolio_optimization/results/README.md).
- [ ] Explain selection, adaptation, size effects, repair, stagnation, failures,
  and the difference between the comma population best and archive best.
- [ ] Limit performance conclusions to the tested variants and historical inputs.
