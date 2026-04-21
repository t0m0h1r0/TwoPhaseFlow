# SP-K: Viscous Term Discretization for CCD/FCCD Two-Phase NS — Stress-Divergence Form, Layer Architecture, Bulk/Interface Split, and Defect Correction

**Compiled**: 2026-04-22  
**Status**: STABLE (research memo)  
**Wiki entries**: WIKI-T-064 (discrete forms), WIKI-X-030 (design guide)  
**Depends on**: WIKI-T-003 (CN cross-term trap), WIKI-T-033 (extended CN design), WIKI-T-041 (AB3 cross-term), WIKI-L-016 (ICNAdvance pattern), WIKI-X-025 (Level-2 NS scheme), WIKI-X-026 (stiffness policy), WIKI-X-029 (BF operator guide)

---

## Abstract

Viscous term discretization for two-phase CCD/FCCD NS flows has five under-appreciated design constraints: (1) variable viscosity requires the stress-divergence form $\nabla\cdot(2\mu\mathbf{D})$, not the Laplacian form $\mu\nabla^2\mathbf{u}$; (2) velocity gradients are kinked at the interface ($u\in C^0$ but $\nabla u \notin C^0$), so high-order CCD must be restricted to the smooth bulk; (3) the shear stress $\tau_{xy} = \mu(\partial_y u + \partial_x v)$ is the hardest term and requires a shared single array to preserve discrete energy dissipation; (4) the implicit Helmholtz solve benefits from a defect correction split with a low-order conservative inner operator and a CCD-bulk outer residual; (5) DCCD applied asymmetrically to the viscous path destroys the energy dissipation property. The primary conclusion is that **the conservative stress-divergence form with a shared $\tau_{xy}$ is non-negotiable for variable-$\mu$ two-phase flow, and high-order CCD should be applied only to bulk velocity gradients (Layer A), never to interface-band stencils**.

---

## 1 Why `μ∇²u` is Wrong for Variable Viscosity

Under incompressibility ($\nabla\cdot\mathbf{u}=0$):

$$\nabla\cdot(2\mu\mathbf{D}) = \mu\nabla^2\mathbf{u} + 2\mathbf{D}\cdot\nabla\mu$$

The second term $2\mathbf{D}\cdot\nabla\mu$ is the **cross-derivative contribution** and is nonzero whenever $\nabla\mu \neq 0$. In two-phase flow, $\mu$ jumps at the interface (e.g., $\mu_l/\mu_g \approx 55$ for water/air), so $\nabla\mu$ is a delta function — the cross-derivative contribution is singular and cannot be dropped.

Using $\mu\nabla^2\mathbf{u}$ for variable-$\mu$ flow:
- Drops the tangential force from $\mu$ variation
- Does not enforce shear stress continuity $[\tau_{xy}]_\Gamma = 0$
- Generates spurious tangential velocities at the interface
- Breaks energy dissipation for high viscosity-ratio flows

---

## 2 2D Staggered MAC Layout

Staggered MAC (Harlow–Welch) placement:

| Quantity | Grid location |
|----------|--------------|
| $p$, $\mu$, $\rho$ | Cell center $(i,j)$ |
| $u$ | x-face $(i+\tfrac12,j)$ |
| $v$ | y-face $(i,j+\tfrac12)$ |
| $\tau_{xx}$, $\tau_{yy}$ | Cell center |
| $\tau_{xy} = \tau_{yx}$ | Corner $(i+\tfrac12,j+\tfrac12)$ |
| $(F_\mu)_x$ | x-face (same as $u$) |
| $(F_\mu)_y$ | y-face (same as $v$) |

Stress components in 2D:

$$\tau_{xx} = 2\mu\,\partial_x u, \quad \tau_{yy} = 2\mu\,\partial_y v, \quad \tau_{xy} = \mu(\partial_y u + \partial_x v)$$

---

## 3 Three-Layer Architecture

The discretisation is organised in three successive layers:

**Layer A — Velocity gradient generation**

Four gradient components at their natural locations:
- $(\partial_x u)_{i,j}$ at cell center — from $u$ at x-faces
- $(\partial_y v)_{i,j}$ at cell center — from $v$ at y-faces
- $(\partial_y u)_{i+1/2,j+1/2}$ at corner — from $u$ at x-faces
- $(\partial_x v)_{i+1/2,j+1/2}$ at corner — from $v$ at y-faces

**Layer B — Stress tensor assembly**

$$\tau_{xx,i,j} = 2\mu_{i,j}\,(\partial_x u)_{i,j}, \quad \tau_{yy,i,j} = 2\mu_{i,j}\,(\partial_y v)_{i,j}$$

$$\tau_{xy,i+1/2,j+1/2} = \mu_{i+1/2,j+1/2}\left[(\partial_y u)_{i+1/2,j+1/2} + (\partial_x v)_{i+1/2,j+1/2}\right]$$

**Layer C — Stress divergence (conservative)**

$$(F_\mu)_x\big|_{i+1/2,j} = \frac{\tau_{xx,i+1,j} - \tau_{xx,i,j}}{\Delta x_{i+1/2}} + \frac{\tau_{xy,i+1/2,j+1/2} - \tau_{xy,i+1/2,j-1/2}}{\Delta y_j}$$

$$(F_\mu)_y\big|_{i,j+1/2} = \frac{\tau_{yx,i+1/2,j+1/2} - \tau_{yx,i-1/2,j+1/2}}{\Delta x_i} + \frac{\tau_{yy,i,j+1} - \tau_{yy,i,j}}{\Delta y_{j+1/2}}$$

**High-order CCD is applied only at Layer A (bulk cells).** Layers B and C are always evaluated with the conservative formulas above.

---

## 4 Complete Discrete Form (Uniform Grid)

Expanding $(F_\mu)_x$ with explicit stencil indices:

$$(F_\mu)_x\big|_{i+1/2,j} = \frac{2\mu_{i+1,j}\dfrac{u_{i+3/2,j}-u_{i+1/2,j}}{\Delta x} - 2\mu_{i,j}\dfrac{u_{i+1/2,j}-u_{i-1/2,j}}{\Delta x}}{\Delta x}$$

$$+ \frac{\mu_{i+1/2,j+1/2}\!\left[\dfrac{u_{i+1/2,j+1}-u_{i+1/2,j}}{\Delta y}+\dfrac{v_{i+1,j+1/2}-v_{i,j+1/2}}{\Delta x}\right] - \mu_{i+1/2,j-1/2}\!\left[\dfrac{u_{i+1/2,j}-u_{i+1/2,j-1}}{\Delta y}+\dfrac{v_{i+1,j-1/2}-v_{i,j-1/2}}{\Delta x}\right]}{\Delta y}$$

This is the reference formula. All higher-order extensions replace the second-order Layer A differences with CCD in the bulk; Layers B and C are unchanged.

---

## 5 Corner Viscosity: τ_xy as a First-Class Citizen

### Placement

$\mu_{i+1/2,j+1/2}$ must be defined at the corner where $\tau_{xy}$ lives:

$$\mu_{i+1/2,j+1/2}^{\rm arith} = \frac14(\mu_{i,j} + \mu_{i+1,j} + \mu_{i,j+1} + \mu_{i+1,j+1})$$

For high viscosity ratio ($\mu_l/\mu_g \gg 1$), harmonic average is safer:

$$\mu_{i+1/2,j+1/2}^{\rm harm} = \left[\frac14\left(\mu_{i,j}^{-1} + \mu_{i+1,j}^{-1} + \mu_{i,j+1}^{-1} + \mu_{i+1,j+1}^{-1}\right)\right]^{-1}$$

### Shared array

$\tau_{xy}$ must be computed **once** and used for both x- and y-momentum equations. Separate computation — even with identical formulas — risks numerical asymmetry and breaks the discrete energy identity.

### Energy identity

With the conservative form and shared $\tau_{xy}$:

$$\langle \mathbf{u}, \mathbf{F}_\mu \rangle_h = -2\sum_{i,j}\mu_{i,j}\left[(\partial_x u)_{i,j}^2 + (\partial_y v)_{i,j}^2\right] - 2\sum_{i,j}\mu_{i+1/2,j+1/2}\left[\partial_y u + \partial_x v\right]_{i+1/2,j+1/2}^2 \;\leq 0$$

Breaking shared $\tau_{xy}$, inconsistent $\mu$ placement, or non-conservative Layer C can make this quantity positive — the viscous term acts as a source of kinetic energy.

---

## 6 CCD Placement: Bulk Layer A Only

### Why interface stencils cannot use CCD

At the interface, $u\in C^0$ (velocity is continuous) but $\nabla u \notin C^0$ (velocity gradient is kinked due to viscosity jump). CCD's O(h^6) accuracy assumes the field is smooth within the stencil support. A CCD stencil spanning the kink amplifies the discontinuity of $\partial_n u$ and produces $O(1)$ oscillations in the gradient estimate.

### Interface band definition

A cell/corner belongs to the interface band if $|\phi| \leq 3h$ (Definition A) or if any stencil point has a different phase indicator (Definition B). In the interface band, all Layer A gradients use 2nd-order central or one-sided differences.

### Operator assignment

| Region | Layer A | Layer B | Layer C |
|--------|---------|---------|---------|
| Bulk (far from interface) | CCD | Conservative formula | Conservative formula |
| Interface band | 2nd-order central or one-sided | Conservative formula | Conservative formula |

A 2nd-order bulk with conservative form outperforms a CCD bulk with inconsistent non-conservative Layer C in terms of interface accuracy.

---

## 7 Defect Correction for Implicit Viscous Helmholtz

### Problem

Crank-Nicolson for the viscous term gives the Helmholtz system:

$$\left(I - \frac{\Delta t}{2\rho}L_H\right)\mathbf{u}^* = \text{RHS}$$

where $L_H = \nabla\cdot(2\mu D_h^{(H)})$ (CCD bulk + 2nd interface band). Direct Krylov solve of this compact operator is expensive because the compact LHS is hard to precondition.

### Defect correction split

Define $A_H = I - (\Delta t/2\rho)L_H$, $A_L = I - (\Delta t/2\rho)L_L$ where $L_L$ uses 2nd-order everywhere.

**Algorithm** (outer index $m$, starting from $\mathbf{u}^{(0)} = \mathbf{u}^n$):

1. $r^{(m)} \leftarrow \text{RHS} - A_H\,\mathbf{u}^{(m)}$  ← high-order residual
2. Solve $A_L\,\delta\mathbf{u} = r^{(m)}$  ← low-order inner solve
3. $\mathbf{u}^{(m+1)} \leftarrow \mathbf{u}^{(m)} + \delta\mathbf{u}$

Outer loop: FGMRES (because inner solve is variable).  
Inner solve of $A_L$: PCG + AMG, ADI, or LU (small domains).

### Requirement on $L_L$

$L_L$ must share the same $\mu$, same BCs, same band-switching as $L_H$. A plain $\mu_0\nabla^2$ fails near the density/viscosity jump. The correct $L_L$ is the 2nd-order conservative form from Phase 1 of the roadmap.

### Connection to ICNAdvance

This maps to the `ICNAdvance` strategy pattern (WIKI-L-016):
- $L_L$ → `PicardCNAdvance` (inner)
- $L_H$ → `ImplicitCNAdvance` (outer residual, Phase 3 roadmap)
- Defect correction wrapper → `DefectCorrectionCNAdvance` (Phase 4 roadmap)

---

## 8 Energy Dissipation and Verification

### Requirement

$\langle \mathbf{u}, \mathbf{F}_\mu \rangle_h \leq 0$ must hold at every timestep. Failure indicates a structural problem.

### Five verification tests

| Test | What to check |
|------|--------------|
| 1. Couette flow | KE decays monotonically |
| 2. Manufactured solution (single-phase) | Spatial convergence order matches CCD in bulk, 2nd at interface band |
| 3. Static droplet ($\mathbf{u}=0$) | $\mathbf{F}_\mu = 0$ to machine precision |
| 4. High-$\mu$-ratio droplet | Energy decays; no energy increase |
| 5. Energy balance diagnostic | $\langle \mathbf{u}^n, \mathbf{F}_\mu^n \rangle_h$ negative at every step |

Test 3 (zero viscous force for zero velocity) is the cheapest diagnostic and should run at startup.

---

## 9 Interaction with BF/PPE Path

The viscous term is **not part of the BF pressure-surface tension balance**. However:

- **$\mu$ placement is independent from $\beta_f = (1/\rho)_f$**: both are face/corner quantities but from separate physical fields. Ensure no shared buffer is accidentally reused.
- **Cross-derivative contamination of BF diagnostic**: near high-$\mu$ interfaces, the cross terms $\partial_x(\mu\partial_y u)$ and $\partial_y(\mu\partial_x v)$ can appear in the BF residual diagnostic if the diagnostic does not correctly project out the viscous contribution. This is a diagnostic artefact, not a BF failure. Use the energy balance test independently.

---

## 10 Anti-Pattern Table

| Anti-pattern | Failure mode |
|--------------|-------------|
| $\mu\nabla^2\mathbf{u}$ for variable $\mu$ | Cross terms dropped; shear stress discontinuous |
| Separate $\tau_{xy}$/$\tau_{yx}$ arrays | Asymmetric stress tensor; discrete energy gain possible |
| CCD at interface-crossing Layer A stencil | Kink amplification; O(1) gradient error |
| Different $\mu$ averaging for x- and y-momentum at same corner | Asymmetric $\tau_{xy}$; fake torque |
| $L_L$ without same $\mu$ field as $L_H$ | Defect correction diverges near interface |
| DCCD on $u$ only (not $v$) at Layer A | Asymmetric $\partial_y u + \partial_x v$; $\tau_{xy}$ energy injection |
| Viscous force diagnostic with raw BF residual | Cross-term contamination; misleading diagnosis |
| Non-conservative Layer C | Energy property lost |

---

## 11 Four-Phase Implementation Roadmap

| Phase | Content | Acceptance gate |
|-------|---------|----------------|
| 1 | Low-order conservative viscous (Layers A/B/C, 2nd order throughout) | Couette, static droplet, manufactured solution 2nd-order |
| 2 | Interface band switching (2nd-order one-sided/central in band) | High-$\mu$-ratio energy test; no regression from Phase 1 |
| 3 | Bulk CCD at Layer A (out-of-band only) | Single-phase manufactured CCD-order convergence; two-phase unchanged |
| 4 | Defect correction for Helmholtz ($L_L$ inner + $L_H$ outer) | Defect correction matches direct $A_H$ solve; Helmholtz convergence faster |

---

## 12 One-Line Summary

> **The conservative stress-divergence form with a shared τ_xy is non-negotiable; CCD is valuable but belongs only at bulk Layer A gradients — never at interface-crossing stencils.**
