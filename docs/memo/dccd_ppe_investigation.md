# DCCD PPE Solver Investigation: Defect Correction for CCD Poisson Equation

**Date**: 2026-04-04  
**Context**: Can the CCD Poisson equation L_CCD(p) = rhs be solved iteratively
via defect correction with a cheaper preconditioner, avoiding Kronecker product
assembly and LU decomposition?

## 1. Problem Statement

The CCD operator L_CCD is O(h^6) accurate and applied matrix-free via
`ccd.differentiate()`. We seek an iterative solver:

```
p^{k+1} = p^k + M^{-1} (rhs - L_CCD(p^k))
```

where M is a preconditioner that is cheap to invert.

## 2. Approaches Tested

### 2.1 FD Preconditioner (Richardson Iteration)

**M = 2nd-order FD Laplacian** (5-point stencil, sparse LU via `splu`).

| N | Behavior |
|---|----------|
| 8 | Converges (small enough that CCD-FD gap is small) |
| 16 | Diverges after ~5 iterations |
| 32 | Diverges after ~3 iterations |
| 64 | Diverges after ~2 iterations |

**Root cause**: Spectral radius rho(I - M^{-1} L_CCD) > 1. CCD and FD have
incompatible high-frequency response — the CCD modified wavenumber exceeds
the FD value at high wavenumbers, causing eigenvalues of the iteration matrix
to exceed 1 in magnitude.

### 2.2 ADI-Split FD Preconditioner (Original PPESolverSweep)

**M = (1/dtau - L_FD_x)(1/dtau - L_FD_y)** via alternating Thomas sweeps.

Same divergence as 2.1, plus additional ADI splitting error. The existing
`PPESolverSweep` passes MMS tests only because (a) N=16 is small enough,
(b) smooth MMS solutions have low high-frequency content, and (c) tests
check `isfinite()` rather than convergence.

### 2.3 Filtered DC: Low-Pass Filter on Correction dp

**dp_filtered = [1/4, 1/2, 1/4] convolution applied to dp** before update.

| Filter strength af | Behavior | Residual floor |
|--------------------|----------|----------------|
| 0.4 | Stable, converges | ~1e-3 (stalls) |
| 0.3 | Stable | ~1e-3 |
| 0.2 | Marginally stable | ~1e-3 |
| 0.0 (no filter) | Diverges | N/A |

Filter suppresses unstable high-frequency modes but introduces O(h^2)
truncation error that prevents convergence below ~1e-3. Insufficient for
projection method time-stepping (requires residual < ~1e-6).

### 2.4 Annealed Filter (Gradual Reduction)

Schedule: af = 0.4 -> 0.3 -> 0.2 -> 0.1 -> 0.05 -> 0.0

Result: Converges during filtered phases, but **diverges immediately when
af reaches 0**. The filtered solution is not a good initial guess for the
unfiltered problem because L_filtered(p) != L_CCD(p) — the residual jumps
when switching operators.

### 2.5 HFE-Smoothed DC

Three variants tested — HFE applied to residual R, correction dp, or
solution p:

| Variant | Result |
|---------|--------|
| HFE on R (both phases) | Diverges (HFE destroys residual structure) |
| HFE on dp (both phases) | Diverges (creates artificial discontinuity) |
| HFE on p (both phases) | Diverges (same) |

**Root cause**: CSF (smoothed Heaviside) pressure is continuous and smooth
across the interface — there is no jump. HFE overwrites one phase with
extrapolated values from the other, introducing artificial discontinuities
into a field that should be smooth. This is the same mechanism observed in
section 12.3 (HFE ablation study: 9000x parasitic current amplification).

HFE is designed for sharp-interface fields with true jumps (e.g., GFM
pressure). It is counterproductive for CSF pressure.

### 2.6 CCD 1D Line Relaxation

Extract 1D CCD D1, D2 matrices via identity differentiation, solve per-line
dense systems as Gauss-Seidel preconditioner.

Result: Diverges at all relaxation parameters (omega = 0.1 to 1.0).

**Root cause**: Same issue as ADI splitting — 1D line solve attributes the
full 2D residual to one axis, creating over-correction. The CCD 1D line
relaxation is structurally equivalent to ADI sweep with CCD operators instead
of FD, and inherits the same instability.

### 2.7 DC with Early Stopping

Observe that plain DC (2.1) actually **converges for the first ~10 iterations**
before diverging. Track residual and revert to best-seen solution when
divergence is detected.

| Metric | Value |
|--------|-------|
| Parasitic velocity (50 steps) | 5.1e-3 |
| Laplace pressure error | 1.1% |
| PPE residual | ~1e0 (not converged) |
| DC iterations per step | 3-10 |
| Stable? | Yes (50 steps) |

Viable but **inferior to FD spsolve** (parasitic velocity 22x worse) because
the PPE is only approximately solved.

## 3. Comparison Table

| Method | PPE accuracy | grad p accuracy | Parasitic vel | Stable? |
|--------|-------------|-----------------|---------------|---------|
| **FD spsolve + CCD grad** | O(h^2) exact | O(h^6) | **2.3e-4** | Yes |
| DC early-stop + CCD grad | ~O(h^2) approx | O(h^6) | 5.1e-3 | Yes |
| FD spsolve + FD grad | O(h^2) exact | O(h^2) | 1.1e-2 | Yes |
| Filtered DC + CCD grad | ~O(h^2) approx | O(h^6) | stalls | No (time-stepping) |
| Plain DC | O(h^6) target | O(h^6) | N/A | Diverges |

## 4. Root Cause Analysis

The fundamental obstacle is the **spectral mismatch** between CCD and any
simpler preconditioner:

- CCD compact scheme has modified wavenumber k* that exceeds the true k at
  high frequencies (super-resolution property)
- FD has modified wavenumber k_FD < k for all frequencies
- The ratio k*_CCD / k_FD grows with wavenumber
- This means M^{-1} L_CCD has eigenvalues > 1 at high frequencies
- Richardson iteration p <- p + M^{-1}(rhs - Lp) amplifies these modes

No amount of filtering, annealing, or relaxation can fix this without
either (a) using a preconditioner that matches CCD's high-frequency
response, or (b) using a Krylov method (GMRES) that minimizes residual
over the Krylov subspace regardless of spectral radius.

## 5. Viable Alternatives (Not Yet Tested)

| Method | Principle | Pros | Cons |
|--------|-----------|------|------|
| **GMRES + FD precond** | Krylov minimization | Converges despite rho>1 | Uses GMRES |
| **4th-order compact FD** | Better spectral match | Smaller rho | Still rho>1 at highest k |
| **CCD Kronecker + LU** | Exact CCD inversion | O(h^6) exact | Uses LU, O(N^3) |
| **Multigrid + CCD** | Scale separation | Optimal O(N) | Complex implementation |

## 6. Conclusion

For the CSF one-fluid solver, **FD spsolve + CCD gradient** is the optimal
production configuration:

- FD PPE is solved exactly (spsolve) — zero residual, no iteration
- CCD gradient provides O(h^6) balanced-force cancellation
- Parasitic currents 2.3e-4 at N=64 — best among all tested methods

The DC approach cannot match this because no cheap preconditioner adequately
approximates the CCD operator at high frequencies. HFE is ineffective
because CSF pressure has no interface jump.

## 7. Eigenvalue Analysis (N=16)

M^{-1} L_CCD has eigenvalues in [-0.03, 2.45] — the operator is **indefinite**.
This makes all stationary iterative methods (Richardson, Jacobi, GS, ADI)
fundamentally unsuitable regardless of relaxation parameter or preconditioner
quality. The optimal Richardson omega = 0.82 gives rho = 0.9998 ≈ 1.

Anderson acceleration (equivalent to GMRES(m)) was tested with m=10..30 but
converges too slowly for time-stepping: 100 iterations yield residual ~1e-2,
insufficient for the projection method (requires < ~1e-6).

## 8. Why FD spsolve + CCD Gradient Works

The key insight: **the projection method applies FD solve and CCD gradient
only once per time step** (no iteration). The discrete continuity violation is:

    CCD_div(u) = dt * (L_FD - L_CCD)(p) = O(h^4)

This is a bounded, non-accumulating truncation error — fundamentally different
from iterative methods where the same CCD-FD mismatch is amplified
exponentially across iterations.

The production configuration (FD spsolve + CCD grad) achieves:
- Exact FD PPE solve (zero residual, no iteration)
- O(h^6) balanced-force via CCD gradient
- Parasitic velocity 2.3e-4 at N=64 (near CSF theoretical floor)

## 9. Final Decision

**Adopted**: FD spsolve + CCD gradient as the production PPE solver.
CCD-consistent PPE remains a theoretical goal but is not required for
the CSF one-fluid solver. The CCD operator's indefinite spectrum makes
all cheap iterative methods unsuitable; only full GMRES or Kronecker-LU
can solve L_CCD exactly, both of which are excluded by design constraints.
