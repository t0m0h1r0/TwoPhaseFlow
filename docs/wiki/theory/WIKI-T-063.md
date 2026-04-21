---
ref_id: WIKI-T-063
title: "FCCD Face-Flux PPE: Adjoint Gradient Design, Defect Correction, and IIM/GFM Integration"
domain: theory
status: STABLE
superseded_by: null
sources:
  - description: Internal research memo — FCCD PPE design, defect correction, IIM/GFM (2026-04-22)
  - description: "Popinet, S. (2003). Gerris: a tree-based adaptive solver for the incompressible Euler equations in complex geometries. JCP 190(2), 572–600."
  - description: "Liu, X.-D., Fedkiw, R. P., & Kang, M. (2000). A boundary condition capturing method for Poisson's equation on irregular domains. JCP 160(1), 151–178. (IIM/GFM basis)"
  - description: "Leveque, R. J., & Li, Z. (1994). The immersed interface method for elliptic equations with discontinuous coefficients and singular sources. SIAM J. Numer. Anal. 31(4), 1019–1044."
depends_on:
  - "[[WIKI-T-046]]: FCCD: Face-Centered Upwind Combined Compact Difference"
  - "[[WIKI-T-004]]: Balanced-Force Condition"
  - "[[WIKI-T-005]]: Defect Correction Method for PPE"
  - "[[WIKI-T-021]]: IIM-CCD for Pressure Solver"
  - "[[WIKI-T-060]]: GPU-Native FVM Projection"
  - "[[WIKI-X-029]]: BF Operator Consistency for CCD/FCCD"
consumers:
  - domain: impl
    description: "ns_pipeline.py: design target for staggered face-flux projection path (CHK-172 PoC)"
  - domain: experiment
    description: "ch13_05 rising bubble: BF residual blow-up from projection closure mismatch"
  - domain: theory
    description: "Variable-density FCCD NS solver: full adjoint PPE derivation"
tags: [fccd, ppe, face_flux, adjoint, defect_correction, iim, gfm, krylov, balanced_force, two_phase]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# FCCD Face-Flux PPE: Adjoint Gradient Design, Defect Correction, and IIM/GFM Integration

## §1 Setup: The Incompressibility Projection

The projection step advances velocity from $u^*$ (intermediate) to $u^{n+1}$ (divergence-free):

$$u_f^{n+1} = u_f^* - \Delta t\,\beta_f\,(G_h^{bf}\,p)_f$$

Applying $D_h^{bf}$ and enforcing $D_h^{bf}\,u^{n+1} = 0$:

$$\boxed{D_h^{bf}\!\left(\beta_f\,G_h^{bf}\,p\right) = \frac{1}{\Delta t}\,D_h^{bf}\,u^*}$$

This is the **face-flux PPE**. It must be built from $G_h^{bf}$ and $D_h^{bf}$ that are used elsewhere; building a separate "PPE Laplacian" and a separate "corrector gradient" breaks BF.

---

## §2 The Adjoint Requirement

Let $\langle\cdot,\cdot\rangle$ denote the discrete $\ell^2$ inner product on the computational mesh. Define the gradient/divergence pair to satisfy:

$$D_h^{bf} = -(G_h^{bf})^* \quad\Longleftrightarrow\quad \langle D_h^{bf}\,\mathbf{v},\,q\rangle = -\langle \mathbf{v},\,G_h^{bf}\,q\rangle$$

for all discrete vector fields $\mathbf{v}$ and scalar fields $q$ satisfying homogeneous BCs.

### Consequence: SPD operator

The combined operator

$$A_h = -D_h^{bf}\!\left(\beta_f\,G_h^{bf}\,\cdot\right)$$

satisfies, for any $p$ with $\beta_f > 0$:

$$\langle p,\,A_h\,p\rangle = \langle G_h^{bf}\,p,\,\beta_f\,G_h^{bf}\,p\rangle \geq 0$$

$A_h$ is symmetric positive semi-definite; after removing the one-dimensional null space (constant on Neumann domains), it is SPD. This enables **Conjugate Gradient** as the primary solver.

### When adjoint breaks

- Compact CCD closure rows near boundaries are often not adjoint to the corresponding divergence rows
- Node-to-face interpolation of CCD gradients breaks adjoint unless the mapping is explicitly adjoint-consistent
- Separate implementations for "PPE build" and "pressure correction subtract" are the most common source

**Fix**: define $G_h^{bf}$ first as a face operator; derive $D_h^{bf}$ as $-(G_h^{bf})^*$ by construction; use both in every path that touches pressure.

---

## §3 Iterative Solvers

### 3.1 Primary choice: PCG

If $D_h^{bf} = -(G_h^{bf})^*$ holds exactly, use Preconditioned Conjugate Gradient:

- Solver: PCG (or CG without preconditioner for debugging)
- Preconditioner: low-order face-flux Laplacian $A_L = -D_2(\beta_f G_2)$ + AMG or geometric MG

PCG is the default. If boundary treatment or IIM corrections break exact symmetry, switch to GMRES/FGMRES.

### 3.2 Matrix-free matvec

FCCD compact operators couple face unknowns. Rather than assembling the full matrix, implement:

$$y = A_h\,x = -D_h^{bf}\!\left(\beta_f\,G_h^{bf}\,x\right)$$

as a function and pass it to a Krylov method via `LinearOperator`. This:
- Hides compact operator complexity (line solves)
- Makes IIM/jump corrections localised modifications
- Reuses GPU-native FCCD primitives from `fccd.py`

Reference: `PPESolverFVMMatrixFree` in WIKI-L-026 (GPU line-solve preconditioner) for analogous pattern.

### 3.3 Solver selection guide

| Scenario | Solver | Preconditioner |
|----------|--------|----------------|
| Adjoint relation holds, $\beta_f > 0$ | PCG | Low-order face-flux AMG |
| IIM correction breaks symmetry | FGMRES | Low-order face-flux AMG |
| Small domain, debugging | Direct (spsolve) | — |
| GPU, large $N$ | FGMRES + PCR line preconditioner | See WIKI-T-060 |

---

## §4 Defect Correction for High-Order FCCD

Defect correction separates accuracy (high-order residual evaluation) from robustness (low-order inner solver):

**Outer iteration** (index $m$):

1. Evaluate residual with high-order FCCD operator: $r^{(m)} = b - A_H\,p^{(m)}$
2. Solve correction with low-order operator: $A_L\,\delta p = r^{(m)}$
3. Update: $p^{(m+1)} = p^{(m)} + \delta p$

**Role assignment**:

| Operator | Role | Order |
|----------|------|-------|
| $A_H = -D_h^{bf}(\beta_f G_h^{bf})$ | Residual evaluation (matvec) | FCCD (4th–6th) |
| $A_L = -D_2(\beta_f G_2)$ | Inner correction solve | 2nd face-flux |

**Critical requirement**: $A_L$ must share the **same** $\beta_f$, BCs, and jump conditions as $A_H$. A plain second-order Laplacian (without $\beta_f$ or jump) fails to approximate $A_H$ near the interface and the correction stagnates.

**Convergence**: defect correction converges at the rate $\|I - A_L^{-1}A_H\|$; for smooth regions this is small, but for large density-ratio two-phase flow near the jump, conditioning depends critically on whether the jump is consistently handled in both $A_H$ and $A_L$.

---

## §5 IIM/GFM Integration for the Pressure Jump

In two-phase flow, the pressure satisfies the jump condition:

$$[p]_\Gamma = \sigma\kappa, \qquad [\beta_f\,\partial_n p]_\Gamma = 0$$

(The second condition holds when the normal stress balance is already absorbed into surface tension.)

### 5.1 GFM approach (simpler, first implementation)

When the FCCD stencil crosses $\Gamma$ at face $f$, modify the face flux:

$$(G_h^{bf}\,p)_f \;\longrightarrow\; (G_h^{bf}\,p)_f^{\mathrm{jump}} = (G_h^{bf}\,p)_f - \frac{[p]_\Gamma}{H_f}$$

where $H_f$ is the effective grid spacing at face $f$ and $[p]_\Gamma = \sigma\kappa$ is the jump at the interface location crossing face $f$.

This is inserted only at interface-crossing faces; bulk faces are unchanged. The correction vector $c_\Gamma$ is assembled once per time step when $\sigma\kappa$ is updated.

**Pros**: minimal operator changes; same bulk FCCD stencil everywhere  
**Cons**: limited to 2nd-order accuracy at the interface; jump must be interpolated to face centre

### 5.2 IIM approach (higher order)

For a compact FCCD operator, the stencil relation at face $f$ near $\Gamma$ is:

$$M_f\,\mathbf{g} = R_f\,\mathbf{p} + c_\Gamma^{IIM}$$

where $c_\Gamma^{IIM}$ is derived from the Taylor expansion of the jump conditions $[p]_\Gamma$, $[\partial_n p]_\Gamma$, and (for second-order jump conditions) $[\partial_{nn} p]_\Gamma$.

This maintains the compact structure while capturing the discontinuity to higher order. The derivation is row-local: only rows whose stencil crosses $\Gamma$ are modified.

**Pros**: consistent with the FCCD compact structure; achievable 4th-order at the interface  
**Cons**: derivation is nontrivial; requires at least $[p]_\Gamma$ and $[\beta\partial_n p]_\Gamma$; implementation effort is high for moving interfaces

### 5.3 Staged implementation roadmap

| Phase | Content | BF quality |
|-------|---------|------------|
| Phase 1 | Low-order face-flux operator ($G_2$, $D_2$), GFM jump on crossing faces | Spurious current $O(h)$ |
| Phase 2 | FCCD bulk operator ($G_h^{bf}$, $D_h^{bf}$), GFM correction on crossing faces, defect correction outer loop | Spurious current $O(h^2)$–$O(h^3)$ |
| Phase 3 | Full IIM row correction for compact FCCD rows at $\Gamma$, high-order $\kappa$ via HFE | Spurious current $O(h^3)$–$O(h^4)$ |

Phase 1 → Phase 2 transition is the most impactful for BF residual reduction. Phase 3 is a research-level upgrade.

---

## §6 Capillary Pressure as a PPE Source (Alternative to CSF Body Force)

An alternative to CSF (body force in momentum) is to embed the capillary jump directly in the PPE:

**Method 1 (CSF)**: add $f_\sigma = \sigma\kappa\nabla\psi$ to the momentum predictor, solve PPE with zero jump:

$$D_h^{bf}(\beta_f G_h^{bf} p) = \frac{1}{\Delta t} D_h^{bf} u^*_{\mathrm{with\ CSF}}$$

**Method 2 (capillary-jump PPE)**: solve PPE with jump condition $[p]_\Gamma = \sigma\kappa$ (IIM/GFM), no body force in momentum:

$$D_h^{bf}(\beta_f G_h^{bf} \tilde p) = \frac{1}{\Delta t} D_h^{bf} u^*, \qquad [\tilde p]_\Gamma = \sigma\kappa$$

In static equilibrium, Method 2 is exact: the pressure gradient automatically cancels surface tension by construction. Method 1 requires BF operator consistency to achieve the same. For BF-priority implementations, Method 2 (when combined with IIM jump conditions) is the stronger option.

---

## §7 Relationship to Existing Solver Architecture

| Component | Role | Reference |
|-----------|------|-----------|
| `fccd.py` `FCCDSolver.face_gradient` | Provides $G_h^{bf}$ | WIKI-L-024 |
| `ns_pipeline._fvm_pressure_grad` | Current face-gradient (2nd-order FVM) | WIKI-L-022 |
| `PPESolverFVMMatrixFree` | Matrix-free Krylov template for face-flux PPE | WIKI-L-026, WIKI-T-060 |
| `iim_solver.py` | IIM jump decomposition $p = \tilde p + p_\sigma$ | WIKI-X-020 |
| `RhieChowInterpolator` | RC face velocity (BF-unsafe path, see §5.5 of WIKI-X-029) | WIKI-T-017 |
| `gradient_operator.py` `FVMDivergenceOperator` | PoC divergence from CHK-171/172 | WIKI-E-030 / ch13_05 PoC |

CHK-172 demonstrated that fixing PPE RHS divergence alone (without matching the corrector $G_h$) is insufficient. Full BF requires the corrector to use **the same face gradient** as the PPE build — the adjoint relation of §2.
