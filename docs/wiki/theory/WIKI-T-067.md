---
ref_id: WIKI-T-067
title: "GFM Variable-Density Projection: Mandatory 1/ρ Factor in Velocity Correction"
domain: theory
status: ACTIVE
superseded_by: null
sources:
  - path: src/twophase/simulation/velocity_reprojector.py
    description: "VariableDensityReprojector.reproject — fixed implementation"
consumers:
  - domain: X
    usage: "ch13 capillary blowup root cause (Fix 1)"
depends_on:
  - "[[WIKI-T-003]]: Variable-Density Projection Method: IPC + AB2 + CN"
  - "[[WIKI-T-034]]: Consistent IIM Reprojection"
tags: [projection, variable-density, gfm, velocity-correction, reprojector]
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-23
---

# GFM Variable-Density Projection: Mandatory 1/ρ Factor in Velocity Correction

## §1 The PPE solved in GFM mode

The GFM fractional-step projection solves the variable-coefficient Poisson equation:

$$\nabla \cdot \left[\frac{1}{\rho} \nabla \phi\right] = \frac{\nabla \cdot \mathbf{u}^*}{\Delta t}$$

where $\phi$ is the pressure correction (or pseudo-pressure for velocity reprojection).

## §2 Correct velocity corrector

The divergence-free velocity is:

$$\mathbf{u}^{n+1} = \mathbf{u}^* - \frac{\Delta t}{\rho} \nabla \phi$$

**The $1/\rho$ factor is mandatory.** It comes directly from the definition of the PPE operator: since the operator is $\nabla \cdot [(1/\rho) \nabla]$, inverting it gives a correction $(1/\rho)\nabla\phi$, not $\nabla\phi$.

## §3 Consequence of omitting 1/ρ

Without the $1/\rho$ factor:

$$\mathbf{u}^{n+1}_{\text{wrong}} = \mathbf{u}^* - \Delta t\, \nabla \phi$$

For water ($\rho = 1000$), this **over-corrects by a factor of 1000** — a single step inflates the water velocity by $\sim 10^3$, causing immediate KE blowup (observed: KE $\sim 10^{-8}$ → $>10^6$ in 3 steps).

For gas ($\rho = 1.2$), the correction is 833× too small — the gas stays nearly divergence-full.

## §4 Implementation note

In `VariableDensityReprojector.reproject` (`velocity_reprojector.py`):

```python
rho_inv = 1.0 / xp.where(xp.abs(rho) > 1e-30, rho, 1.0)
dp_dx, _ = ccd.differentiate(phi, 0)
dp_dy, _ = ccd.differentiate(phi, 1)
u_proj = u_d - rho_inv * xp.asarray(dp_dx)
v_proj = v_d - rho_inv * xp.asarray(dp_dy)
```

The guard `xp.where(|ρ| > 1e-30, ρ, 1.0)` prevents division by zero at mixed cells where the smeared density field may reach near-zero values.

## §5 Scope

This applies to **all** fractional-step projections that solve a variable-density PPE — both the main NS projection and the post-grid-rebuild velocity reprojection in `VariableDensityReprojector`. The CCD-uniform-grid path (`LegacyReprojector`) solves a constant-coefficient Laplacian, so no $1/\rho$ factor is needed there.
