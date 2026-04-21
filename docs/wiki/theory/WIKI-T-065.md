---
ref_id: WIKI-T-065
title: "CLS Complete 1-Step Algorithm: Conservative Transport, ψ↔φ Mapping, Narrow-Band Reinit, and Staged Mass Correction"
domain: theory
status: STABLE
superseded_by: null
sources:
  - description: Internal research memo — advection, CLS, body force, time integration for two-phase CCD/FCCD NS (2026-04-22)
  - description: "Olsson, E. & Kreiss, G. (2005). A conservative level set method for two phase flow. JCP 210(1), 225–246."
  - description: "Olsson, E., Kreiss, G. & Zahedi, S. (2007). A conservative level set method for two phase flow II. JCP 225(1), 785–807."
  - description: "Shu, C.-W. & Osher, S. (1988). Efficient implementation of essentially non-oscillatory shock-capturing schemes. JCP 77(2), 439–471. (TVD-RK3 coefficients)"
depends_on:
  - "[[WIKI-T-007]]: Conservative Level Set: ψ transport and mass properties"
  - "[[WIKI-T-027]]: Mass correction: ψ(1-ψ) interface-local scheme"
  - "[[WIKI-T-028]]: Reinit pseudo-time PDE for φ"
  - "[[WIKI-T-030]]: Level set geometry: n, κ from φ"
  - "[[WIKI-T-036]]: phi-primary transport path"
  - "[[WIKI-T-013]]: WENO5 vs DCCD: scheme selection benchmarks"
consumers:
  - "[[WIKI-X-031]]: Advection Design Guide"
  - "[[WIKI-X-032]]: Complete 8-Phase NS+CLS Algorithm"
  - "[[SP-L]]: Advection, CLS, body force, time integration short paper"
tags: [cls, conservative_level_set, transport, taa_rk3, weno, mass_correction, reinit, psi_phi_mapping, narrow_band, epsilon_management]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# CLS Complete 1-Step Algorithm

## §1 Three-Responsibility Principle

The Conservative Level Set (CLS) method splits interface representation into three independent responsibilities:

| Responsibility | Field | Method |
|----------------|-------|--------|
| **Mass conservation** | $\psi \in [0,1]$ | Conservative flux divergence transport |
| **Interface geometry** (normal, curvature) | $\phi$ (signed distance) | Reinit from $\psi$ then standard gradient/divergence |
| **Mass correction** | correction to $\psi$ | Interface-local $\psi(1-\psi)$ adjustment |

Each responsibility is handled by a dedicated stage. Conflating them — e.g., using $\phi$ for transport, or applying mass correction to geometry — is the primary source of CLS implementation bugs.

**Design rule**: $\psi$ conserves mass; $\phi$ provides geometry. Never transport $\phi$ directly with a non-conservative advection operator.

---

## §2 ψ↔φ Mapping

The two fields are related by the hyperbolic tangent profile:

$$\phi = 2\varepsilon\,\mathrm{artanh}(2\psi - 1), \qquad \psi = \tfrac12\!\left(1 + \tanh\!\left(\frac{\phi}{2\varepsilon}\right)\right)$$

where $\varepsilon > 0$ is the interface half-width parameter.

### Numerical clamp

The artanh mapping is singular at $\psi = 0$ and $\psi = 1$. In practice, clamp $\psi$ before mapping:

$$\psi_\delta = \max(\delta,\, \min(1-\delta,\, \psi)), \qquad \delta = 10^{-14} \text{ (double precision)}$$

then $\phi = 2\varepsilon\,\mathrm{artanh}(2\psi_\delta - 1)$.

### Interface location

The interface $\Gamma$ is defined by $\psi = \tfrac12$ (equivalently $\phi = 0$). The narrow band for reinit and geometry is $|\phi| \leq W$ with $W \approx 4$–$6\,\varepsilon$ (typically $W = 5\varepsilon$).

---

## §3 Six-Stage Algorithm A→F

One complete CLS step per flow time step $[t^n, t^{n+1}]$ with $\Delta t = t^{n+1} - t^n$:

| Stage | Name | Input | Output |
|-------|------|-------|--------|
| **A** | Conservative transport | $\psi^n$, $\mathbf{u}^n$ (divergence-free) | $\psi^{(1)}$ |
| **B** | Pre-reinit mass correction | $\psi^{(1)}$ | $\psi^{(2)}$ |
| **C** | ψ→φ mapping | $\psi^{(2)}$ | $\phi^{(2)}$ |
| **D** | Narrow-band reinit | $\phi^{(2)}$ | $\phi^{n+1}$ |
| **E** | φ→ψ mapping + geometry | $\phi^{n+1}$ | $\psi^{n+1}$, $\mathbf{n}^{n+1}$, $\kappa^{n+1}$ |
| **F** | Post-reinit mass correction | $\psi^{n+1}$ | $\psi^{n+1}$ (corrected) |

Stage B is optional (omit if mass error is small before reinit). Stage F is mandatory after reinit because pseudo-time PDE is not mass-conservative.

---

## §4 Stage A — Conservative Transport (TVD-RK3)

### Governing equation

$$\frac{\partial\psi}{\partial t} + \nabla\cdot(\psi\mathbf{u}) = 0$$

Using $\nabla\cdot\mathbf{u} = 0$ this is equivalent to the non-conservative form $\partial_t\psi + \mathbf{u}\cdot\nabla\psi = 0$, but the conservative form is preferred because it ensures mass conservation at the discrete level when a flux-conserving scheme is used.

### TVD-RK3 (Shu-Osher)

Three sub-stages with coefficients:

| Stage | Formula |
|-------|---------|
| 1 | $\psi^{(1)} = \psi^n + \Delta t\,\mathcal{L}(\psi^n,\mathbf{u}^n)$ |
| 2 | $\psi^{(2)} = \tfrac{3}{4}\psi^n + \tfrac{1}{4}\left[\psi^{(1)} + \Delta t\,\mathcal{L}(\psi^{(1)},\mathbf{u}^n)\right]$ |
| 3 | $\psi^{n+1} = \tfrac{1}{3}\psi^n + \tfrac{2}{3}\left[\psi^{(2)} + \Delta t\,\mathcal{L}(\psi^{(2)},\mathbf{u}^n)\right]$ |

where $\mathcal{L}(\psi,\mathbf{u}) = -[(\psi u)_{i+1/2,j} - (\psi u)_{i-1/2,j}]/\Delta x - [(\psi v)_{i,j+1/2} - (\psi v)_{i,j-1/2}]/\Delta y$.

### Face flux reconstruction

At face $(i+\tfrac12,j)$ with face velocity $u_{i+1/2,j}$ (from PPE projection):

$$(\psi u)_{i+1/2,j} = u_{i+1/2,j}\,\psi^{\rm upwind}_{i+1/2,j}$$

$\psi^{\rm upwind}$ is reconstructed from the **upwind** side using:

| Region | Scheme |
|--------|--------|
| Bulk ($|\phi| > W_{\rm WENO}$, smooth) | **WENO5** (mandatory for $\psi$) |
| Interface band ($|\phi| \leq W_{\rm WENO}$) | **WENO5** or monotone MUSCL-Minmod |

**Rule**: CCD must **not** be used for $\psi$ face reconstruction. CCD presupposes $C^\infty$ fields; $\psi$ has a steep but continuous profile near the interface that CCD over-differentiates and destabilizes.

### Divergence-free velocity requirement

The face velocities $u_{i+1/2,j}$, $v_{i,j+1/2}$ used in the face fluxes must satisfy $D_h \mathbf{u} = 0$ (from the PPE projection). Using a predicted velocity $\mathbf{u}^*$ that has not been projected introduces a divergence error that propagates into $\psi$ transport and generates spurious mass changes.

---

## §5 Bounded Reconstruction and Clipping

### Monotone MUSCL-Minmod

For cells flagged as interface band ($|\phi| \leq W_{\rm MUSCL}$, typically $2\varepsilon$–$3\varepsilon$):

$$\psi^+_{i+1/2} = \psi_i + \tfrac12 \mathrm{minmod}(\psi_i - \psi_{i-1},\, \psi_{i+1} - \psi_i)$$

The minmod limiter $\mathrm{minmod}(a,b) = \tfrac12(\mathrm{sgn}(a)+\mathrm{sgn}(b))\min(|a|,|b|)$ suppresses oscillations near steep gradients.

### Clipping rule

After each RK sub-stage:

$$\psi^{(k)} \leftarrow \max(0,\,\min(1,\,\psi^{(k)}))$$

**Clipping is a last resort.** If clipping triggers frequently (more than $O(N^2)$ cells per step), the root cause is typically: insufficient upwind weighting, CCD used for $\psi$, or non-divergence-free face velocities.

---

## §6 Stages B and F — Mass Correction

### ψ(1-ψ) interface-local correction

After any stage that perturbs $\psi$ without conserving mass (primarily Stage D, the reinit), apply:

$$\psi \leftarrow \psi + \alpha\,\psi(1-\psi)$$

where $\alpha$ is determined from the global mass balance:

$$\alpha = \frac{M_{\rm target} - \sum_{i,j}\psi_{i,j}\,h^2}{\sum_{i,j}\psi_{i,j}(1-\psi_{i,j})\,h^2}$$

$M_{\rm target}$ is the reference mass (e.g., set at $t=0$ and updated only when physical mass change occurs).

### Properties

- Localised: $\psi(1-\psi)$ is nonzero only near the interface; bulk values (near 0 or 1) are not perturbed
- Bounded: for small $|\alpha|$, the corrected $\psi \in [0,1]$ is preserved
- Idempotent if iterated: one iteration is sufficient when $|\alpha| \ll 1$

### Stage B vs Stage F

- **Stage B** (pre-reinit, optional): corrects mass drift accumulated during transport; useful for long simulations
- **Stage F** (post-reinit, mandatory): corrects mass change caused by the non-conservative reinit PDE

---

## §7 Stage D — Narrow-Band Reinit

### Reinit PDE

The reinit equation in pseudo-time $\tau$:

$$\frac{\partial\phi}{\partial\tau} + S(\phi_0)\left(|\nabla\phi| - 1\right) = 0, \qquad \phi(\cdot,0) = \phi_0$$

where $S(\phi_0) = \phi_0 / \sqrt{\phi_0^2 + \varepsilon^2}$ is the smoothed sign function.

**Separation of pseudo-time from physical time** (WIKI-X-027): reinit runs in $\tau$ with step $\delta\tau \approx 0.3 h_{\rm min}$; it must not be confused with the physical $\Delta t$.

### Narrow-band restriction

Apply reinit only where $|\phi_0| \leq W = 5\varepsilon$ (typically $\approx 5$–$7$ cells). Outside the band, $\phi$ is held fixed. This:
- Prevents the reinit from altering the interface location
- Reduces cost from $O(N^2)$ to $O(N)$ per step
- Avoids contamination of the smooth bulk $\psi$ values

### Stopping criterion

Run for $K$ pseudo-time steps where $K$ satisfies $K\,\delta\tau \approx W/2$. Alternatively, stop when $\|\,|\nabla\phi| - 1\,\|_{L^\infty} < \text{tol}$ (e.g., $10^{-4}$).

### FMM/Eikonal alternative

For high-accuracy signed distance without pseudo-time iterations:
- Fast Marching Method (FMM) solves $|\nabla\phi| = 1$ with Godunov upwind scheme
- Exact to first order away from $\Gamma$; higher-order variants available
- More expensive per step but avoids iteration count choice; useful when reinit must be run infrequently (every $M$ steps)

---

## §8 ε Management and Reinit Frequency

### ε selection

| Grid type | Recommended ε |
|-----------|---------------|
| Uniform, mesh size $h$ | $\varepsilon = 1.5\,h$ or $\varepsilon = 2h$ |
| Non-uniform, minimum spacing $h_{\rm min}$ | $\varepsilon = 1.5\,h_{\rm min}$ |
| Adaptive mesh | $\varepsilon$ must track local $h$; requires careful implementation |

**Rule**: $\varepsilon$ must be fixed for a given grid; changing it during a run perturbs the interface profile and alters the discrete BF balance (since $\kappa$ depends on $\phi$).

### Reinit frequency

| Strategy | When to use |
|----------|-------------|
| Every step | Safest; recommended for production |
| Every $M$ steps | Acceptable for $M \leq 5$; mass correction Stage F is more important than frequency |
| Conditional (when $\||\nabla\phi|-1\|>$ tol) | Research only; not recommended for production |

Over-reinitialising (large $K$ pseudo-steps every physical step) wastes cost but is not incorrect as long as $\phi$ is not altered outside the narrow band.

---

## §9 Failure Modes

| Anti-pattern | Failure mode |
|--------------|-------------|
| CCD for $\psi$ face reconstruction | Over-differentiation of steep profile; nonlinear instability |
| Non-conservative advection $\mathbf{u}\cdot\nabla\psi$ for $\psi$ | Mass not conserved at discrete level; drift accumulates |
| Non-divergence-free $\mathbf{u}$ in Stage A | Spurious mass generation/destruction; BF coupling error |
| Reinit applied outside narrow band | Interface drift; mass change incompatible with Stage F correction |
| Using $\phi$ for advection (instead of $\psi$) | $\phi$ transport not conservative; mass loss |
| ε changed mid-simulation | Profile shape change; $\kappa$ discontinuity; BF disruption |
| Stage F omitted after reinit | Mass drift accumulates each step |
| Clipping used as primary conservation mechanism | Hides transport scheme instability; masks mass error |
| Reinit pseudo-time confused with physical $\Delta t$ | Wrong step size; either non-convergence or |slow evolution |
| Different ε in φ→ψ and reinit PDE | Profile inconsistency; ghost interface layers |
