---
ref_id: WIKI-X-030
title: "Viscous Term Design Guide for CCD/FCCD Two-Phase NS: Bulk-CCD vs Interface-Band Split, Defect Correction, and Implicit Solver Architecture"
domain: cross-domain
status: STABLE
superseded_by: null
sources:
  - description: Internal research memo — viscous term design for two-phase CCD/FCCD NS (2026-04-22)
depends_on:
  - "[[WIKI-T-064]]: ∇·(2μD) Staggered MAC Discretization"
  - "[[WIKI-T-033]]: Extended CN × CCD: Viscous Time Integration Design"
  - "[[WIKI-T-041]]: Third-Order Time Integration: AB3 Cross-Term Extrapolation"
  - "[[WIKI-L-016]]: CN Advance Strategy Pattern"
  - "[[WIKI-X-029]]: BF Operator Consistency for CCD/FCCD"
  - "[[WIKI-T-003]]: Variable-Density Projection: CN cross-derivative trap"
consumers:
  - domain: impl
    description: "ns_pipeline.py ViscousTerm predictor + implicit Helmholtz solver"
  - domain: theory
    description: "SP-K: viscous term short paper"
tags: [viscous, ccd, interface_band, bulk_split, defect_correction, implicit_helmholtz, two_phase, design_guide, energy_dissipation]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# Viscous Term Design Guide for CCD/FCCD Two-Phase NS

## §0 Operator Identity: Stress-Divergence Owns Viscosity

The viscous term is not selected by asking "CCD, FCCD, or UCCD?" at the top
level.  Its governing object is the conservative variable-viscosity
stress-divergence operator

$$
\mathbf{F}_\mu = \nabla\cdot(2\mu D(\mathbf{u})).
$$

Therefore the scheme hierarchy is:

1. **Primary operator**: conservative stress assembly + conservative stress
   divergence, even at low order.
2. **Bulk accuracy option**: CCD may be used inside Layer A only, i.e. for
   smooth-region velocity gradients used to build stresses.
3. **Interface-band fallback**: low-order / one-sided / jump-aware gradients
   are mandatory where stencils cross the phase interface.
4. **Implicit solve**: the robust low-order conservative operator is the
   solve/preconditioner body; high-order bulk CCD enters as a defect correction
   $L_\mu^H - L_\mu^L$.

The efficient CCD-family production path is the phi/psi-gated split:

$$
L_\mu\mathbf{u}
= (1-\chi_\Gamma)\,\mu\Delta_h^{CCD}\mathbf{u}
+ \chi_\Gamma\,\nabla_h\cdot(2\mu D_h(\mathbf{u})).
$$

Here $\chi_\Gamma$ is built from the transported interface field, e.g.
$\psi\in(\varepsilon_\psi,1-\varepsilon_\psi)$ with a one-cell dilation.
This keeps CCD as the bulk workhorse while preventing the global
$\mu\nabla^2\mathbf{u}$ anti-pattern near the viscosity jump.

FCCD remains a pressure / surface-tension balanced-force tool because its value
is face-locus alignment.  It is not the viscous operator's primary design axis.
UCCD6 remains a transport / advection stabilisation tool; using its
hyperviscosity as the viscous term's main mechanism would obscure the physical
stress tensor and its energy-dissipation requirement.

---

## §1 Core Split: Layer A CCD (Bulk) vs Low-Order Conservative (Interface Band)

The key architectural decision is to **separate accuracy from robustness** by region:

| Region | Operator | Rationale |
|--------|----------|-----------|
| Bulk (far from interface) | CCD velocity gradients (Layer A) | Smooth field → high order valid |
| Interface band | Low-order conservative (all layers) | $u \in C^0$ but $\nabla u \notin C^0$ → CCD invalid |

**What CCD contributes**: higher-order velocity gradients at Layer A (see WIKI-T-064 §4), giving lower truncation error in the smooth bulk. **What CCD cannot contribute**: accuracy at stencils that cross the interface, where velocity gradient kinks make the smoothness assumption false.

The Layer B (stress assembly) and Layer C (stress divergence) are always computed with the same conservative form regardless of region — they do not participate in the high-order/low-order split.

---

## §2 Interface Band Definition

The interface band is the set of cells (and corners) where a Layer A gradient stencil crosses the interface. Two practical definitions:

### Definition A: Level-set proximity

A cell/corner belongs to the interface band if

$$|\phi|_{i,j} \leq m\,h \quad \text{or} \quad \psi_{i,j} \in [\varepsilon_1,\, 1-\varepsilon_1]$$

where $m = 2$–$3$ gives a safe margin around the thin interface region. Conservative choice is $m = 3$.

### Definition B: Stencil-crossing detection

A gradient stencil is in the interface band if any two points in its support have opposite phase indicators (e.g., $\phi_L < 0$ and $\phi_R > 0$). This is exact by construction but requires checking at every gradient evaluation.

**Recommended default**: Definition A with $m=3$ is simpler to implement and avoids expensive stencil inspection at every point. Tighten to Definition B if performance permits.

---

## §3 τ_xy is the Hardest Term

The shear stress $\tau_{xy} = \mu(\partial_y u + \partial_x v)$ requires special attention because:

1. It mixes two velocity components from different grid locations (x-faces and y-faces)
2. Its stencil accesses corners, which are shared by four cells — interface crossings are more frequent
3. The corner viscosity $\mu_{i+1/2,j+1/2}$ must be defined consistently (see WIKI-T-064 §6/§7)
4. Shear stress continuity $[\mu(\partial_y u + \partial_x v)]_\Gamma = 0$ is physically required and must be approximately satisfied

**Interface band rule for τ_xy**: whenever any of the four cells forming a corner belongs to the interface band, that corner uses the low-order one-sided or low-order central formula for both $(\partial_y u)_\oplus$ and $(\partial_x v)_\oplus$. Do not mix high-order for one gradient and low-order for the other at the same corner.

**τ_xy = τ_yx rule**: a single array must be computed and shared. Separate computation for x-momentum and y-momentum with different averaging or stencils produces an asymmetric stress tensor and destroys the discrete energy dissipation property.

---

## §4 DCCD Safety Rules for Viscous Terms

Dissipative CCD (DCCD) filters may be applied to the viscous path only under symmetric conditions:

| Application | Safe? |
|-------------|-------|
| $u$ or $v$ field before Layer A gradients (both components, same filter) | Conditionally yes |
| Layer A gradient of $u$ only (leaving $v$ unfiltered at same corner) | **No** — asymmetric τ_xy |
| Viscous force $(F_\mu)_x$ only (without matching $(F_\mu)_y$) | **No** — breaks energy balance |
| Applied after Layer C (as a force smoother) uniformly | Conditionally yes |

Rule: **if DCCD is applied anywhere in the viscous path, it must preserve the symmetry of the stress tensor**. This is more restrictive than it might appear because $\tau_{xy}$ involves both $u$ and $v$.

---

## §5 Defect Correction for Implicit Viscous Helmholtz

### 5.1 Problem setup

In the Crank-Nicolson predictor, the viscous Helmholtz system is:

$$\left(I - \frac{\Delta t}{2\rho}\,L_H\right)\mathbf{u}^* = \text{RHS}$$

where $L_H = \nabla\cdot(2\mu\,D_h^{(H)})$ uses CCD velocity gradients (bulk only; interface band uses low-order). Solving this directly with a Krylov method requires a good preconditioner because $L_H$ is a compact operator.

### 5.2 Defect correction algorithm

Define:
- $L_H$: high-order viscous operator (CCD bulk + low-order interface band)
- $L_L$: low-order viscous operator (conservative 2nd-order throughout)
- $A_H = I - (\Delta t/2\rho)L_H$, $A_L = I - (\Delta t/2\rho)L_L$

Outer iteration (index $m$):

1. Evaluate residual with high-order operator: $r^{(m)} = \text{RHS} - A_H\,\mathbf{u}^{(m)}$
2. Solve correction with low-order operator: $A_L\,\delta\mathbf{u} = r^{(m)}$
3. Update: $\mathbf{u}^{(m+1)} = \mathbf{u}^{(m)} + \delta\mathbf{u}$

### 5.3 Requirements for $L_L$

$L_L$ must share with $L_H$:
- The **same $\mu$ field** (same cell-center and corner viscosity)
- The **same boundary conditions** (no-slip, symmetry)
- The **same interface band switching** (so both are low-order in the same region)
- The **same null space** (no additional zero modes)

A plain Laplacian $\mu_0\nabla^2$ used as $L_L$ fails these requirements near the density/viscosity jump and converges poorly. The 2nd-order conservative stress-divergence form (WIKI-T-064 §8, low-order stencil) is the correct $L_L$.

### 5.4 Solver for $A_L$

$L_L$ has a second-order conservative structure well-suited to:
- **ADI (alternating direction implicit)**: line-by-line Thomas algorithm if operators are separable; exact for constant $\mu$, approximate for variable $\mu$ (Picard iteration needed)
- **Krylov (CG/GMRES)**: when $A_L$ is SPD (checked: $L_L$ is negative semi-definite for $\mu \geq 0$), PCG + AMG is effective
- **LU (small domains)**: direct factorisation; only feasible for 2D at moderate $N$

For the existing `ICNAdvance` hierarchy (WIKI-L-016), $L_L$ corresponds to `PicardCNAdvance` and $L_H$ corresponds to `ImplicitCNAdvance` (Phase 3 in the roadmap); defect correction wraps them as `DefectCorrectionCNAdvance`.

### 5.5 When defect correction is most valuable

| Scenario | Value of defect correction |
|----------|---------------------------|
| High CCD accuracy in smooth bulk | High — bulk benefits; interface doesn't |
| High viscosity ratio $\mu_l/\mu_g$ | High — $A_L$ captures jump correctly |
| Non-uniform grid | High — CCD metric terms only enter residual |
| Small $\Delta t$ (capillary flow) | Lower — viscous Helmholtz is near identity |
| Uniform $\mu$, single phase | Lowest — standard CN solve suffices |

---

## §6 Energy Dissipation Requirement and Verification

### 6.1 Requirement

The discrete viscous term must satisfy:

$$\langle \mathbf{u},\, \mathbf{F}_\mu \rangle_h \leq 0$$

This holds for the conservative form (WIKI-T-064 §9) with consistent $\mu$ placement and shared $\tau_{xy}$. It may fail when:
- $\tau_{xy}$ and $\tau_{yx}$ are computed separately with different stencils
- $\mu_{corner}$ is evaluated inconsistently
- Layer C uses a non-conservative formula
- DCCD is applied asymmetrically

### 6.2 Verification protocol

**Test 1 — Couette flow**: viscous force should reduce kinetic energy monotonically. Any energy increase → structural problem.

**Test 2 — Manufactured solution** (smooth, single-phase): convergence rate should match CCD order in bulk, drop to 2nd at interface band.

**Test 3 — Static droplet** (two-phase, $\mathbf{u}=0$): viscous term should be zero to machine precision (since $\mathbf{D}(\mathbf{0})=\mathbf{0}$). Nonzero value indicates $\mu$ placement bug.

**Test 4 — High viscosity ratio** ($\mu_l/\mu_g = 55$, water/air): energy should decay; if it grows, corner viscosity averaging is wrong.

**Test 5 — Energy balance diagnostic**: monitor $\langle \mathbf{u}^n, (F_\mu)^n \rangle_h$ at each step; flag if positive.

---

## §7 Interaction with the PPE/BF Path

Viscous terms do not participate in the balanced-force (BF) pressure-surface tension balance. However, there are two coupling points to be aware of:

### 7.1 $\mu$ placement consistency

The corner viscosity $\mu_{i+1/2,j+1/2}$ used in $\tau_{xy}$ must not conflict with the density weighting $\beta_f = (1/\rho)_f$ used in the PPE. Both are face/corner quantities, but they are independent. The only requirement is internal consistency within each sub-system.

### 7.2 Cross-derivative terms and BF residual

The cross terms $\partial_y(\mu\partial_x v)$ and $\partial_x(\mu\partial_y u)$ generate force contributions that are neither purely viscous nor purely pressure-related near the interface. Under high viscosity ratio, these can appear as spurious contributions in the BF residual diagnostic if the diagnostic does not account for viscous anisotropy. This is a diagnostic artefact, not a BF failure.

**Rule**: do not use BF residual alone to diagnose viscous-term correctness. Use the energy balance test (§6.2 Test 5) independently.

---

## §8 Four-Phase Implementation Roadmap

This roadmap follows the memo's recommended sequence for maximum safety.

### Phase 1 — Low-order conservative viscous operator (foundation)

**Goal**: get the correct structure working at 2nd order.

- Implement Layer A, B, C as described in WIKI-T-064 §4–§8
- Use arithmetic-average corner viscosity as default
- No CCD at this stage
- Validate with Tests 1–5 above

**Acceptance gate**: energy decays monotonically for Couette and static droplet; manufactured solution gives 2nd-order spatial convergence.

### Phase 2 — Interface band switching

**Goal**: protect interface-crossing stencils.

- Add band detection (Definition A, $m=3$)
- In the interface band: force all Layer A gradients to 2nd-order one-sided or central
- In the bulk: still use 2nd-order (not CCD yet)
- Validate: static droplet spurious current should not increase; Couette convergence unchanged

**Acceptance gate**: Phase 1 tests still pass; high-viscosity-ratio droplet shows no energy increase.

### Phase 3 — Bulk CCD Layer A gradients

**Goal**: raise accuracy in smooth bulk regions.

- Replace 2nd-order Layer A gradients with CCD in the bulk (non-band) region
- Interface band still uses 2nd-order from Phase 2
- Validate: manufactured solution in single-phase shows CCD-order spatial convergence; two-phase results unchanged (as expected, since interface controls)

**Acceptance gate**: single-phase manufactured solution reaches design order; two-phase tests from Phase 1–2 unchanged.

### Phase 4 — Defect correction for implicit Helmholtz

**Goal**: high-order temporal accuracy with robust implicit solve.

- Implement $L_L$ (Phase 3 operator as conservative inner)
- Implement $L_H$ (CCD bulk + Phase 2 band fallback as outer)
- Wrap in `DefectCorrectionCNAdvance` extending `ICNAdvance` (WIKI-L-016 roadmap Phase 3–4)
- Validate: compare against direct solve of $A_H$ on small problem; defect correction should match

**Acceptance gate**: defect correction agrees with direct $A_H$ solve; implicit Helmholtz converges faster than plain $A_H$ solve.

---

## §9 Anti-Pattern Table

| Anti-pattern | Failure mode |
|--------------|-------------|
| Use $\mu\nabla^2 u$ for variable-$\mu$ flow | Cross-terms dropped; shear stress discontinuous at interface |
| Compute $\tau_{xy}$ and $\tau_{yx}$ separately | Asymmetric stress tensor; energy not conserved |
| Apply CCD at Layer A stencil crossing interface | Kink amplified by high-order finite difference; oscillations |
| Different $\mu$ averaging for $\tau_{xy}$ in x- vs y-momentum | Asymmetric $\tau_{xy}$; torque at interface |
| $L_L$ for defect correction without same $\mu$/BC | Correction diverges near density/viscosity jump |
| Apply DCCD asymmetrically across velocity components | Asymmetric Layer A → asymmetric $\tau_{xy}$ → energy injection |
| Use viscous $\mu\nabla^2$ for implicit LHS but stress-divergence for force | Inconsistent operator; convergence failure for Helmholtz |
| Non-conservative Layer C | Energy property lost; possible energy gain |
| Ignore cross terms $\partial_x(\mu\partial_y u)$, $\partial_y(\mu\partial_x v)$ | O(Δt) accuracy near high-$\mu$-ratio interfaces (WIKI-T-003) |

---

## §10 Cross-References

| Entry | Relation |
|-------|----------|
| [[WIKI-T-064]] | Full discrete staggered MAC formulas for $\nabla\cdot(2\mu D)$ |
| [[WIKI-T-033]] | Extended CN × CCD: Padé/Richardson for viscous time integration |
| [[WIKI-T-041]] | AB3 extrapolation for cross-derivative explicit part |
| [[WIKI-L-016]] | `ICNAdvance` strategy pattern: Phase 3–4 roadmap entries |
| [[WIKI-T-003]] | CN cross-derivative O(Δt) trap at high-$\mu$-ratio interface |
| [[WIKI-X-029]] | BF operator consistency guide (pressure/surface tension — separate from viscous) |
| [[WIKI-X-025]] | Level-2 NS scheme: AB2 advection + CN viscous + semi-implicit ST |
| [[WIKI-X-026]] | Stiffness policy: why viscous must be implicit on non-uniform grids |
