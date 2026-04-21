---
ref_id: WIKI-T-060
title: "GPU-Native FVM Projection: Face-Local Matrix-Free Operator and Variable-Batched Line Preconditioner"
domain: theory
status: PROPOSED
superseded_by: null
sources:
  - path: docs/memo/short_paper/SP-F_gpu_native_fvm_projection.md
    description: Full derivation and roadmap
  - path: src/twophase/ppe/fvm_spsolve.py
    description: Current global sparse direct-solve path
  - path: src/twophase/ppe/ppe_builder.py
    description: Existing face-local FVM coefficient construction
  - path: src/twophase/linalg_backend.py
    description: Current PCR special case for common tridiagonal coefficients
  - path: docs/memo/cupy_optimization_guidelines.md
    description: Existing GPU invariants: zero hot-loop transfer, cache device operators
depends_on:
  - "[[WIKI-T-017]]: FVM Reference Methods — PPE Face Coefficients, Rhie-Chow, Balanced-Force"
  - "[[WIKI-T-005]]: Defect Correction Method for PPE"
  - "[[WIKI-L-015]]: CuPy / GPU Backend Unification"
  - "[[WIKI-L-022]]: G^adj FVM-Consistent Pressure Gradient"
consumers:
  - domain: code
    description: WIKI-L-026 implementation roadmap for `PPESolverFVMMatrixFree`
  - domain: cross-domain
    description: WIKI-X-018 performance-axis companion to H-01 / A-01
tags: [fvm, gpu, ppe, matrix_free, pcr, tridiagonal, line_preconditioner, d2h_h2d, research_proposal]
compiled_by: Codex GPT-5
compiled_at: "2026-04-21"
---

# GPU-Native FVM Projection

## Context

The current non-uniform FVM stack already computes several hot-path pieces in `backend.xp`:

- `_fvm_pressure_grad` in `ns_pipeline.py`,
- `RhieChowInterpolator.face_velocity_divergence`,
- `PPEBuilder.build_values`.

The remaining performance bottleneck is the global PPE solve in `PPESolverFVMSpsolve.solve`, which still routes the operator through a CSR + `spsolve` abstraction.

## ResearchArchitect verdict

The performance problem is **not** that FVM itself is intrinsically sequential. The problem is that the current implementation expresses a face-local operator as a global sparse matrix and therefore loses access to line parallelism.

The correct theory is:
$$
L_{\mathrm{FVM}}(\rho)\,p
\;=\;
\sum_{a=1}^{d} D_a\,A_a(\rho)\,G_a\,p,
$$
where $G_a$ is a face gradient, $A_a(\rho)$ is the harmonic face coefficient, and $D_a$ is the face-to-node divergence. This representation is matrix-free, face-local, and device-native.

## Matrix-free face-local operator

For axis $a$:

$$
(G_a p)_f = \frac{p_R - p_L}{H_{a,f}},
\qquad
A_{a,f}(\rho)=\frac{2}{\rho_L+\rho_R},
\qquad
(D_a q)_i = \frac{q_{i+1/2}-q_{i-1/2}}{\Delta V_i}.
$$

Then
$$
L_{\mathrm{FVM}}(\rho)\,p
=
\sum_a D_a\!\left(A_a(\rho)\,G_a p\right).
$$

This is algebraically identical to the coefficients assembled by `PPEBuilder.build_values`, but it avoids explicit CSR construction in the hot loop.

## Variable-batched line preconditioner

Holding all transverse indices fixed, each axis contribution reduces to a tridiagonal line operator
$$
(\mathcal{T}_{a,\mathbf{m}} p)_k
=
c^-_{k,\mathbf{m}} p_{k-1,\mathbf{m}}
+ c^0_{k,\mathbf{m}} p_{k,\mathbf{m}}
+ c^+_{k,\mathbf{m}} p_{k+1,\mathbf{m}}.
$$

Because $\rho$ varies spatially, every line has different $(c^-, c^0, c^+)$. The missing GPU primitive is therefore a **variable-batched tridiagonal solve**
$$
\text{PCRVar}(a_{k,b}, d_{k,b}, c_{k,b}, r_{k,b}),
$$
not the current common-matrix batched solve used for compact filters.

The existing PCR recurrence in `linalg_backend.py` already gives the special case where $(a,d,c)$ are shared across batches. Replacing broadcast `(n,1)` diagonals by full `(n,B)` diagonals yields the required generalisation.

## Why this is not ADI-redux

The line solves must be used **inside Krylov as a preconditioner**, not as a standalone split solver. In that role:

- the exact fixed point remains $L_{\mathrm{FVM}}(\rho)\,p = b$,
- any line-splitting approximation changes convergence speed only,
- no ADI splitting error enters the solved equation.

FGMRES is the safest default because the preconditioner may evolve with the density field across timesteps.

## D2H / H2D boundary

The hot-loop invariant is:

1. geometry arrays upload once at grid build,
2. $\rho$-dependent coefficients form in `backend.xp`,
3. matrix-free apply, preconditioning, and Krylov all stay on device.

Under this invariant the PPE hot loop has zero mandatory host-device transfers. D2H / H2D remains only at I/O boundaries or in modules that are intentionally CPU-serial and outside the FVM projection path.

## A3 traceability

| Layer | Decision |
|---|---|
| Equation | $L_{\mathrm{FVM}}(\rho)\,p = \sum_a D_a A_a(\rho) G_a p$ |
| Discretisation | face-local gradient + harmonic face flux + node divergence + per-line tridiagonal restriction |
| Linear algebra | variable-batched PCR/CR line solves used as Krylov preconditioner |
| Code | `_fvm_pressure_grad`, `RhieChowInterpolator`, `PPEBuilder.build_values`, `linalg_backend._pcr_solve_batched` |

## Implementation implications

- A new additive PPE solver should be introduced; the legacy `PPESolverFVMSpsolve` remains intact.
- The new solver should expose a matrix-free `apply(p, rho)` and a device-native line-coefficient builder.
- `backend` should gain a variable-batched tridiagonal solve primitive derived from the current PCR implementation.
- Verification must include both algebraic parity (matrix-free vs CSR) and a no-transfer grep gate on the solve loop.
