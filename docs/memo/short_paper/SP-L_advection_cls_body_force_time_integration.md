# SP-L: Advection, CLS, Body Force, and Time Integration Design for CCD/FCCD Two-Phase NS

**Compiled**: 2026-04-22  
**Status**: STABLE (research memo)  
**Wiki entries**: WIKI-T-065 (CLS algorithm), WIKI-T-066 (body force), WIKI-X-031 (advection guide), WIKI-X-032 (complete algorithm)  
**Depends on**: SP-J (BF/CCD design), SP-K (viscous term), WIKI-X-025/026/027/028 (existing NS/CLS design)

---

## Abstract

Four inter-related design areas for CCD/FCCD two-phase NS are synthesised: (1) conservative momentum advection requires flux-divergence form $\nabla\cdot(\mathbf{u}\otimes\mathbf{u})$, not $(\mathbf{u}\cdot\nabla)\mathbf{u}$, because residual discrete divergence generates spurious acceleration with the non-conservative form; (2) scheme selection is variable-specific — WENO5 for $\psi$ (CLS, mandatory), CCD for smooth bulk $u/v$ (with interface-band fallback to WENO), face-flux for pressure (BF path); (3) Conservative Level Set (CLS) has six stages (A→F) with TVD-RK3 transport, narrowband reinit, and $\psi(1-\psi)$ mass correction — CCD must never be used for $\psi$ face reconstruction; (4) body force discretization requires consistent $\rho_f$ placement — the same face density used in $\beta_f = 1/\rho_f$ must be used for gravity normalization; (5) a complete 8-phase (A–H) time integration algorithm, interface-first, achieves $O(\Delta t)$ geometry lag with predictable ordering; (6) the hydrostatic split $p = p_{\rm hyd} + p'$ reduces PPE conditioning for buoyant flows. The primary conclusion is that **the dominant source of errors in two-phase NS is operator inconsistency across sub-systems, not insufficient differentiation order**.

---

## 1 Conservative Momentum Flux Form

### Why (u·∇)u is wrong for two-phase discretization

The continuous forms $\nabla\cdot(\mathbf{u}\otimes\mathbf{u})$ and $(\mathbf{u}\cdot\nabla)\mathbf{u} + \mathbf{u}(\nabla\cdot\mathbf{u})$ are identical when $\nabla\cdot\mathbf{u}=0$ exactly. In discrete two-phase NS, $\nabla\cdot\mathbf{u}$ is not exactly zero — the PPE solve reduces it to $O(\text{tol})$ but not machine zero. The non-conservative form has a spurious term $\mathbf{u}(D_h\mathbf{u}) \neq 0$, which acts as a momentum source proportional to the divergence residual. For high-velocity or long-time simulations, this accumulates into observable error.

The conservative form:
$$\mathcal{A}_x\big|_{i+1/2,j} = \frac{F^x_{i+1,j} - F^x_{i,j}}{\Delta x} + \frac{F^y_{i+1/2,j+1/2} - F^y_{i+1/2,j-1/2}}{\Delta y}$$

is form-invariant and does not produce spurious momentum from residual divergence.

### Density-weighted momentum

The physically conserved quantity is $\rho\mathbf{u}$, not $\mathbf{u}$. Near the interface, where $\rho$ varies sharply, the flux $\rho\mathbf{u}\otimes\mathbf{u}$ must be reconstructed with consistent $\rho$ interpolation. The $\rho_f$ used in the momentum flux must match the $\rho_f$ used in $\beta_f$ for the PPE corrector (same interpolation scheme, same time level $n+1$).

---

## 2 Velocity-PPE Consistency for Advection

Both the CLS transport (Stage A, WIKI-T-065) and the momentum advection (Phase E predictor) use the **post-projection** velocity $\mathbf{u}^n$ from the end of the previous step. Using the unprojected $\mathbf{u}^*$ from the current step introduces:

- Divergence error in the advecting velocity field for CLS → spurious $\psi$ mass changes
- Inconsistency between the advection and the PPE RHS divergence

The correct ordering is:
$$\text{PPE at step } n \Rightarrow \mathbf{u}^n \Rightarrow \text{CLS transport and momentum advection} \Rightarrow \mathbf{u}^*_{n+1} \Rightarrow \text{PPE at step } n+1$$

---

## 3 Scheme Selection per Variable

The critical design choice is matching the differentiation scheme to the field character:

| Variable | Character | Scheme |
|----------|-----------|--------|
| $\psi$ | $C^0$ steep tanh profile | WENO5 (mandatory, everywhere) |
| $u, v$ bulk | $C^\infty$ smooth | CCD 6th order |
| $u, v$ interface band | $C^0$ (kink in $\nabla u$) | WENO5 or 2nd upwind |
| $\phi$ reinit PDE | Eikonal | WENO-HJ |
| $p$ | jump at $\Gamma$ | Face-flux + GFM/IIM correction |
| $\rho$, $\mu$ | step-function profile | Low-order, no CCD |

The dominant design error is applying CCD universally:
- CCD for $\psi$: amplifies steep tanh curvature → nonlinear instability
- CCD for $p$ without jump correction: smears pressure jump → spurious currents
- CCD for $\mu, \rho$: amplifies discontinuity → oscillations

---

## 4 CFL on Non-Uniform Grids

On interface-refined or adaptive grids, the CFL constraint is:

$$\Delta t \leq C_{\rm CFL}\,\frac{h_{\rm min}}{u_{\rm max}}, \qquad h_{\rm min} = \min_{\rm cells} h$$

where $h_{\rm min}$ is controlled by the smallest cells, typically near the interface. This can be 5–10× smaller than the bulk cell size. The viscous constraint:

$$\Delta t \leq C_\nu\,\frac{h_{\rm min}^2}{\nu_{\rm max}}$$

is the reason viscous terms must be implicit on non-uniform grids: the $h^2$ dependence makes this constraint far more severe than advective CFL, requiring $\Delta t = O(h^2)$ for stability with explicit viscous.

---

## 5 CLS Three-Responsibility Principle and ψ↔φ Mapping

### Three-responsibility principle

| Responsibility | Field | Mechanism |
|----------------|-------|-----------|
| Mass conservation | $\psi \in [0,1]$ | Conservative flux transport |
| Geometry (normal, curvature) | $\phi$ (signed distance) | Reinit then gradient/divergence |
| Mass correction | correction to $\psi$ | $\psi(1-\psi)$ interface-local |

These are independent operations. Conflating them — transporting $\phi$ with a non-conservative scheme, using $\psi$ for curvature without reinit, applying mass correction to $\phi$ — is the primary CLS implementation failure mode.

### ψ↔φ mapping

The tanh/artanh pair:

$$\phi = 2\varepsilon\,\mathrm{artanh}(2\psi - 1), \qquad \psi = \tfrac12\!\left(1 + \tanh\!\frac{\phi}{2\varepsilon}\right)$$

Clamp $\psi$ to $[\delta, 1-\delta]$ before artanh to avoid singularity. The parameter $\varepsilon$ must be fixed throughout a simulation (changing it alters $\kappa$).

---

## 6 CLS Six-Stage Algorithm (A→F)

Stage sequence for one physical time step:

| Stage | Operation | Key requirement |
|-------|-----------|----------------|
| A | TVD-RK3 conservative transport | WENO5 face flux; divergence-free $\mathbf{u}^n$ |
| B | Pre-reinit $\psi(1-\psi)$ correction | Optional; useful for long simulations |
| C | $\psi \to \phi$ mapping | Clamp $\psi$ before artanh |
| D | Narrow-band reinit | $|\phi| \leq W = 5\varepsilon$; pseudo-$\tau$ separate from $\Delta t$ |
| E | $\phi \to \psi$ + geometry ($\mathbf{n}$, $\kappa$) | Clamp $\phi/2\varepsilon$ before tanh |
| F | Post-reinit $\psi(1-\psi)$ correction | Mandatory after reinit |

**TVD-RK3 Shu-Osher coefficients**:

$$\psi^{(1)} = \psi^n + \Delta t\,\mathcal{L}^n$$
$$\psi^{(2)} = \tfrac34\psi^n + \tfrac14(\psi^{(1)} + \Delta t\,\mathcal{L}^{(1)})$$
$$\psi^{n+1} = \tfrac13\psi^n + \tfrac23(\psi^{(2)} + \Delta t\,\mathcal{L}^{(2)})$$

---

## 7 Mass Correction: ψ(1-ψ), Interface-Local

The correction formula $\psi \leftarrow \psi + \alpha\psi(1-\psi)$ with $\alpha$ from global mass balance:

$$\alpha = \frac{M_{\rm target} - \int\psi\,dV}{\int\psi(1-\psi)\,dV}$$

has three key properties:
1. **Interface-local**: $\psi(1-\psi) = 0$ exactly where $\psi = 0$ or $\psi = 1$; bulk values are never perturbed
2. **Mass-conservative**: $\int(\psi + \alpha\psi(1-\psi))\,dV = M_{\rm target}$ by construction
3. **Bounded for small $|\alpha|$**: $\psi \in [0,1]$ preserved when $|\alpha| \leq 4$

This correction is applied twice: once optionally before reinit (Stage B), once mandatorily after reinit (Stage F), because the reinit pseudo-time PDE is not mass-conservative.

---

## 8 f vs f/ρ: Body Force Density and Acceleration

The momentum equation conserves $\rho\mathbf{u}$; the body force density $\mathbf{f}$ has units N/m³. After dividing by $\rho$, the acceleration is $\mathbf{a} = \mathbf{f}/\rho$.

For gravity: $\mathbf{f}_g = \rho\mathbf{g}$, so $\mathbf{a}_g = \mathbf{f}_g/\rho = \mathbf{g}$ (uniform acceleration). The predictor uses $-g$ directly in the y-equation.

**Critical requirement**: the $\rho_f$ used to form $\mathbf{a}_g = \mathbf{f}_g/\rho_f$ and the $\rho_f$ in $\beta_f = 1/\rho_f$ (PPE and corrector) must be identical — same interpolation scheme (arithmetic or harmonic), same time level ($n+1$). Inconsistent $\rho_f$ between gravity normalization and $\beta_f$ generates a spurious body force at the interface proportional to $\Delta\rho$.

---

## 9 Gravity Face Placement on Staggered MAC

Gravity enters the y-velocity predictor as a constant $-g$ per unit mass. The x-predictor has no gravity for horizontal-gravity cases. For the y-face $(i, j+\tfrac12)$:

$$v^* = v^n + \Delta t\!\left[-\beta_f(G_h p)_{j+1/2} - g + \beta_f(F_\mu)_y + \beta_f(f_\sigma)_y\right]$$

The density-weighting $\beta_f = 1/\rho_{i,j+1/2}$ is the inverse of the face density interpolated from $\rho^{n+1}$. For the static hydrostatic test ($\mathbf{u} = \mathbf{0}$, flat interface), this predictor must give $v^* = 0$ exactly. This requires $\beta_f(G_h p_{\rm hyd})_{j+1/2} = g$, which holds when the same $\rho_f$ is used in $p_{\rm hyd}$ construction and in $\beta_f$.

---

## 10 Hydrostatic Split

Decompose $p = p_{\rm hyd}(z) + p'$ where $\nabla p_{\rm hyd} = \rho\mathbf{g}$ (continuous hydrostatic balance). The PPE then solves only for $p'$:

$$D_h^{bf}(\beta_f G_h^{bf} p') = \frac{1}{\Delta t}D_h^{bf}\mathbf{u}^* - D_h^{bf}(\beta_f G_h^{bf} p_{\rm hyd})$$

For a stratified flow with large $\rho$ variation, $p_{\rm hyd}$ dominates $p$ by orders of magnitude and the PPE for $p'$ has a much smaller condition number. Reinitialize $p_{\rm hyd}$ from $\rho^{n+1}$ at every step (interface moves, so $p_{\rm hyd}$ changes).

---

## 11 Complete 8-Phase NS+CLS Algorithm (A→H)

```
Phase A:  CLS conservative transport   psi^n, u^n  →  psi^(1)
Phase B:  Pre-reinit mass correction   psi^(1)     →  psi^(2)   [optional]
Phase C:  Reinit + geometry            psi^(2)     →  phi^{n+1}, psi^{n+1}, n, kappa
Phase D:  Material update              psi^{n+1}   →  rho^{n+1}, mu^{n+1}, beta_f
Phase E:  NS predictor                 u^n, p^n    →  u*
Phase F:  PPE solve                    u*, beta_f  →  p^{n+1}
Phase G:  Velocity corrector           u*, p^{n+1} →  u^{n+1}
Phase H:  Diagnostics                  all fields  →  scalar monitors
```

Interface-first ordering (A–D before E–G) ensures all NS force terms use $\rho^{n+1}$, $\mu^{n+1}$, $\kappa^{n+1}$. The only geometry lag is in the advecting velocity: CLS Stage A uses $\mathbf{u}^n$ because $\mathbf{u}^{n+1}$ is not yet available.

---

## 12 Geometry Lag Policy

| Quantity | Time level | Phase that sets it |
|----------|-----------|-------------------|
| $\rho$, $\mu$ | $n+1$ | D |
| $\kappa$, $\mathbf{n}$ | $n+1$ | C |
| $\beta_f = 1/\rho_f$ | $n+1$ | D |
| $p$ (explicit in predictor) | $n$ | F of previous step |
| Advecting velocity ($\mathbf{u}$ in CLS Stage A, advection $\mathcal{A}^n$) | $n$ | G of previous step |
| Viscous CN: time-centered | $(n + n^*)/2$ | WIKI-T-033 |

The $O(\Delta t)$ geometry lag from using $\mathbf{u}^n$ in CLS is unavoidable without sub-cycling. For second-order accuracy in the interface position, use AB2 extrapolation for the advecting velocity: $\mathbf{u}^{n+1/2} \approx \frac{3}{2}\mathbf{u}^n - \frac{1}{2}\mathbf{u}^{n-1}$.

---

## 13 Operator Splitting Safety

### Non-symmetric Lie splitting

The Phase A–H algorithm is first-order accurate in the splitting error ($O(\Delta t)$ from non-symmetric splitting of interface and NS operators). For two-phase NS with moderate surface tension, this is acceptable.

### Critical ordering requirements

1. CLS (Phases A–D) **must** complete before NS predictor (Phase E) — geometry must be consistent
2. Material update (Phase D) **must** complete before Phase E — $\rho^{n+1}$ in predictor
3. Phase G corrector **must** use the same $G_h^{bf}$ as Phase F PPE (P-2, WIKI-X-029)
4. Phase F PPE **must** use the same $\beta_f$ as Phase G corrector (P-4, WIKI-X-029)

Violating any of these breaks BF consistency, not just time accuracy.

---

## 14 Anti-Patterns and V1/V2/V3 Roadmap

### Anti-pattern table

| Anti-pattern | Failure mode |
|--------------|-------------|
| CCD for $\psi$ transport | Nonlinear instability from over-differentiating tanh |
| $(u\cdot\nabla)u$ non-conservative form | Spurious acceleration from residual divergence |
| Using $\mathbf{u}^*$ (unprojected) for CLS Stage A | Divergence error → spurious $\psi$ mass |
| Different $\rho_f$ for gravity and $\beta_f$ | Spurious body force at flat interface |
| Stage F (post-reinit mass correction) omitted | Mass drift after every reinit |
| Reinit run after NS predictor (Phase E) | Geometry inconsistency in predictor |
| PPE $G_h$ ≠ corrector $G_h$ | BF broken regardless of order (CHK-172) |
| $\varepsilon$ changed mid-simulation | Profile alteration; $\kappa$ discontinuity |
| Explicit viscous on non-uniform grid | Viscous CFL $O(h^2)$ → impractical $\Delta t$ |
| DCCD on $\psi$ face flux | Mass non-conservation; interface deformation |
| Uniform CFL based on bulk $h$ (not $h_{\rm min}$) | Instability in refined interface cells |

### V1/V2/V3 roadmap

| Version | Content | Accuracy target |
|---------|---------|----------------|
| **V1** | WENO5 CLS; 2nd-order advection; 2nd-order viscous; 2nd-order face-flux PPE; Lie splitting | $O(h)$ spurious current; proof-of-concept |
| **V2** | CCD bulk momentum advection; CN viscous + interface band; FCCD PPE + defect correction; full 7-principle BF | $O(h^2)$–$O(h^3)$ spurious current; production |
| **V3** | CCD bulk Layer A viscous; IIM jump correction for FCCD PPE; high-order $\kappa$; AB3+Richardson-CN time integration | $O(h^3)$–$O(h^4)$ spurious current; research |

The V1→V2 jump (from 2nd-order advection to CCD) requires adding the interface-band detection (WIKI-X-030 §2) to the momentum advection path. The V2→V3 jump (IIM row correction) requires nontrivial compact linear system modification at interface-crossing rows (WIKI-T-063 §5.2).
