---
ref_id: WIKI-T-064
title: "∇·(2μD) Staggered MAC Discretization: Layer Architecture, Shear Stress Corner Placement, and Conservative Discrete Forms"
domain: theory
status: STABLE
superseded_by: null
sources:
  - description: Internal research memo — viscous term discretization for two-phase CCD/FCCD NS (2026-04-22)
  - description: "Harlow, F. H. & Welch, J. E. (1965). Numerical calculation of time-dependent viscous incompressible flow of fluid with a free surface. Physics of Fluids 8(12), 2182–2189. (MAC staggered grid)"
  - description: "Tryggvason, G. et al. (2011). A Front-Tracking Method for the Computations of Multiphase Flow. Academic Press. (Chapter 7: variable viscosity stress)"
depends_on:
  - "[[WIKI-T-003]]: Variable-Density Projection Method: CN viscous cross-derivative trap"
  - "[[WIKI-T-046]]: FCCD: Face-Centered CCD"
  - "[[WIKI-X-023]]: UCCD6 NS Design: flux-form viscous mention"
consumers:
  - "[[WIKI-X-030]]: Viscous Term Design Guide: CCD/interface-band split, defect correction"
  - "[[WIKI-T-033]]: Extended CN × CCD: sequential D₂ for Helmholtz solve"
  - "[[WIKI-T-041]]: Third-order time integration: AB3 cross-term extrapolation"
  - "[[SP-K]]: Viscous Term short paper"
tags: [viscous, stress_divergence, staggered_mac, corner_viscosity, tau_xy, variable_viscosity, two_phase, conservative_form, layer_architecture]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# ∇·(2μD) Staggered MAC Discretization

## §1 Motivation: Why `μ∇²u` is Insufficient

For an incompressible Newtonian fluid the viscous body force is

$$\mathbf{F}_\mu = \nabla\cdot\boldsymbol{\tau}, \qquad \boldsymbol{\tau} = 2\mu\mathbf{D}(\mathbf{u}), \qquad \mathbf{D} = \tfrac12(\nabla\mathbf{u} + \nabla\mathbf{u}^T)$$

When $\mu$ is uniform this simplifies because $\nabla\cdot(2\mu\mathbf{D}) = \mu\nabla^2\mathbf{u}$ (using $\nabla\cdot\mathbf{u}=0$). **In two-phase flow $\mu$ jumps at the interface, so this identity fails.** The full stress-divergence form must be used.

Consequences of using $\mu\nabla^2\mathbf{u}$ incorrectly near the interface:
- Shear stress continuity $[\mu\partial_n u_t]_\Gamma = 0$ is not enforced discretely
- The cross-derivative terms $\partial_x(\mu\partial_y u)$, $\partial_y(\mu\partial_x v)$ are dropped
- Spurious tangential forces appear at the interface
- High viscosity-ratio flows become unstable

---

## §2 2D Staggered MAC Variable Placement

| Quantity | Location | Grid index |
|----------|----------|------------|
| $p$, $\mu$, $\rho$ | Cell center | $(i,j)$ |
| $u$ (x-velocity) | x-face | $(i+\tfrac12, j)$ |
| $v$ (y-velocity) | y-face | $(i, j+\tfrac12)$ |
| $\tau_{xx}$, $\tau_{yy}$ | Cell center | $(i,j)$ |
| $\tau_{xy} = \tau_{yx}$ | Corner | $(i+\tfrac12, j+\tfrac12)$ |

The viscous force components live at the same location as the velocity they accelerate:
- $(F_\mu)_x$ at x-face $(i+\tfrac12, j)$
- $(F_\mu)_y$ at y-face $(i, j+\tfrac12)$

---

## §3 Strain Rate and Stress Tensor in 2D

$$\mathbf{D} = \begin{pmatrix} \partial_x u & \tfrac12(\partial_y u + \partial_x v) \\ \tfrac12(\partial_y u + \partial_x v) & \partial_y v \end{pmatrix}$$

Stress components:

$$\tau_{xx} = 2\mu\,\partial_x u, \qquad \tau_{yy} = 2\mu\,\partial_y v, \qquad \tau_{xy} = \tau_{yx} = \mu(\partial_y u + \partial_x v)$$

Viscous force:

$$(F_\mu)_x = \partial_x\tau_{xx} + \partial_y\tau_{xy}, \qquad (F_\mu)_y = \partial_x\tau_{yx} + \partial_y\tau_{yy}$$

---

## §4 Layer Architecture

The discretisation is structured in three layers. This separation is the key design principle — high-order CCD is applied only at Layer A; Layers B and C preserve the conservative structure.

```
Layer A: Velocity gradient generation
  ┌──────────────────────────────────────────────────────┐
  │ (∂_x u)_c  at cell center (i,j)  — from u at x-faces│
  │ (∂_y v)_c  at cell center (i,j)  — from v at y-faces│
  │ (∂_y u)_⊕  at corner (i+½,j+½) — from u at x-faces │
  │ (∂_x v)_⊕  at corner (i+½,j+½) — from v at y-faces │
  └──────────────────────────────────────────────────────┘
          ↓
Layer B: Stress tensor assembly
  ┌──────────────────────────────────────────────────────┐
  │ τ_xx = 2 μ_c (∂_x u)_c    at cell center (i,j)      │
  │ τ_yy = 2 μ_c (∂_y v)_c    at cell center (i,j)      │
  │ τ_xy = μ_⊕ [(∂_y u)_⊕ + (∂_x v)_⊕]  at corner       │
  │        ← τ_xy = τ_yx: ONE array shared by both eqs  │
  └──────────────────────────────────────────────────────┘
          ↓
Layer C: Stress divergence (conservative finite difference)
  ┌──────────────────────────────────────────────────────┐
  │ (F_μ)_x at x-face: [τ_xx(i+1,j) - τ_xx(i,j)]/Δx    │
  │                   + [τ_xy(i+½,j+½) - τ_xy(i+½,j-½)]/Δy│
  │ (F_μ)_y at y-face: [τ_yx(i+½,j+½) - τ_yx(i-½,j+½)]/Δx│
  │                   + [τ_yy(i,j+1) - τ_yy(i,j)]/Δy    │
  └──────────────────────────────────────────────────────┘
```

**High-order CCD enters only at Layer A** (velocity gradients). Layers B and C are always evaluated with their natural conservative formula.

---

## §5 Layer A: Velocity Gradient Generation

### Cell-center gradients (for τ_xx, τ_yy)

At cell center $(i,j)$, the velocity gradients use face values already available from the staggered layout:

$$(\partial_x u)_{i,j} = \frac{u_{i+1/2,j} - u_{i-1/2,j}}{\Delta x_i}, \qquad (\partial_y v)_{i,j} = \frac{v_{i,j+1/2} - v_{i,j-1/2}}{\Delta y_j}$$

These can be raised to higher order by replacing finite differences with CCD-based derivatives in the **bulk** (away from the interface).

### Corner gradients (for τ_xy)

At corner $(i+\tfrac12, j+\tfrac12)$:

$$(\partial_y u)_{i+1/2,j+1/2} = \frac{u_{i+1/2,j+1} - u_{i+1/2,j}}{\Delta y_{j+1/2}}, \qquad (\partial_x v)_{i+1/2,j+1/2} = \frac{v_{i+1,j+1/2} - v_{i,j+1/2}}{\Delta x_{i+1/2}}$$

CCD can be applied here in the bulk, but the corner stencil more readily crosses the interface, requiring earlier fallback to low-order (see WIKI-X-030 §2).

---

## §6 Layer B: Stress Tensor Assembly

### Normal stresses (cell center)

$$\tau_{xx}\big|_{i,j} = 2\mu_{i,j}\,(\partial_x u)_{i,j}, \qquad \tau_{yy}\big|_{i,j} = 2\mu_{i,j}\,(\partial_y v)_{i,j}$$

The cell-center viscosity $\mu_{i,j}$ is the natural choice here.

### Shear stress (corner) — τ_xy = τ_yx

$$\tau_{xy}\big|_{i+1/2,j+1/2} = \mu_{i+1/2,j+1/2}\left[(\partial_y u)_{i+1/2,j+1/2} + (\partial_x v)_{i+1/2,j+1/2}\right]$$

**Critical design rule**: $\tau_{xy}$ and $\tau_{yx}$ must be the **same array**. Implementing them separately (e.g., with different viscosity interpolations) breaks the symmetry of the stress tensor, destroys energy dissipation properties, and introduces artificial torques at the interface.

---

## §7 Corner Viscosity $\mu_{i+1/2,j+1/2}$

The shear stress lives at the corner; $\mu$ must be interpolated there.

### Arithmetic average (standard)

$$\mu_{i+1/2,j+1/2}^{\rm arith} = \frac14\left(\mu_{i,j} + \mu_{i+1,j} + \mu_{i,j+1} + \mu_{i+1,j+1}\right)$$

Adequate for moderate viscosity ratios. Simple to implement.

### Harmonic average (high-ratio flows)

$$\mu_{i+1/2,j+1/2}^{\rm harm} = \left[\frac14\left(\mu_{i,j}^{-1} + \mu_{i+1,j}^{-1} + \mu_{i,j+1}^{-1} + \mu_{i+1,j+1}^{-1}\right)\right]^{-1}$$

More appropriate when $\mu_l/\mu_g \gg 1$ (e.g., water/air $\approx 55$). Prevents the high-viscosity phase from contaminating the corner when only one cell is in the liquid phase.

### Design principle

Whatever averaging is chosen, **it must be applied consistently** across all corners. Different averaging for $\tau_{xy}$ in the $x$-momentum equation vs the $y$-momentum equation (which uses the same corner) causes an asymmetric stress tensor and breaks energy conservation.

---

## §8 Layer C: Complete Discrete Forms

### x-momentum viscous force at x-face $(i+\tfrac12, j)$

$$\boxed{(F_\mu)_x\big|_{i+1/2,j} = \frac{\tau_{xx,i+1,j} - \tau_{xx,i,j}}{\Delta x_{i+1/2}} + \frac{\tau_{xy,i+1/2,j+1/2} - \tau_{xy,i+1/2,j-1/2}}{\Delta y_j}}$$

Expanding with the explicit stencil (uniform grid):

$$= \frac{2\mu_{i+1,j}\dfrac{u_{i+3/2,j}-u_{i+1/2,j}}{\Delta x} - 2\mu_{i,j}\dfrac{u_{i+1/2,j}-u_{i-1/2,j}}{\Delta x}}{\Delta x}$$
$$+ \frac{\mu_{i+1/2,j+1/2}\!\left[\dfrac{u_{i+1/2,j+1}-u_{i+1/2,j}}{\Delta y}+\dfrac{v_{i+1,j+1/2}-v_{i,j+1/2}}{\Delta x}\right] - \mu_{i+1/2,j-1/2}\!\left[\dfrac{u_{i+1/2,j}-u_{i+1/2,j-1}}{\Delta y}+\dfrac{v_{i+1,j-1/2}-v_{i,j-1/2}}{\Delta x}\right]}{\Delta y}$$

### y-momentum viscous force at y-face $(i, j+\tfrac12)$

$$\boxed{(F_\mu)_y\big|_{i,j+1/2} = \frac{\tau_{yx,i+1/2,j+1/2} - \tau_{yx,i-1/2,j+1/2}}{\Delta x_i} + \frac{\tau_{yy,i,j+1} - \tau_{yy,i,j}}{\Delta y_{j+1/2}}}$$

where $\tau_{yx,i+1/2,j+1/2} = \tau_{xy,i+1/2,j+1/2}$ (same array), and

$$\tau_{yy,i,j} = 2\mu_{i,j}\,\frac{v_{i,j+1/2} - v_{i,j-1/2}}{\Delta y_j}$$

---

## §9 Energy Dissipation Property

For a conservative stress-divergence form, the discrete power dissipated by the viscous term satisfies

$$\langle \mathbf{u}, \mathbf{F}_\mu \rangle_h = -\sum_{i,j} \left[\tau_{xx,i,j}\,(\partial_x u)_{i,j} + \tau_{yy,i,j}\,(\partial_y v)_{i,j}\right] - 2\sum_{i,j} \tau_{xy,i+1/2,j+1/2}\,(\partial_y u + \partial_x v)_{i+1/2,j+1/2}$$

$$= -2\sum_{i,j}\mu_{i,j}\left[(\partial_x u)_{i,j}^2 + (\partial_y v)_{i,j}^2\right] - 2\sum_{i,j}\mu_{i+1/2,j+1/2}\left[(\partial_y u + \partial_x v)_{i+1/2,j+1/2}\right]^2 \;\leq\; 0$$

(using summation-by-parts, periodic or Dirichlet BCs, and $\mu \geq 0$).

This means the conservative form with a **shared $\tau_{xy}$** and **consistent $\mu$ placement** is guaranteed to be dissipative at the discrete level. Breaking any of these (separate $\tau_{xy}/\tau_{yx}$, inconsistent $\mu$, non-conservative Layer C) can cause the viscous term to act as a source of kinetic energy.

---

## §10 Non-Uniform Grid Extension

On a non-uniform grid with $\Delta x_i$ varying, the formula generalises:

**Layer A** (cell-center gradients):

$$(\partial_x u)_{i,j} = \frac{u_{i+1/2,j} - u_{i-1/2,j}}{\Delta x_i}$$

**Layer C** (divergence of normal stress):

$$\frac{\tau_{xx,i+1,j} - \tau_{xx,i,j}}{\Delta x_{i+1/2}}, \qquad \Delta x_{i+1/2} = \tfrac12(\Delta x_i + \Delta x_{i+1})$$

**Layer C** (divergence of shear stress):

$$\frac{\tau_{xy,i+1/2,j+1/2} - \tau_{xy,i+1/2,j-1/2}}{\Delta y_j}$$

The CCD upgrades at Layer A follow the non-uniform CCD theory (WIKI-T-011, WIKI-T-012). Layers B and C are unchanged in structure; only the metric spacings differ.

**Corner gradients** on non-uniform grids:

$$(\partial_y u)_{i+1/2,j+1/2} = \frac{u_{i+1/2,j+1} - u_{i+1/2,j}}{\Delta y_{j+1/2}}, \qquad \Delta y_{j+1/2} = \tfrac12(\Delta y_j + \Delta y_{j+1})$$

---

## §11 Summary

| Layer | Content | High-order CCD? |
|-------|---------|-----------------|
| A: Velocity gradients | $(\partial_x u)_c$, $(\partial_y v)_c$, $(\partial_y u)_\oplus$, $(\partial_x v)_\oplus$ | **Yes — bulk only** |
| B: Stress assembly | $\tau_{xx}$, $\tau_{yy}$ at center; $\tau_{xy}=\tau_{yx}$ at corner | No (algebraic) |
| C: Stress divergence | Face-centred finite difference of stress fluxes | No (2nd order conservative) |

The conservative property and energy dissipation come from Layer C. Accuracy comes from Layer A.
