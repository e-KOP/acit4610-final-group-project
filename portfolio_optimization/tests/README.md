# Validation to implement

- Exact asset/record counts, valid indices, complete unique correlation pairs,
  symmetric covariance, and finite numeric inputs.
- All three port1 parser checkpoints in the problem README.
- Hand-calculated returns and variances from the specification's example.
- Simplex projection and return repair, including already feasible inputs.
- Final feasibility checks at tolerance 1e-8, independent of search code.
- Strict (1+1) acceptance, per-trial success rule, and step-size bounds.
- Correct population recombination, independent mutation draws, and adaptation.
- Plus versus comma survivor selection; reporting archive excluded from comma parents.
- Initialization and rejected candidates count toward the budget.
- Partial final offspring batch contributes to the archive; exact 30,000 stop.
- Archive never worsens; saved allocation reproduces saved variance and return.
- Complete case/seed coverage, valid-only variance statistics, all-run mean runtime.

No algorithm tests exist yet. Dataset checksums can already be checked with the
root `scripts/verify_data.py` utility.
