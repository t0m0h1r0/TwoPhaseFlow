---
ref_id: WIKI-T-012
title: "CCD Boundary Treatment, Periodic BC, Elliptic Solver & Kronecker Assembly"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: paper/sections/appendix_ccd_impl_s1.tex
    git_hash: 3d4d1bb
    description: "Ghost cell method for CCD boundary treatment (alternative to boundary scheme)"
  - path: paper/sections/appendix_ccd_impl_s4.tex
    git_hash: 3d4d1bb
    description: "Periodic BC: block-circulant CCD matrix, regularity proof, LU solve"
  - path: paper/sections/appendix_ccd_impl_s2.tex
    git_hash: 3d4d1bb
    description: "2-stage CCD mixed derivative accuracy: C^8 condition and degradation mechanism"
  - path: paper/sections/appendix_ccd_impl_s3.tex
    git_hash: 3d4d1bb
    description: "CCD elliptic solver structure, Kronecker product assembly, checkerboard mode, Neumann BC"
consumers:
  - domain: L
    usage: "ccd_solver.py periodic mode, PPE Kronecker assembly, Neumann BC implementation"
  - domain: A
    usage: "Appendix B.2–B.3 referenced from §4 (boundary) and §8 (PPE solver)"
  - domain: E
    usage: "Uniform flow test validates periodic CCD; Neumann unit tests validate PPE BC"
depends_on:
  - "[[WIKI-T-001]]"
  - "[[WIKI-T-011]]"
  - "[[WIKI-X-002]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-08
---

## B.2.1 — Ghost Cell Method (Alternative BC)

Alternative to boundary scheme method. Adds virtual cells (i=−1, i=N) outside domain and applies interior stencil uniformly.

**Ghost cell settings by BC type:**

| BC | Ghost value | Meaning |
|---|---|---|
| Dirichlet (no-slip) | u_{-1} = −u_1 | Mirror reflection (u₀ ≈ 0) |
| Dirichlet (inflow) | u_{-1} = 2U_w − u_1 | u₀ = U_w |
| Neumann (outflow) | u_{-1} = u_1 | Zero gradient (even reflection) |

Derivative ghost values follow parity: for odd-symmetric u, f'_{-1} = f'_1 (even), f''_{-1} = −f''_1 (odd).

**PPE Neumann via ghost cells:** Setting p_{-1}=p_1, p'_{-1}=−p'_1, p''_{-1}=p''_1 automatically gives p'₀=0 (Neumann). No explicit boundary row modification needed.

## B.2.2 — Periodic BC: Block-Circulant Matrix

**Problem:** One-sided boundary scheme is incompatible with periodic BC. Using it causes ~16× error amplification per step → blowup at t≈0.07 (Gustafsson boundary instability).

**Solution:** All N nodes use interior stencil with wrap-around indexing:

A_L v_{(i-1) mod N} + B v_i + A_R v_{(i+1) mod N} = r_i

Global matrix K_circ is 2N×2N block-circulant — differs from block-tridiagonal by only 2 corner blocks.

**Regularity proof:** Constant modes give (1+2α₁) = 15/8 ≠ 0 and (1+2β₂) = 3/4 ≠ 0. Fourier modes: eigenvalues of K̂_k = e^{−2πik/N} A_L + B + e^{+2πik/N} A_R are nonzero for all k (from CCD modified wavenumber analysis).

**Solver:** Dense LU at initialization O(N³), then lu_solve per timestep O(N²B). Practical for N ≤ 512.

**Verification:** Uniform flow test (u=1, v=0, p=0, periodic BC): periodic CCD maintains machine zero; one-sided scheme blows up.

## B.3.1 — Mixed Derivative Accuracy: C^8 Condition

Two-stage CCD for φ_{xy}: Step 1 gives g = ∂f/∂x with E_g = O(h⁶); Step 2 differentiates g in y.

- **f ∈ C⁸:** ∂E_g/∂y ∝ h⁶ f^(8) → O(h⁶) maintained
- **Interface vicinity:** ψ^(8) ~ O(1/ε⁷) → C⁸ fails within ~3ε of interface → degrades to O(h⁵) or below
- **Impact:** Only O(ε/h) ~ O(1) grid points affected; CSF error O(h²) already dominates

## B.3.2 — CCD as Elliptic Solver: Kronecker Product Assembly

### CCD Operator Matrix

From block Thomas system M_CCD v = R(f), extract derivatives via projection:
- D_x^(1) p = E₁ M_CCD⁻¹ R(p) (first derivative)
- D_x^(2) p = E₂ M_CCD⁻¹ R(p) (second derivative)

1D Laplacian: L_CCD^(x) = E₂ M_CCD⁻¹ R ∈ R^{N×N}

### Variable-Density PPE Operator

L^ρ p = (1/ρ) p'' − (ρ_x/ρ²) p'

Using diagonal density matrices:

L_CCD^ρ = Λ_{ρ⁻¹} (D_{2x}^{2D} + D_{2y}^{2D}) − Λ_{∂ρ_x/ρ²} D_{1x}^{2D} − Λ_{∂ρ_y/ρ²} D_{1y}^{2D}

### 2D Kronecker Product Structure

C-order flattening: k(i,j) = i·N_y + j. Then:
- D_{2x}^{2D} = D₂^(x) ⊗ I_{N_y} (x second derivative)
- D_{2y}^{2D} = I_{N_x} ⊗ D₂^(y) (y second derivative)

Proof: [D₂^(x) ⊗ I_{N_y}]_{iN_y+j} = Σ_κ [D₂^(x)]_{iκ} p[κ,j] = (D_x^(2) p)_{ij}. QED.

### Checkerboard Mode

p_j = P₀(−1)^j gives zero central-difference gradient: (p_{j+1}−p_{j-1})/(2h) = 0. This ghost mode requires DCCD suppression (see [[WIKI-T-002]]).

### Null Space & Pin Condition

| N | Null dim | Condition # | Note |
|---|---|---|---|
| 4 | 8 | ~10¹⁷ | Boundary asymmetry dominates |
| 8 | 4 | ~10¹⁰ | Interior contribution grows |
| 16 | 2 | ~10⁶ | Improving |
| ≥32 | 1 | ~10⁴ | Theoretical (1 with O(h⁴) promotion) |

Pin condition (center node p=0) is mandatory. O(h⁴) boundary promotion resolves excess null dimensions.

### Neumann BC Implementation

Replace row 0 first equation with p'₀=0. Density gradient term vanishes: (L_CCD^ρ p)₀ = p''₀/ρ₀.

### Matrix-Free Evaluation

4-step sweep: x-sweep (block Thomas) → x-operator → y-sweep → y-operator add. Total: O(N_x N_y).

### Computational Cost

| Phase | Cost | Note |
|---|---|---|
| 1D CCD matrix | O(N²) | Initialization (once) |
| Kronecker assembly | O(N_x N_y²) | scipy.sparse.kron |
| Density update | O(n) | Each timestep |
| LGMRES solve | O(nk) | k = iteration count |
