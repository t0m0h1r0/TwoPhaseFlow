# CHK-RA-CH14-AO-FASTVOL-043 — Ch14 capillary failure RCA: viscous DC amplification

## Question

Investigate the ch14 AO-Fast capillary-wave failure from physics and
mathematics, without coordinate offsets, tolerance weakening, damping, or other
ad hoc fixes.

## Hypotheses Tested

| Hypothesis | Test | Verdict |
|---|---|---|
| AO P1 geometry / common flux / PCG projection is inexact | CHK-041 dense CPU oracle exactness | Refuted for PCG route |
| PPE creates the first blow-up | Stage-chain probe before PPE | Refuted: `u_star` is already huge before PPE in the original run |
| Pressure-coordinate history directly creates the first blow-up | Stage-chain pressure-history face/div metrics | Refuted as first cause: history is `O(10^2-10^3)` when `u_star` is `O(10^21)` |
| BDF2 history switch is the cause | Forced predictor startup every step | Refuted: startup mode still triggers viscous DC amplification |
| Material coefficients are invalid | Stage-chain `rho_min/max`, `mu_min/max` | Refuted: coefficients remain within water-air bounds |
| GPU sparse LU alone is the cause | `--backend cpu` on the same remote tree | Refuted: CPU reproduces the same amplification |
| Low-order Helmholtz initial solve is already singular | Nearly zero DC relaxation | Refuted: initial low solution remains small; fixed-relaxation corrections amplify |
| Low/high viscous operator mismatch makes fixed-relaxation DC non-contractive | Residual-history and spatial-operator toggles | Supported |

## Key Evidence

Original PCG-only YAML, before the fix:

- Step 2 material fields are bounded:
  `rho=[1.204, 998.2]`, `mu=[1.825e-5, 1.002e-3]`.
- Step 2 viscous DC residual starts small but explodes:
  `residual0=4.821792e-04`, `final=1.408634e+19`,
  growth `2.921392e+22`.
- The state returned to PPE is therefore unphysical:
  `u_star=1.136440e+21`, `predictor_div=4.028476e+24`,
  `ppe_rhs=1.654730e+29`.
- `--viscous-dc-low-operator scalar` gives the same failure class.
- `--viscous-dc-relaxation 1e-6` keeps the predictor small
  (`u_star=2.015e-05` at step 2), showing that the low-order initial solve is
  not the source; the fixed correction step is.
- `--viscous-spatial conservative_stress` makes the viscous DC residual
  contract and converge, confirming that the high-order `ccd_bulk` operator and
  low-order Helmholtz preconditioner can be too far apart for fixed-omega DC.

Mathematical interpretation:

The implicit viscous BDF2 solve is a Helmholtz problem

`A_H u* = b`, with `A_H = I - tau V_H`.

Defect correction computes `d = A_L^{-1} r_H` and previously updated

`u <- u + omega d`

with fixed `omega=0.8`.  This assumes the iteration matrix
`I - omega A_H A_L^{-1}` is contractive.  The capillary interface case violates
that assumption; fixed omega turns a small high residual into a massive
anti-diffusive correction.

## Repair Implemented

`src/twophase/simulation/viscous_helmholtz_dc.py` now uses the same
residual-minimising defect-correction principle already used by the PPE DC:

- Form the high-operator image of the correction, `A_H d`.
- Choose `alpha` that minimises `||r_H - alpha A_H d||_2`.
- Fall back to halved configured relaxation candidates only if they reduce the
  high residual.
- Reject non-decreasing corrections and record `viscous_dc_stalled`.

This is a mathematical correction to the Krylov/defect-correction step length,
not a physical damping, CFL reduction, tolerance weakening, coordinate offset,
or smoothing fix.

## Post-Fix Evidence

Default `ccd_bulk` viscous path after the line-search fix:

- Step 2 viscous residual:
  `residual0=4.821792e-04`, `final=6.007344e-06`,
  growth `1.245874e-02`.
- Step 2 predictor no longer explodes:
  `u_star=8.914468e-04`, not `1.136440e+21`.
- Full remote test suite passed:
  `736 passed, 33 skipped`.

Remaining unresolved problem:

- The capillary-wave probe still does not reach 10 steps.  It now fails later:
  step 4 fail-close with `q/phi compatibility residual 1.746289e-10 >
  1e-11`.
- PPE/pressure history still grows rapidly (`ppe_rhs` reaches `6.020189e+07`
  by step 3 after the viscous fix), so the next RCA should target the
  AO pressure-reaction/PPE/pressure-history chain rather than the viscous DC
  blow-up.

## Validation

- Local targeted tests:
  `3 passed`.
- Remote `make test PYTEST_ARGS=...` ran the repository suite:
  `736 passed, 33 skipped`.
- Remote stage-chain and theory probes executed on the PCG-only capillary YAML.
- `git diff --check` passed.

