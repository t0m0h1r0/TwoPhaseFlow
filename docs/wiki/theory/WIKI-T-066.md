---
ref_id: WIKI-T-066
title: "Body Force Discretization in Variable-Density Two-Phase NS: f vs f/ρ, Gravity Face Placement, Hydrostatic Split, and BF Consistency"
domain: theory
status: STABLE
superseded_by: null
sources:
  - description: Internal research memo — body force and time integration design for two-phase CCD/FCCD NS (2026-04-22)
  - description: "Prosperetti, A. & Tryggvason, G. (2007). Computational Methods for Multiphase Flow. Cambridge UP. (Chapter 3: volume-averaged body forces)"
  - description: "Dodd, M. S. & Ferrante, A. (2014). A fast pressure-correction method for incompressible two-fluid flows. JCP 273, 416–434. (density-weighted corrector)"
depends_on:
  - "[[WIKI-T-003]]: Variable-Density Projection: CN cross-derivative and BF trap"
  - "[[WIKI-T-004]]: Balanced-Force (BF) condition for surface tension"
  - "[[WIKI-X-024]]: UCCD6-NS balanced-force design"
  - "[[WIKI-X-029]]: BF Operator Consistency Guide"
  - "[[WIKI-T-064]]: ∇·(2μD) Staggered MAC Discretization"
consumers:
  - "[[WIKI-X-032]]: Complete 8-Phase NS+CLS Algorithm"
  - "[[SP-L]]: Advection, CLS, body force, time integration short paper"
tags: [body_force, gravity, hydrostatic_split, f_over_rho, balanced_force, staggered_mac, variable_density, two_phase, face_placement]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# Body Force Discretization in Variable-Density Two-Phase NS

## §1 f vs f/ρ: Body Force Density vs Acceleration

The momentum equation is

$$\rho\frac{D\mathbf{u}}{Dt} = -\nabla p + \nabla\cdot(2\mu\mathbf{D}) + \mathbf{f}$$

where $\mathbf{f}$ is a **body force density** $[\mathrm{N/m^3}]$. After dividing by $\rho$:

$$\frac{D\mathbf{u}}{Dt} = -\frac{1}{\rho}\nabla p + \frac{1}{\rho}\nabla\cdot(2\mu\mathbf{D}) + \frac{\mathbf{f}}{\rho}$$

The **acceleration** from the body force is $\mathbf{a} = \mathbf{f}/\rho$.

### Gravity: f = ρg vs a = g

| Form | Expression | Units | Variable density? |
|------|-----------|-------|-------------------|
| Body force density | $\mathbf{f}_g = \rho\mathbf{g}$ | N/m³ | Must use local $\rho$ at each face |
| Acceleration | $\mathbf{a}_g = \mathbf{g}$ | m/s² | Uniform — but this is the acceleration, not the force |

In the velocity predictor, the term entering as:

$$u^* = u^n + \Delta t\left(-\beta_f(G_h p)_f + \frac{(f_g)_f}{\rho_f} + \cdots\right)$$

The correct form uses $\mathbf{f}_g / \rho = \rho\mathbf{g}/\rho = \mathbf{g}$, but this is only valid at the **same face** and with the **same** $\rho_f$ that appears in the density-weighting $\beta_f = 1/\rho_f$.

**Key requirement**: the $\rho_f$ used to form $\mathbf{f}_g/\rho_f = \mathbf{g}$ must be identical to the $\rho_f$ in $\beta_f$. If $\beta_f$ uses harmonic averaging but gravity uses arithmetic averaging of $\rho$, a spurious force appears in the absence of motion — identical to the BF inconsistency for surface tension.

---

## §2 Gravity on Staggered MAC: Face Placement

### Standard placement

Gravity $\mathbf{g} = (0,-g)$ in 2D. The gravitational acceleration enters the predictor at velocity faces:

| Component | Face | Gravity contribution |
|-----------|------|---------------------|
| $u^*_{i+1/2,j}$ | x-face | $(f_g)_x / \rho_f = \rho_f \cdot 0 / \rho_f = 0$ |
| $v^*_{i,j+1/2}$ | y-face | $(f_g)_y / \rho_f = \rho_{i,j+1/2} \cdot (-g) / \rho_{i,j+1/2} = -g$ |

For the y-component:

$$v^*_{i,j+1/2} = v^n_{i,j+1/2} + \Delta t\left(-\beta_{i,j+1/2}(G_h p)_{i,j+1/2} - g + (\text{viscous}) + (\text{ST})\right)$$

where $\beta_{i,j+1/2} = 1/\rho_{i,j+1/2}$ and $\rho_{i,j+1/2}$ is interpolated from the cell-center values.

### ρ interpolation at y-face

$$\rho_{i,j+1/2} = \frac12(\rho_{i,j} + \rho_{i,j+1}) \quad \text{(arithmetic, standard)}$$

or harmonic for high density ratios:

$$\rho_{i,j+1/2} = \frac{2\rho_{i,j}\rho_{i,j+1}}{\rho_{i,j} + \rho_{i,j+1}}$$

**Rule**: whichever interpolation is used for $\rho_{i,j+1/2}$ must be used **identically** in $\beta_f = 1/\rho_f$. Mixing harmonic for gravity and arithmetic for $\beta_f$ generates a face-wise body force error proportional to the density jump.

---

## §3 Hydrostatic Split p = p_hyd + p'

### Motivation

In stratified flows (and bubbles/droplets in gravity), the pressure field has a large hydrostatic component:

$$\frac{\partial p_{\rm hyd}}{\partial z} = -\rho g \quad \Rightarrow \quad p_{\rm hyd}(z) = p_{\rm ref} + \int_z^{z_{\rm top}} \rho(z') g\,dz'$$

The dynamic pressure $p' = p - p_{\rm hyd}$ is much smaller and varies on shorter length scales.

### PPE for dynamic pressure

Substituting $p = p_{\rm hyd} + p'$ into the variable-density PPE:

$$D_h^{bf}\!\left(\beta_f G_h^{bf} p'\right) = \frac{1}{\Delta t} D_h^{bf} u^* - D_h^{bf}\!\left(\beta_f G_h^{bf} p_{\rm hyd}\right)$$

Since $G_h^{bf} p_{\rm hyd} \approx \rho_f \mathbf{g}$ (continuous identity; discrete error $O(h^2)$), the RHS is dominated by $D_h^{bf} u^* / \Delta t$ and the subtracted term is small.

### When to use the hydrostatic split

| Scenario | Recommendation |
|----------|---------------|
| Light bubble in heavy liquid (large $\rho$ jump) | **Yes** — reduces condition number of PPE |
| Flat-interface stratification (quiescent) | **Yes** — $p' \approx 0$; easy convergence |
| Droplet in microgravity ($g \approx 0$) | Unnecessary; $p_{\rm hyd} = 0$ |
| Weakly stratified flow | Optional; small benefit |

**Initialization**: set $p'(t=0) = 0$ and $p_{\rm hyd}$ from the initial density profile. Then only $p'$ is solved during the simulation.

---

## §4 BF Consistency of Gravity: Weakly BF-Critical

Gravity is **weakly BF-critical**: unlike surface tension (strongly BF-critical), gravity does not require exact cancellation for stability, but incorrect $\rho_f$ placement still generates spurious motion at a flat quiescent interface.

### Static flat interface test

For a flat interface with $\rho_l$ below, $\rho_g$ above, $\mathbf{u} = \mathbf{0}$, the hydrostatic equilibrium requires:

$$-\beta_f (G_h^{bf} p)_f + g_y = 0 \quad \text{at every y-face}$$

This holds **if and only if** the $\rho_f$ in $\beta_f$ and the $\rho_f$ in $p_{\rm hyd}$ discretisation are identical.

### Magnitude comparison

Typical spurious velocity from gravity BF inconsistency:

$$u_{\rm spurious} \sim \Delta t \cdot g \cdot \delta\beta_f$$

where $\delta\beta_f$ is the $\rho$ interpolation mismatch at the face. For $\rho_l/\rho_g = 1000$ (water/air), $g = 9.81$, and arithmetic vs harmonic mismatch $\delta\beta_f \sim O(\Delta\rho/\rho^2 \cdot h)$, this is non-negligible for large $\Delta t$.

---

## §5 Surface Tension vs Gravity: BF Path vs Standard Body Force

| Force | Strongly BF-critical? | Must go through $G_h^{bf}$ path? |
|-------|-----------------------|----------------------------------|
| Surface tension $\mathbf{f}_\sigma$ | **Yes** | **Yes** — P-1..P-4 from WIKI-X-029 |
| Gravity $\rho\mathbf{g}$ | Weakly | No — but $\rho_f$ must match $\beta_f$ |
| External body force (uniform) | No | No |

**Surface tension rule (WIKI-X-029, P-1)**: $f_\sigma$ must be evaluated at the same face where $G_h^{bf} p$ is applied. Using $f_\sigma$ at nodes then interpolating breaks the discrete BF balance.

**Gravity rule (this entry)**: gravity enters as a uniform acceleration $-g$ in the y-predictor, not through the $G_h^{bf}$ path. However, the $\rho_f$ used to define $\beta_f$ must match the one used to construct $p_{\rm hyd}$ (for the hydrostatic split) or the face $\rho$ interpolation (for direct body force).

---

## §6 Non-Uniform Grid: ρ Face Interpolation

On a non-uniform grid with cell sizes $\Delta y_j$ varying:

$$\rho_{i,j+1/2} = \frac{\Delta y_{j+1}\,\rho_{i,j} + \Delta y_j\,\rho_{i,j+1}}{\Delta y_j + \Delta y_{j+1}} \quad \text{(linear, area-weighted)}$$

This reduces to arithmetic average on uniform grids. For the hydrostatic pressure gradient:

$$(\partial_y p_{\rm hyd})_{i,j+1/2} \approx \frac{p_{\rm hyd,i,j+1} - p_{\rm hyd,i,j}}{\Delta y_{j+1/2}}, \qquad \Delta y_{j+1/2} = \tfrac12(\Delta y_j + \Delta y_{j+1})$$

The BF test for non-uniform grids: $-\beta_f (G_h p_{\rm hyd})_f + g_y = 0$ must hold at every y-face when $\mathbf{u} = \mathbf{0}$ and $p = p_{\rm hyd}$.

---

## §7 Time Integration: Gravity Time Level

### Predictor: which time level for ρ?

For the velocity predictor at time level $n+1$:

$$\mathbf{u}^* = \mathbf{u}^n + \Delta t\!\left[-\frac{1}{\rho^{n+1}}\nabla p^n + \mathbf{g} + \frac{1}{\rho^{n+1}}\nabla\cdot(2\mu^{n+1}\mathbf{D}^{n}) + \cdots\right]$$

- **Use $\rho^{n+1}$** (material updated from CLS at start of step) for $\beta_f$ and gravity normalization
- **Use $p^n$** as the explicit pressure estimate; PPE then solves for $p^{n+1}$
- **Use $\mathbf{g}$** at the current time (gravity is constant; no time-level issue)

### Hydrostatic split and pressure initialization

If using the hydrostatic split:
- Reinitialize $p_{\rm hyd}$ at every step from $\rho^{n+1}$ (since the interface moves)
- $p'^{n+1}$ is the PPE solution
- The velocity corrector applies $\beta_f G_h^{bf} p'^{n+1}$ only (not the hydrostatic part, which has already been accounted for in the predictor RHS)

### Summary

| Quantity | Time level in predictor |
|----------|------------------------|
| $\rho_f$, $\beta_f = 1/\rho_f$ | $n+1$ (from CLS update) |
| $\mu_f$ | $n+1$ (from CLS update) |
| $\kappa$ (curvature for ST) | $n+1$ (from CLS geometry) |
| $p$ (explicit pressure) | $n$ |
| $\mathbf{g}$ | constant (no time level) |
| $p_{\rm hyd}$ | $n+1$ (recomputed from $\rho^{n+1}$) |
