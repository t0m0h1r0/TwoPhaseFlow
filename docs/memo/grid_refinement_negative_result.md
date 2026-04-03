# Non-Uniform Grid Refinement for Static Droplet: Investigation Report

**Date**: 2026-04-04  
**Experiment**: `experiment/ch12/viz_ch12_grid_refinement.py`  
**Figure**: `paper/figures/ch12_grid_refinement.png`

## 1. Objective

Evaluate whether the interface-fitted non-uniform grid (section 6, `alpha_grid`)
can reduce parasitic currents in the static droplet benchmark (CSF, R=0.25,
rho_l/rho_g=2, We=10, N=64).

## 2. Method

Grid concentration factor alpha = 1 (uniform), 2, 4.
`grid.update_from_levelset(phi, eps, ccd)` clusters nodes near phi=0.
All cases run to T=0.5. dt = 0.25 * h_min (CFL constraint).

Three projection variants tested:

| Variant | PPE | div(u*) | grad(p) | CSF force |
|---------|-----|---------|---------|-----------|
| **A** (CCD grad) | FD spsolve | CCD | CCD | CCD |
| **B** (FD grad) | FD spsolve | FD | FD | CCD |
| **C** (DC sweep) | CCD iterative | CCD | CCD | CCD |

## 3. Results

### Variant A: FD PPE + CCD gradients (production configuration)

| alpha | h_min | steps | parasitic vel | Laplace err |
|-------|-------|-------|--------------|-------------|
| 1     | 0.0156 | 128  | **2.3e-4**   | 1.2%        |
| 2     | 0.0030 | 669  | 2.1e-2       | 1.6%        |
| 4     | 0.0012 | 1629 | 8.7e-2       | **0.2%**    |

Stable. Laplace pressure improves at alpha=4 (0.2%). Parasitic currents
worsen by ~400x.

### Variant B: Fully FD projection (FD div, FD grad, FD PPE)

| alpha | h_min | steps | parasitic vel | Laplace err |
|-------|-------|-------|--------------|-------------|
| 1     | 0.0156 | 128  | 1.1e-2       | 1.0%        |
| 2     | 0.0030 | 669  | 8.2e-2       | 2.1%        |
| 4     | 0.0012 | 1629 | 4.1e-1       | 1.8%        |

Stable. Discrete divergence-free condition is exactly satisfied
(FD div(FD grad(p)) = FD Laplacian(p)), but parasitic currents are
50x worse than Variant A at alpha=1 due to O(h^2) balanced-force mismatch.

### Variant C: Defect correction (DCCD sweep)

Divergent at all alpha values. The ADI-split FD preconditioner fails to
converge for CSF-driven RHS. At N=64, residuals grow exponentially
(spectral radius of iteration matrix > 1). MMS tests with smooth RHS
converge only at N >= 64 with large iteration counts.

Root cause: CCD and FD operators have incompatible high-frequency response.
The defect M^{-1}(L_CCD - L_FD) has eigenvalues outside the unit circle,
making Richardson-type iteration unstable.

## 4. Root Cause Analysis

### Why parasitic currents worsen with alpha > 1

Two independent mechanisms:

**Mechanism 1: Projection inconsistency (Variant A)**

PPE uses FD Laplacian; velocity correction uses CCD gradient.
On uniform grids, FD and CCD agree to O(h^4), so the discrete
divergence-free violation is small. On non-uniform grids, the
coordinate metric amplifies the CCD-FD discrepancy, especially
where h_local << h_uniform (near the interface).

Result: div(u) != 0 after projection, accumulating as parasitic velocity.

**Mechanism 2: CSF epsilon mismatch**

The smoothed Heaviside uses epsilon = 1.5 * h_uniform (fixed globally).
At alpha=4, h_min = 0.0012 near the interface, so epsilon/h_local ~ 19.
The CSF force extends over ~19 local cells instead of ~3, creating an
unnaturally broad force distribution. The pressure field cannot exactly
balance this spread-out force, generating residual velocities.

This mechanism affects ALL projection variants equally and is the
dominant source of parasitic currents at large alpha.

### Why Variant B is worse than A at alpha=1

Balanced-force condition requires identical operators for grad(p) and
grad(psi) in the CSF force. Variant A uses CCD for both -> O(h^6)
cancellation at equilibrium. Variant B uses FD for grad(p) but CCD for
CSF -> O(h^2) mismatch -> 50x larger parasitic currents.

### Summary: the fundamental trilemma

| Requirement | Variant A | Variant B |
|---|---|---|
| Balanced force (grad p = grad psi) | CCD = CCD | FD != CCD |
| Projection consistency (div grad p = Lap p) | CCD != FD | FD = FD |
| High-order accuracy | O(h^6) grad | O(h^2) grad |

No variant satisfies all three simultaneously. On uniform grids,
Variant A wins because balanced-force dominates. On non-uniform grids,
the epsilon mismatch dominates both, making the choice less consequential.

## 5. Potential Remedies (Future Work)

| Approach | Addresses | Difficulty |
|----------|-----------|------------|
| Spatially varying epsilon(x) = 1.5 * h_local(x) | Mechanism 2 | Medium: requires variable-width Heaviside |
| CCD-consistent PPE (DCCD with better preconditioner) | Mechanism 1 | High: current FD preconditioner diverges |
| Multigrid preconditioner for DCCD | Mechanism 1 | High: non-trivial for CCD operators |
| GFM / sharp-interface (section 13) | Both mechanisms | High: eliminates CSF entirely |

The most promising near-term fix is spatially varying epsilon.
The CSF force computation (`heaviside(phi, eps)`) would need to accept
a per-node epsilon array instead of a scalar. The curvature calculation
would similarly need adaptation. This is a localized change that does
not require modifications to the PPE solver or projection method.

## 6. Conclusion

Interface-fitted grids improve Laplace pressure accuracy (alpha=4: 0.2%
vs 1.2% uniform) but worsen parasitic currents by 2 orders of magnitude.
The dominant cause is the fixed CSF smoothing width epsilon = 1.5h being
applied to a grid where h varies by 13x. The projection inconsistency
(FD PPE vs CCD gradients) is a secondary contributor.

Grid refinement alone cannot fix CSF parasitic currents. The section 6
non-uniform grid framework remains valid for level-set advection and
curvature computation, where CCD is used throughout without projection.

**Decision**: Excluded from section 12 main text. Results archived here.
