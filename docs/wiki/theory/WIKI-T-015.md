---
ref_id: WIKI-T-015
title: "Defect Correction: Thomas Coefficients, Convergence Rate γ(t), and Spectral Theory"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/appendix_numerics_solver_s2.tex
    git_hash: 3d4d1bb
    description: "Thomas tridiagonal coefficients for FD sweep in defect correction"
  - path: paper/sections/appendix_numerics_solver_s3.tex
    git_hash: 3d4d1bb
    description: "Convergence rate γ(t), optimal Δτ derivation, CCD Laplacian λ_max analysis"
  - path: paper/sections/appendix_numerics_solver_s5.tex
    git_hash: 3d4d1bb
    description: "DC convergence theory: iteration matrix spectrum, optimal ω, variable-density limits"
consumers:
  - domain: L
    usage: "PPESolverSweep Thomas coefficients; DC+LU ω parameter; Δτ_opt formula"
  - domain: A
    usage: "Appendix D.1 referenced from §8 (defect correction, pseudotime)"
  - domain: E
    usage: "exp10_18 validates ω convergence; Δτ_opt used in PPE solver benchmarks"
depends_on:
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-001]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## D.1.1 — Thomas Tridiagonal Coefficients

For variable-density FD Laplacian (L_{FD,x} q)_i = (1/ρ_i)(q_{i-1}−2q_i+q_{i+1})/h² − (∂ρ/∂x)_i/(ρ_i²)(q_{i+1}−q_{i-1})/(2h):

### Interior Nodes (1 ≤ i ≤ N−1)

| Coefficient | Formula | Role |
|---|---|---|
| a_i (lower) | −1/(ρ_i h²) + (∂ρ/∂x)_i/(2ρ_i² h) | q_{i-1} |
| b_i (main) | 1/Δτ + 2/(ρ_i h²) | q_i |
| c_i (upper) | −1/(ρ_i h²) − (∂ρ/∂x)_i/(2ρ_i² h) | q_{i+1} |

**Strict diagonal dominance:** |b_i| − |a_i| − |c_i| = 1/Δτ > 0 when density gradient smooth enough. Thomas algorithm stable without pivoting.

### Boundary (Neumann ghost cell reflection)

Left wall (i=0): a₀=0, b₀=1/Δτ+2/(ρ₀h²), c₀=−2/(ρ₀h²). Cross-derivative term vanishes (q₁−q_{-1}=0 under q_{-1}=q₁).

Right wall (i=N): mirror symmetric.

### Gauge Fix

Center node (N/2, N/2) pinned to δp=0 after each sweep. Preserves 4-fold symmetry of square domain.

### Computational Cost

O(N²) per iteration: x-sweep (N_y batches of N_x Thomas) + y-sweep + CCD residual evaluation.

## D.1.2 — Convergence Rate γ(t) and Optimal Δτ

### Sweep-type pseudotime iteration

(I + Δτ L_x)(I + Δτ L_y) p^{m+1} = p^m + Δτ q_h

Error contracts: e^{m+1} = e^m / (1+t)² where t = Δτλ/2. **Unconditionally stable** for any t > 0.

### Convergence indicator

γ(t) = (1 + t²) / (1 + t)² — captures trade-off between convergence speed (small t → slow) and splitting error (large t → O(Δτ²) fixed-point bias).

**Optimal:** dγ/dt = 0 at t* = 1, giving γ(1) = 1/2. Then:

**Δτ_opt = 2/λ_max ≈ 0.58 h²/a_max**

### CCD Laplacian λ_max

| Analysis | λ_max h² (a=1) |
|---|---|
| Eq-II Fourier (infinite grid) | 9.6 |
| Eq-I+II coupled Fourier (ξ=π) | 9.6 |
| Neumann BC finite grid (N=64, numerical) | ≈ 3.43 |

Boundary modification reduces effective λ_max. Practical coefficient: 3.43/h² at N=64.

## D.1.3 — DC Convergence Theory: Spectral Analysis

### Iteration Matrix

M = I − ω L_L⁻¹ L_H, where L_H = CCD (O(h⁶)), L_L = FD (O(h²)).

Eigenvalues: σ_j = 1 − ω · (λ_j/μ_j). Convergence requires ρ(M) < 1.

### Eigenvalue Ratio r(k) = λ_H/λ_FD

| kh/π | r(k) | ω_max at this mode |
|---|---|---|
| 0 (smooth) | 1.000 | 2.000 |
| 0.50 | 1.239 | 1.614 |
| 0.75 | 1.707 | 1.171 |
| 0.90 | 2.213 | 0.904 |
| 1.00 (Nyquist) | 2.400 | 0.833 |

Range: [α_min, α_max] = [1.0, 2.4], monotonically increasing with ξ.

### Optimal Relaxation

ω_max = 2/α_max = 2/2.4 ≈ 0.833 (stability limit)

ω* = 2/(α_min + α_max) = 2/3.4 ≈ 0.588 (Chebyshev midpoint)

ρ(M*) = (α_max − α_min)/(α_max + α_min) = 1.4/3.4 ≈ 0.41

### Practical ω Selection

| ω | Nyquist |σ| | Smooth |σ| | Status |
|---|---|---|---|
| 1.0 | 1.40 (diverge) | 0.00 | FAIL |
| 0.833 | 1.00 (stall) | 0.17 | MARGINAL |
| 0.70 | 0.28 | 0.30 | GOOD (fast) |
| **0.50** | **0.20** | **0.50** | **GOOD (balanced)** |
| 0.30 | 0.28 | 0.70 | GOOD (safe) |

### Variable-Density Limits

High density ratio (ρ_l/ρ_g ≥ 5): CCD O(h⁶) vs FD O(h²) ∇ρ evaluation mismatch creates residual floor ∝ (ρ_l/ρ_g)·h². DC+LU stalls. **Krylov (GMRES + FD preconditioner) needed for high density ratios.**

k=3 iterations suffice for O(h⁶) accuracy (with direct LU in Step 2).
