# CHK-RA-CH14-AO-FASTVOL-044 — Ch14 Capillary Nonuniform CCD Metric RCA

Date: 2026-05-13

## User Question

The user asked whether the remaining capillary-wave failure was caused by the non-uniform grid, and required a theory-first fix rather than a numerical workaround.

## Theory

For the non-uniform CCD route the paper-level chain is:

1. solve the compact derivative in the uniform computational coordinate `xi`;
2. map to physical space with `J = dxi/dx`;
3. use the resulting physical derivatives in viscous, FCCD/PPE, and AO pressure-reaction operators.

Therefore the CCD axis spacing must be `Delta xi = 1/N` whenever `grid.uniform` is false.  Using the physical mean spacing `L/N` in that raw solve and then multiplying by `J` mixes two coordinate systems.

For the ch14 capillary domain, `L = 0.02`.  The wrong composition over-scales first derivatives by about `1/L = 50` and second derivatives by about `1/L^2 = 2500` on the pre-rebuild non-uniform-operator path.  Existing non-uniform CCD tests used `L = 1`, so this defect was invisible.

## Hypotheses Tested

- H1: AO PCG-only projection is the root.  Refuted by the uniform-grid control, which runs with the same PCG policy.
- H2: PPE defect-correction iteration count is the root.  Refuted by prior probes: more PPE iterations reduce immediate divergence but amplify pressure history, and do not explain the 50/2500 scale split.
- H3: pressure history is the root.  Partially contributing, but refuted as sole cause: dropping history reduces residuals but still fails.
- H4: the user's non-uniform-grid suspicion is correct.  Supported: `--uniform-grid` makes the stage chain run 10 steps, while the non-uniform-operator path failed at step 4 before the fix.
- H5: exact root is coordinate-scale mixing in non-uniform CCD.  Supported by code inspection and the `L != 1` regression: non-uniform CCD was building compact operators with `h=L/N` although metric mapping assumes raw `xi` derivatives.

## Fix

`CCDSolver` now uses:

- `h = L/N` for truly uniform physical-grid derivatives;
- `h = 1/N` for non-uniform computational-coordinate derivatives.

The metric fallback in `Grid` already used `J=(1/N)/h_phys`, so this restores the mathematical chain `d/dx = (dxi/dx) d/dxi`.

Added regression:

- `test_nonuniform_metric_uses_dimensionless_xi_for_short_domain`, using `L=0.02` and `alpha_grid=2`, to catch the hidden double-scaling.

Enhanced diagnostic:

- `experiment/ch14/diagnose_ao_stage_chain.py` can now compare default and `--uniform-grid` controls and prints geometric cell divergence alongside projection divergence.

## Validation

- Local targeted regression: `1 passed`.
- Remote suite: `737 passed, 33 skipped`.
- Remote ch14 capillary stage-chain, default non-uniform settings: 10 steps passed after the fix.
- Remote ch14 capillary stage-chain, default non-uniform settings: 20 steps passed after the fix.
- `git diff --check`: PASS.

## Guardrails

[SOLID-X] No physical parameter change, CFL reduction, damping, smoothing, tolerance weakening, coordinate offset, FD/WENO/PPE fallback, dense runtime fallback, hidden CPU fallback, experiment result commit, main merge, or branch deletion was introduced.
