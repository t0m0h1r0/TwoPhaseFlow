---
ref_id: WIKI-X-031
title: "Advection Design Guide for CCD/FCCD Two-Phase NS: Conservative Flux Form, Velocity-PPE Consistency, and Scheme Selection per Variable"
domain: cross-domain
status: STABLE
superseded_by: null
sources:
  - description: Internal research memo — advection, CLS, body force, time integration for two-phase CCD/FCCD NS (2026-04-22)
depends_on:
  - "[[WIKI-T-065]]: CLS Complete 1-Step Algorithm"
  - "[[WIKI-X-028]]: Conservative Momentum Form for Variable-Density Two-Phase NS"
  - "[[WIKI-X-029]]: BF Operator Consistency Guide"
  - "[[WIKI-X-030]]: Viscous Term Design Guide"
  - "[[WIKI-T-013]]: WENO5 vs DCCD: Scheme Selection Benchmarks"
  - "[[WIKI-T-055]]: FCCD Conservative Flux-Divergence Advection"
consumers:
  - "[[WIKI-X-032]]: Complete 8-Phase NS+CLS Algorithm"
  - "[[SP-L]]: Advection, CLS, body force, time integration short paper"
tags: [advection, conservative_form, momentum_flux, velocity_pppe_consistency, scheme_selection, weno, ccd, cfl, dccd, two_phase, design_guide]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# Advection Design Guide for CCD/FCCD Two-Phase NS

## §1 Conservative vs Non-Conservative Form: Why (u·∇)u Fails

### The two momentum advection forms

| Form | Expression | Property |
|------|-----------|----------|
| Non-conservative | $(\mathbf{u}\cdot\nabla)\mathbf{u}$ | Equivalent to conservative only when $\nabla\cdot\mathbf{u}=0$ exactly |
| Conservative (flux divergence) | $\nabla\cdot(\mathbf{u}\otimes\mathbf{u})$ | Conserves discrete momentum; form-invariant under phase mixing |

For single-phase incompressible flow with exact $\nabla\cdot\mathbf{u}=0$, the two forms are analytically equivalent. In two-phase discretizations, they differ for three reasons:

1. **Discrete divergence is not exactly zero**: the PPE solve reduces $\|D_h \mathbf{u}\|$ but does not zero it to machine precision. Non-conservative form has $O(\|D_h\mathbf{u}\|)$ spurious acceleration; conservative form does not.

2. **Density-weighted momentum**: the actual conserved quantity is $\rho\mathbf{u}$, not $\mathbf{u}$. The flux form $\nabla\cdot(\rho\mathbf{u}\otimes\mathbf{u})$ explicitly transports the mass-weighted momentum; the non-conservative form $\rho(\mathbf{u}\cdot\nabla)\mathbf{u}$ drops the density-weighted flux correction at phase boundaries.

3. **BF coupling**: the conservative form maintains consistency with the PPE flux divergence $D_h \mathbf{u}^*$; see §3.

### Conservative flux form (WIKI-X-028)

The x-momentum advection term:

$$\mathcal{A}_x\big|_{i+1/2,j} = \frac{(\rho u^2)_{i+1,j} - (\rho u^2)_{i,j}}{\Delta x} + \frac{(\rho uv)_{i+1/2,j+1/2} - (\rho uv)_{i+1/2,j-1/2}}{\Delta y}$$

where fluxes are evaluated at natural MAC locations:
- $(\rho u^2)$ at cell center (the $\rho u$ flux in x-direction)
- $(\rho uv)$ at corner $(i+\tfrac12, j+\tfrac12)$

---

## §2 MAC Flux Form: Explicit Stencil

### x-momentum at x-face $(i+\tfrac12, j)$

The face velocity $u_{i+1/2,j}$ is at the natural x-face location. The fluxes use reconstructed face values:

$$\mathcal{A}_x = \frac{F^x_{i+1,j} - F^x_{i,j}}{\Delta x} + \frac{F^y_{i+1/2,j+1/2} - F^y_{i+1/2,j-1/2}}{\Delta y}$$

where:
- $F^x_{i,j} = \rho_{i,j}\, u_{i+1/2,j}^{\rm up}\, u_{i,j}^{\rm interp}$ (cell-center flux): reconstruct $u$ from surrounding faces
- $F^y_{i+1/2,j+1/2} = \rho_{i+1/2,j+1/2}\, v_{i+1/2,j+1/2}^{\rm interp}\, u_{i+1/2,j+1/2}^{\rm interp}$ (corner flux)

The density $\rho$ must be at the same location as the flux, interpolated from cell-center values with the same scheme used for $\beta_f$ (see WIKI-T-066 §2).

### y-momentum at y-face $(i, j+\tfrac12)$

Symmetric: replace $u \leftrightarrow v$ and $x \leftrightarrow y$ indices.

---

## §3 Velocity-PPE Consistency: Divergence-Free Advecting Field

The advecting velocity in $\nabla\cdot(\mathbf{u}\otimes\mathbf{u})$ must be the **post-projection** divergence-free field. Using the predicted velocity $\mathbf{u}^*$ (before PPE) for advection in the next time step introduces a consistency error.

### Correct cycle (Phase ordering)

In an explicit (or semi-implicit with explicit advection) scheme:

1. Advance CLS to get $\rho^{n+1}$, $\mu^{n+1}$
2. Compute momentum advection $\mathcal{A}^n$ using $\mathbf{u}^n$ (the projected velocity from step $n$)
3. Form predictor $\mathbf{u}^*$
4. Solve PPE for $p^{n+1}$ using $D_h \mathbf{u}^*$
5. Correct: $\mathbf{u}^{n+1} = \mathbf{u}^* - \Delta t\,\beta_f^{n+1} G_h p^{n+1}$
6. Use $\mathbf{u}^{n+1}$ for CLS transport at step $n+1$

**Rule**: both momentum advection ($\mathcal{A}^n$) and CLS transport (Stage A) use the same $\mathbf{u}^n$ — the fully projected velocity from the end of the previous step. Never use $\mathbf{u}^*$ for these operations.

---

## §4 Scheme Selection per Variable

| Variable | Field character | Recommended scheme | Rationale |
|----------|----------------|-------------------|-----------|
| $\psi$ (CLS) | $C^0$ steep profile | **WENO5** everywhere | Monotone near interface; CCD invalid |
| $u, v$ (momentum, bulk) | $C^\infty$ smooth bulk | **CCD** (bulk) + WENO/upwind (band) | High-order smooth; low-order at interface band |
| $u, v$ (momentum, interface band) | $C^0$ (velocity continuous) | **WENO5** or 2nd upwind | Interface-crossing CCD produces oscillations |
| $\phi$ (reinit PDE) | signed distance | **WENO-HJ** (Hamilton-Jacobi) | Eikonal equation; standard HJ-WENO appropriate |
| $p$ (pressure) | smooth bulk, jump at $\Gamma$ | Face-flux (FCCD) + GFM/IIM jump | BF path; not CCD |
| $\mu$, $\rho$ | jump at $\Gamma$ | Low-order conservative, no CCD | Jump fields; CCD amplifies discontinuity |

### CCD in the interface band: forbidden for ψ, mandatory-limited for u/v

| Variable | Interface band rule |
|----------|---------------------|
| $\psi$ | WENO5 throughout (never CCD) |
| $u, v$ | Fallback to 2nd-order one-sided or WENO5; band detection same as viscous Layer A (WIKI-X-030 §2) |
| $\phi$ (transport for geometry only) | HJ-WENO; narrow-band only |

---

## §5 CCD for Advection: When Safe, When Unsafe

### Safe: smooth bulk momentum

For $u$ or $v$ in cells where $|\phi| > 3h$, CCD provides 6th-order velocity gradients:

$$(\partial_x u)_{i+1/2,j}^{\rm CCD} = \text{compact 6th-order from FCCD} \quad (|\phi| > 3h)$$

Low dispersion error reduces phase error in the momentum transport, especially for rotating or shear flows.

### Unsafe: ψ field, interface-crossing, near-discontinuity

1. **ψ field**: hyperbolic tangent profile has large second derivatives near interface. CCD's implicit solver amplifies these in the compact system → nonlinear instability or negative $\psi$ values.

2. **Interface-crossing stencil**: CCD stencil support spans multiple cells. If the stencil crosses the interface where $\nabla u$ is kinked, the compact solve treats the kink as high-frequency smooth content → oscillation.

3. **Near-discontinuity ρ, μ**: never apply CCD to jump fields.

**Practical rule**: CCD is safe for advection only for smooth fields ($C^\infty$ within the stencil support). Use the same interface band detection as in WIKI-X-030 §2.

---

## §6 CFL on Non-Uniform Grids

### Standard CFL condition

$$\Delta t \leq C_{\rm CFL}\,\frac{h_{\rm min}}{u_{\rm max}}$$

where $h_{\rm min}$ is the **minimum** cell size in the domain and $u_{\rm max}$ is the maximum velocity magnitude. For typical explicit advection, $C_{\rm CFL} = 0.5$ (WENO5) or $C_{\rm CFL} = 0.3$ (CCD with compact stencil).

### Non-uniform grid: h_min at interface

On an interface-fitted or refined grid, cells near the interface may be significantly smaller than bulk cells. The CFL condition is then **dominated by the interface-region cells**, even though the interface-band uses low-order (cheaper) schemes. This is unavoidable: CFL is a stability constraint, not an accuracy constraint.

**Implication**: adaptive time-stepping keyed to interface cell size is essential for non-uniform grids with interface refinement.

### Viscous CFL (if explicit viscous)

$$\Delta t \leq C_\nu\,\frac{h_{\rm min}^2}{\nu_{\rm max}}$$

Stiffness policy (WIKI-X-026): viscous term must be implicit when this constraint is active (e.g., on non-uniform grids or high-viscosity flows). Never use explicit viscous on non-uniform grids with $h_{\rm min} \ll h_{\rm bulk}$.

---

## §7 DCCD Safety Rules for Advection

| Application | Safe? |
|-------------|-------|
| DCCD on $u, v$ in bulk (away from interface, symmetric) | Conditionally yes — adds dissipation |
| DCCD on $\psi$ transport stencil | **No** — asymmetric with interface |
| DCCD filter on momentum flux $F_x$ only (not $F_y$) | **No** — breaks momentum conservation symmetry |
| DCCD on both $u$ and $v$ uniformly | Conditionally yes — preserves energy balance |
| Different DCCD on x- and y-momentum | **No** — anisotropic artificial dissipation |

Rule: DCCD for advection is a numerical stabilizer, not a physical model. If applied, it must be applied symmetrically and should not affect the BF path.

---

## §8 Role Separation: Four Independent Sub-Systems

| Sub-system | Operator | Scheme |
|-----------|----------|--------|
| **CLS transport** ($\psi$) | Flux divergence, TVD-RK3 | WENO5 face flux |
| **Momentum advection** ($\mathbf{u}$) | Flux divergence | CCD (bulk) + WENO/upwind (band) |
| **Viscous term** | Conservative Layer A/B/C | CCD (bulk) + 2nd (band) |
| **Pressure-BF sub-system** | Face-flux PPE + corrector | FCCD or 2nd face-flux |

Each sub-system has its own operator and accuracy requirements. Blending operators across sub-systems — e.g., using the BF face-flux gradient for momentum advection, or using the viscous CCD stencil for $\psi$ transport — is never correct.

**Why this matters**: the BF sub-system's internal consistency is more important than its order. If FCCD face-flux is used for PPE but CCD node-gradient is used for the momentum corrector, BF fails regardless of the individual operator orders (P-2 in WIKI-X-029).

---

## §9 Anti-Patterns

| Anti-pattern | Failure mode |
|--------------|-------------|
| CCD for $\psi$ transport | Over-differentiates steep tanh profile; instability |
| Non-conservative $(u\cdot\nabla)u$ for momentum | Discrete divergence error accumulates as spurious acceleration |
| Advecting velocity = $\mathbf{u}^*$ (predicted, not projected) | Divergence error in advecting field → mass and momentum error |
| Same WENO stencil for $\psi$ and $p$ near interface | Pressure uses jump correction (GFM/IIM); ψ does not |
| CFL keyed to bulk $h$, not $h_{\rm min}$ | Instability in interface-refined cells |
| Explicit viscous on non-uniform grid (stiff) | Time-step dominated by viscous CFL; impractical |
| DCCD applied to $\psi$ face flux | Asymmetric near interface; mass conservation violated |
| Different density interpolation for advection $\rho$ and $\beta_f$ | Gravity BF inconsistency (WIKI-T-066 §4) |
| BF face-flux gradient used for momentum advection | Conflates BF consistency with accuracy; incompatible stencils |
