---
ref_id: WIKI-X-032
title: "Complete 1-Step Time Integration for CLS + Variable-Density CCD NS: Phase Ordering, Geometry Lag Policy, and Operator Splitting Safety"
domain: cross-domain
status: STABLE
superseded_by: null
sources:
  - description: Internal research memo — advection, CLS, body force, time integration for two-phase CCD/FCCD NS (2026-04-22)
depends_on:
  - "[[WIKI-T-065]]: CLS Complete 1-Step Algorithm"
  - "[[WIKI-T-066]]: Body Force Discretization"
  - "[[WIKI-X-031]]: Advection Design Guide"
  - "[[WIKI-X-025]]: Time Integration Level 1/2/3 for UCCD6-NS"
  - "[[WIKI-X-026]]: Stiffness Policy"
  - "[[WIKI-X-027]]: Reinit Pseudo-Time vs Physical-Time Separation"
  - "[[WIKI-T-041]]: AB3 + Richardson-CN + Rotational IPC"
  - "[[WIKI-X-030]]: Viscous Term Design Guide"
consumers:
  - "[[SP-L]]: Advection, CLS, body force, time integration short paper"
tags: [time_integration, phase_ordering, geometry_lag, operator_splitting, ns_cls_algorithm, two_phase, pseudocode, diagnostics, roadmap]
compiled_by: ResearchArchitect
compiled_at: "2026-04-22"
---

# Complete 1-Step Time Integration for CLS + Variable-Density CCD NS

## §1 Phase Ordering Rationale: Interface-First

### Why CLS before NS?

In a coupled NS+CLS system, the interface geometry ($\mathbf{n}$, $\kappa$, $\rho$, $\mu$) must be evaluated at a consistent time level for all NS force terms. The two possible orderings are:

| Order | Geometry time level | Consistency |
|-------|-------------------|-------------|
| **Interface-first** (CLS then NS) | $n+1$ in NS predictor | Consistent: all forces use updated $\rho^{n+1}$, $\mu^{n+1}$, $\kappa^{n+1}$ |
| NS-first (NS then CLS) | $n$ in NS predictor | Geometry lag: NS uses $\rho^n$, $\mu^n$, $\kappa^n$ throughout |

Interface-first ordering reduces the geometry lag by one time step. For stiff surface tension or high density ratio, using stale $\kappa^n$ in the ST force can destabilize the predictor. Interface-first is the standard choice.

### Geometry lag in practice

Even with interface-first ordering, the **advecting velocity** for the CLS transport (Stage A) uses $\mathbf{u}^n$ (the projected velocity from the previous step), not $\mathbf{u}^{n+1}$ (which is not yet available). This introduces a geometry lag of $O(\Delta t)$ in the interface position, which is unavoidable without sub-cycling or iteration.

For the geometry to be first-order accurate in time: use $\mathbf{u}^n$ for CLS transport and accept $O(\Delta t)$ interface position error. For second-order accuracy, use AB2-extrapolated velocity $\mathbf{u}^{n+1/2} \approx \frac32\mathbf{u}^n - \frac12\mathbf{u}^{n-1}$.

---

## §2 Eight-Phase Algorithm A–H

### Overview

| Phase | Name | Input → Output |
|-------|------|----------------|
| **A** | CLS transport (TVD-RK3) | $\psi^n$, $\mathbf{u}^n$ → $\psi^{(1)}$ |
| **B** | Pre-reinit mass correction | $\psi^{(1)}$ → $\psi^{(2)}$ |
| **C** | Reinit + geometry | $\psi^{(2)}$ → $\phi^{n+1}$, $\psi^{n+1}$, $\mathbf{n}^{n+1}$, $\kappa^{n+1}$ |
| **D** | Material update | $\psi^{n+1}$ → $\rho^{n+1}$, $\mu^{n+1}$, $\beta_f^{n+1}$ |
| **E** | NS predictor | $\mathbf{u}^n$, $p^n$, materials at $n+1$ → $\mathbf{u}^*$ |
| **F** | PPE solve | $\mathbf{u}^*$, $\beta_f^{n+1}$ → $p^{n+1}$ |
| **G** | Velocity corrector | $\mathbf{u}^*$, $p^{n+1}$, $\beta_f^{n+1}$ → $\mathbf{u}^{n+1}$ |
| **H** | Diagnostics | $\mathbf{u}^{n+1}$, $\psi^{n+1}$, $p^{n+1}$ → scalar monitors |

### Phase A — CLS conservative transport

$$\psi^{(1)} = \mathrm{TVD\text{-}RK3}\!\left[\psi^n,\;\mathbf{u}^n,\;\Delta t\right]$$

using WENO5 face reconstruction and divergence-free $\mathbf{u}^n$ (WIKI-T-065 §4).

### Phase B — Pre-reinit mass correction (optional)

$$\alpha = \frac{M_0 - \sum_{i,j}\psi^{(1)}_{i,j}h^2}{\sum_{i,j}\psi^{(1)}_{i,j}(1-\psi^{(1)}_{i,j})h^2}$$
$$\psi^{(2)} = \psi^{(1)} + \alpha\,\psi^{(1)}(1-\psi^{(1)})$$

Omit if $|\alpha| < 10^{-10}$. Include for simulations longer than $O(100)$ steps.

### Phase C — Reinit and geometry extraction

$$\phi^{(0)} = 2\varepsilon\,\mathrm{artanh}(2\psi^{(2)}_\delta - 1) \quad (\psi_\delta = \mathrm{clamp}(\psi^{(2)},\delta,1-\delta))$$

Narrow-band reinit (WIKI-T-065 §7):
$$\frac{\partial\phi}{\partial\tau} + S(\phi^{(0)})(|\nabla\phi|-1) = 0, \quad |\phi^{(0)}| \leq W$$

After $K$ pseudo-steps: $\phi^{n+1}$

Geometry extraction:
$$\mathbf{n}^{n+1} = \frac{\nabla\phi^{n+1}}{|\nabla\phi^{n+1}|}, \qquad \kappa^{n+1} = \nabla\cdot\mathbf{n}^{n+1}$$

Map back: $\psi^{n+1} = \tfrac12(1 + \tanh(\phi^{n+1}/2\varepsilon))$

Post-reinit mass correction (mandatory):
$$\psi^{n+1} \leftarrow \psi^{n+1} + \alpha_F\,\psi^{n+1}(1-\psi^{n+1})$$

### Phase D — Material update

$$\rho^{n+1} = \rho_l\,\psi^{n+1} + \rho_g(1-\psi^{n+1})$$
$$\mu^{n+1} = \mu_l\,\psi^{n+1} + \mu_g(1-\psi^{n+1})$$
$$\beta_f^{n+1} = 1/\rho_f^{n+1} \quad \text{(interpolated at each face)}$$

Face interpolation for $\beta_f$ must be consistent with the interpolation used in Phase F (PPE) and Phase G (corrector) — same averaging scheme (harmonic recommended for high density ratio).

### Phase E — NS predictor

The x-velocity predictor at x-face $(i+\tfrac12, j)$:

$$u^*_{i+1/2,j} = u^n_{i+1/2,j} + \Delta t\!\left[-\mathcal{A}_x^n + \beta_{i+1/2,j}^{n+1}(F_\mu)_x^{n+1/2} + \beta_{i+1/2,j}^{n+1}(f_\sigma)_{x,i+1/2,j}^{n+1} - \beta_{i+1/2,j}^{n+1}(G_h^{\rm explicit}p^n)_{i+1/2,j}\right]$$

where:
- $\mathcal{A}_x^n$: momentum advection at time $n$ (WIKI-X-031 §2)
- $(F_\mu)_x^{n+1/2}$: viscous force (CN: half implicit, half explicit, WIKI-T-064 §8; WIKI-X-030 §5)
- $(f_\sigma)_x^{n+1}$: surface tension at $n+1$ geometry (through BF path, WIKI-X-029 P-1)
- $\beta_f^{n+1}(G_h p^n)$: explicit pressure (using $p^n$ as initial guess)

For gravity (y-component only):
$$v^*_{i,j+1/2} = v^n_{i,j+1/2} + \Delta t\!\left[\cdots - g\right]$$

### Phase F — PPE solve

$$D_h^{bf}\!\left(\beta_f^{n+1}\,G_h^{bf}\,p^{n+1}\right) = \frac{1}{\Delta t}D_h^{bf}\,\mathbf{u}^*$$

Solver: PCG + AMG (when SPD, i.e., no IIM asymmetry), or FGMRES + low-order preconditioner (WIKI-T-063 §3–§4).

### Phase G — Velocity corrector

$$u^{n+1}_{i+1/2,j} = u^*_{i+1/2,j} - \Delta t\,\beta_{i+1/2,j}^{n+1}(G_h^{bf}\,p^{n+1})_{i+1/2,j}$$

**Same $G_h^{bf}$ as PPE** (P-2 from WIKI-X-029). This is the most common BF bug: using a different pressure gradient in the corrector than in the PPE assembly.

### Phase H — Per-step diagnostics

See §6.

---

## §3 Geometry Lag Policy

| Quantity | Time level in predictor (Phase E) | Source |
|----------|----------------------------------|--------|
| $\rho_f$ | $n+1$ | Phase D |
| $\mu_f$ | $n+1$ | Phase D |
| $\kappa$ (for ST) | $n+1$ | Phase C |
| $\mathbf{n}$ (for ST) | $n+1$ | Phase C |
| $\psi$ | $n+1$ | Phase C |
| $p$ (explicit) | $n$ | Previous step's Phase F |
| Momentum advection $\mathcal{A}^n$ | $n$ | Uses $\mathbf{u}^n$ (WIKI-X-031 §3) |
| Viscous (CN half-implicit) | $(n + n^*)/2$ | $n^*$ = corrected; WIKI-T-033 |

**Rule**: all material properties ($\rho$, $\mu$, $\kappa$) are evaluated at $n+1$ (from CLS). All velocity-based terms are evaluated at $n$ or via extrapolation. This separation avoids the geometry-lag stiffness that appears when $\kappa$ lags the corrected velocity.

---

## §4 Operator Splitting Safety

### Non-symmetric splitting

The phase A–H ordering is **non-symmetric** (Lie splitting): each sub-operator is applied once sequentially. For two-phase NS with stiff ST, Lie splitting is $O(\Delta t)$ in the splitting error.

**Strang splitting** (symmetric): apply half-step CLS, full NS, half-step CLS. Achieves $O(\Delta t^2)$ splitting accuracy at doubled CLS cost. Not recommended as default (extra mass correction stages, geometry extraction twice per step), but may be needed for capillary-dominated flows with $We \ll 1$.

### Common splitting dangers

| Danger | Symptom | Fix |
|--------|---------|-----|
| Reinit after NS predictor (not after CLS) | Interface shape inconsistent with $\mathbf{u}^*$; κ error in predictor | Always reinit before NS (Phase C before Phase E) |
| Material update ($\rho^{n+1}$) before CLS completed | $\rho$ inconsistent with $\psi$ | Phase D must follow Phase C completely |
| Gravity at old $\rho^n$ in predictor | Spurious pressure-gravity mismatch (WIKI-T-066 §4) | Use $\rho^{n+1}$ from Phase D |
| PPE $G_h$ ≠ corrector $G_h$ | BF broken (CHK-172) | Unify to same $G_h^{bf}$ |
| $\beta_f$ in PPE ≠ $\beta_f$ in corrector | Variable-density BF broken | Unified $\beta_f$ field from Phase D |

---

## §5 Stiff Term Treatment

| Term | Treatment | Reference |
|------|-----------|-----------|
| Viscous $\nabla\cdot(2\mu\mathbf{D})$ | CN (half-implicit) | WIKI-X-026, WIKI-X-030 §5 |
| Surface tension $f_\sigma$ | Semi-implicit (linear ST) or explicit (with $\Delta t$ restriction) | WIKI-X-025 |
| Gravity | Explicit | WIKI-T-066 §7 |
| Pressure | Projection (implicit) | PPE in Phase F |
| CLS transport | Explicit TVD-RK3 | WIKI-T-065 §4 |
| Reinit | Pseudo-time (separate from $\Delta t$) | WIKI-X-027 |

**Viscous CN requirement**: on non-uniform grids or high-$\mu$ flows, the viscous term must be treated implicitly or the time step becomes impractically small (WIKI-X-026). The CN half-implicit form gives a Helmholtz system solved in Phase E with defect correction (WIKI-X-030 §5).

---

## §6 Phase H Diagnostics

Run these at every step. Flag (not abort) when thresholds are exceeded.

| Diagnostic | Formula | Healthy threshold |
|-----------|---------|------------------|
| Velocity divergence | $\|D_h\mathbf{u}^{n+1}\|_\infty / (1/\Delta t)$ | $< 10^{-10}$ (relative) |
| $\psi$ mass drift | $(M^{n+1} - M^0)/M^0$ | $< 10^{-6}$ per step |
| BF residual | $\|{-G_h^{bf}p_\sigma + f_\sigma}\|_\infty / (|\sigma\kappa|/\rho)$ | $< 10^{-3}$ (for static test) |
| Kinetic energy | $\frac12\sum_{i,j}\rho_{i,j}|\mathbf{u}^{n+1}|^2 h^2$ | Monotone or physical |
| Viscous energy dissipation | $\langle\mathbf{u}^{n+1}, \mathbf{F}_\mu^{n+1}\rangle_h$ | $\leq 0$ always |
| $\kappa$ noise | $\|\kappa^{n+1}\|_\infty$ vs expected $1/R$ | $< 10\%$ deviation for circular drop |

The viscous dissipation check ($\leq 0$) is the cheapest structural correctness test and should run at every step after Phase E (WIKI-X-030 §6).

---

## §7 Three-Stage Implementation Roadmap (V1/V2/V3)

### V1 — Proof of concept (2nd order throughout)

| Component | Scheme |
|-----------|--------|
| CLS transport (Stage A) | WENO5 + TVD-RK3 |
| Momentum advection | 2nd-order upwind |
| Viscous term | Low-order conservative (Phase 1, WIKI-X-030 §8) |
| PPE | Low-order face-flux $G_2$, $D_2$ |
| BF | GFM jump correction (Phase 1, WIKI-X-029 §7.1) |
| ST | CSF body force, 2nd-order |
| Time integration | Lie splitting, explicit Euler |

**Acceptance gates**: V1 reproduces Couette flow, static droplet spurious current at $O(h)$, bubble rise trajectory.

### V2 — Production accuracy

| Component | Upgrade from V1 |
|-----------|----------------|
| Momentum advection | CCD bulk + WENO5 interface band (WIKI-X-031 §4) |
| Viscous term | Interface band switching; defect correction Helmholtz (Phases 2–4, WIKI-X-030 §8) |
| PPE | FCCD $G_h^{bf}$, adjoint $D_h^{bf}$; defect correction (WIKI-T-063 §4) |
| BF | Full 7-principle FCCD path (WIKI-X-029 §2) |
| Time integration | CN viscous; AB2 advection |

**Acceptance gates**: V2 achieves $O(h^2)$–$O(h^3)$ spurious current; 4th-order spatial convergence on smooth manufactured solution.

### V3 — Research accuracy

| Component | Upgrade from V2 |
|-----------|----------------|
| Viscous bulk | CCD Layer A (Phase 3, WIKI-X-030 §8) |
| PPE | IIM row correction for FCCD interface-crossing rows (WIKI-T-063 §5.2) |
| BF | High-order $\kappa$ via HFE; capillary-jump PPE (Phase 3, WIKI-X-029 §7.2) |
| Time integration | AB3 + Richardson-CN; rotational IPC (WIKI-T-041) |
| CLS transport | Potentially higher-order RK or IMEX |

**Acceptance gates**: V3 achieves CCD-order spatial convergence in bulk; $O(h^3)$–$O(h^4)$ spurious current.

---

## §8 Pseudocode

```
for each time step n → n+1:

  # ─── INTERFACE (Phases A–D) ────────────────────────────────────────
  # Phase A: CLS transport
  psi_1 = TVD_RK3(psi_n, u_n, dt, weno5_face_flux)

  # Phase B: pre-reinit mass correction (optional)
  alpha_B = (M0 - sum(psi_1) * h^2) / sum(psi_1*(1-psi_1) * h^2)
  if |alpha_B| > 1e-10:
    psi_2 = psi_1 + alpha_B * psi_1*(1-psi_1)
  else:
    psi_2 = psi_1

  # Phase C: reinit + geometry
  phi_0   = 2*eps * arctanh(2*clamp(psi_2, 1e-14, 1-1e-14) - 1)
  phi_np1 = narrow_band_reinit(phi_0, eps, W=5*eps, K_steps)
  n_np1   = grad(phi_np1) / |grad(phi_np1)|
  kappa_np1 = div(n_np1)
  psi_np1 = 0.5*(1 + tanh(phi_np1 / (2*eps)))
  alpha_F = (M0 - sum(psi_np1)*h^2) / sum(psi_np1*(1-psi_np1)*h^2)
  psi_np1 = psi_np1 + alpha_F * psi_np1*(1-psi_np1)

  # Phase D: material update
  rho_np1 = rho_l*psi_np1 + rho_g*(1-psi_np1)
  mu_np1  = mu_l *psi_np1 + mu_g *(1-psi_np1)
  rho_f   = face_interp(rho_np1, 'harmonic')   # at each velocity face
  beta_f  = 1.0 / rho_f                         # for PPE and corrector

  # ─── NS PREDICTOR (Phase E) ─────────────────────────────────────────
  A_adv   = conservative_momentum_flux(u_n, rho_np1)   # WIKI-X-031 §2
  F_visc  = cn_viscous_predictor(u_n, mu_np1)           # WIKI-X-030 §5
  F_sigma = bf_surface_tension(n_np1, kappa_np1, beta_f) # WIKI-X-029 P-1
  G_p_exp = bf_gradient(p_n)                             # explicit pressure

  u_star = u_n + dt*(-A_adv + beta_f*(F_visc + F_sigma - G_p_exp))
  u_star[y] -= dt * g   # gravity (y-component, uniform acceleration)

  # ─── PROJECTION (Phases F–G) ─────────────────────────────────────────
  # Phase F: PPE
  rhs_ppe = (1/dt) * div_bf(u_star)
  p_np1   = ppe_solve(beta_f, rhs_ppe)   # D_h(beta_f G_h p) = rhs

  # Phase G: velocity corrector
  u_np1 = u_star - dt * beta_f * bf_gradient(p_np1)  # same G_h^bf as PPE

  # ─── DIAGNOSTICS (Phase H) ──────────────────────────────────────────
  check_divergence(u_np1)             # < 1e-10 (relative)
  check_mass_drift(psi_np1, M0)       # < 1e-6 per step
  check_bf_residual(p_np1, F_sigma)   # < 1e-3 (static)
  check_viscous_dissipation(u_np1, F_visc)  # <= 0
```
