---
ref_id: WIKI-T-034
title: "Consistent IIM Reprojection: Variational Weighted-Hodge Projection for Post-Rebuild Velocity"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: "docs/memo/理論_reproject_velocity_再構成直後投影の整合設計.md"
    description: "Theory: reproject_velocity as density-weighted Hodge projection"
  - path: "docs/memo/設計_reproject_velocity_整合実装仕様_v0.md"
    description: "Implementation spec v0: phased variable-density + guard + IIM"
  - path: "docs/memo/検討_reproject_velocity_演算子整合+界面条件整合_同時導入方針.md"
    description: "Strategy: simultaneous operator + interface condition consistency"
  - path: "src/twophase/simulation/ns_pipeline.py"
    description: "Implementation: reproject_mode enum, consistent_iim path"
consumers:
  - domain: E
    usage: "exp12_20/21/22 reprojection mode selection; exp13_90/91 IIM statistics"
  - domain: X
    usage: "WIKI-X-014 recommended defaults; WIKI-X-012 fix path"
depends_on:
  - "[[WIKI-T-003]]"
  - "[[WIKI-T-004]]"
  - "[[WIKI-T-021]]"
  - "[[WIKI-T-035]]"
  - "[[WIKI-X-012]]"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-16
---

# Consistent IIM Reprojection

---

## 1. Problem: Three Failure Modes

After grid rebuild, the interpolated velocity $u^r = R_h u^n$ does not satisfy
the discrete incompressibility constraint $D_h^{n+1} u^r = 0$ due to the
commutator error:

$$
D_h^{n+1} R_h u^n - R_h D_h^n u^n = [D_h^{n+1}, R_h] \, u^n
$$

The current `_reproject_velocity` implementation has three structural failures:

### Mode 1 — Density-Weight Mismatch

The reprojection uses $\rho = 1$ (single-phase Laplace), while the main
time-step correction uses the physical two-phase density. This minimizes
$\|u - u^r\|_{L^2}$ instead of $\|u - u^r\|_{M_\rho}$, over-correcting
the high-density phase.

### Mode 2 — Adjoint Inconsistency

$D_h$ and $G_h$ are not adjoint under the same discrete inner product. The
projection is therefore not orthogonal and can amplify discrete kinetic energy.

### Mode 3 — Missing Interface Jump Conditions

The reprojection potential $\phi$ requires jump conditions at the interface:
$[\phi]_\Gamma = 0$ and $[(1/\rho)\,\partial_n \phi]_\Gamma = 0$. Omission
makes the gradient correction discontinuous near the interface, injecting
spurious velocity peaks per rebuild.

---

## 2. Variational Formulation

The reprojection is a constrained optimization:

$$
\min_u \;\frac{1}{2}(u - u^r)^T M_\rho (u - u^r)
\quad\text{subject to}\quad D_h u = 0
$$

**KKT system** yields the corrected PPE:

$$
D_h \, M_\rho^{-1} \, G_h \, \phi = D_h \, u^r
$$

**Velocity correction:**

$$
u = u^r - M_\rho^{-1} \, G_h \, \phi
$$

where $M_\rho$ is the mass-weighted diagonal (or block-diagonal) matrix with
$\rho = \rho_g + (\rho_l - \rho_g)\psi$.

---

## 3. Interface Conditions

The reprojection potential satisfies:

- $[\phi]_\Gamma = 0$ — continuity of potential (no new pressure jump injected)
- $[(1/\rho)\,\partial_n \phi]_\Gamma = 0$ — normal flux continuity

The surface tension jump $[p] = \sigma\kappa$ belongs to the main PPE, not the
reprojection. This distinction is critical: injecting $\sigma\kappa$ into the
reprojection would double-count the capillary pressure.

---

## 4. Energy Non-Amplification Guarantee

Under adjoint-consistent $D_h$, $G_h$ with correct interface conditions:

$$
\|u^{n+1}\|_{M_\rho} \le \|u^r\|_{M_\rho}
$$

The proof follows from orthogonality: the correction $M_\rho^{-1} G_h \phi$
lies in the range of $M_\rho^{-1} G_h$, which is $M_\rho$-orthogonal to the
kernel of $D_h$ when the adjoint relation holds.

---

## 5. Variable-Density-Only is Catastrophically Unstable

Applying Mode 1 fix alone (variable-density PPE) without Modes 2 and 3 is
**worse** than the legacy $\rho=1$ projection. Evidence from exp12_21:

| Configuration | $u_\text{peak}$ | $\text{div}_\text{peak}$ |
|---|---|---|
| legacy (rebuild_freq=10) | $8.43$ | $36.5$ |
| varrho-only (rebuild_freq=1) | $7.82\times10^{27}$ | $2.32\times10^{28}$ |
| varrho-only (rebuild_freq=10) | $7.82\times10^{27}$ | $2.32\times10^{28}$ |

The density-weighted PPE amplifies the adjoint error and interface discontinuity.
Simultaneous resolution of all three modes is required.

---

## 6. Acceptance Gate and Backtracking

The `consistent_iim` implementation adds a safety layer:

1. Solve base PPE (legacy correction).
2. Compute IIM jump correction $\delta q$ via `IIMStencilCorrector`.
3. Solve corrected PPE: $\phi_\text{iim} = \text{solve}(\text{div} + \delta q, \rho)$.
4. **Accept** if result is finite AND $\text{div}_\text{iim} \le 1.05 \times \text{div}_\text{base}$.
5. **Backtrack** on rejection: retry with $\delta q$ scaled by $\{0.5,\;0.25,\;0.125\}$.
6. If all backtrack attempts fail, fall back to base projection.

This guarantees the IIM correction never degrades below the legacy baseline.

**Diagnostic statistics** tracked per run:
`iim_attempts`, `iim_accepts`, `iim_rejects`, `iim_backtrack_accepts`,
`iim_crossings_total`, `div_sum_accepted`, `div_sum_rejected`.

---

## 7. Implementation Modes

| `reproject_mode` | Behaviour |
|---|---|
| `"legacy"` | Unit-density PPE correction (original) |
| `"variable_density_only"` | Density-weighted only — **disqualified** (see §5) |
| `"consistent_iim"` | IIM jump-aware + acceptance gate + backtracking |
| `"consistent_gfm"` | Skeleton stub (not yet implemented, falls back to legacy) |

---

## 8. Open Questions

1. **Geometric consistency:** deriving $D_h$, $G_h$ from the same discrete geometry
   (mimetic/SBP adjoint relation $D_h = -H^{-1} G_h^T H + B$).
2. **3D generalization:** extending the IIM stencil corrector to 3D interface crossings.
3. **PPEBuilder mismatch:** current PPEBuilder is FVM-based while CCD operates
   differently — long-term both main solve and reprojection should share a single PPE.

---

## One-Line Summary

Reprojection requires simultaneous density-weighting, adjoint-consistent operators,
and interface jump conditions; partial fixes (varrho-only) are catastrophically unstable.
