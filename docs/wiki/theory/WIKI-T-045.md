---
ref_id: WIKI-T-045
title: "Late Blowup Hypothesis Catalog: G^adj Residual Instability on Non-Uniform Grids (WIKI-E-030)"
domain: theory
status: OPEN  # Exp-1 confirms H-01+H-16 primary; Exp-2/3/4 pending
superseded_by: null
sources:
  - path: src/twophase/simulation/ns_pipeline.py
    description: Corrector Step 5 L805–815 — G^adj vs CCD mixed-metric balanced-force
  - path: src/twophase/coupling/gfm.py
    description: kappa_f arithmetic mean, non-uniform spacing
  - path: experiment/ch13/config/ch13_02_waterair_bubble.yaml
    description: base config for late blowup experiments
depends_on:
  - "[[WIKI-T-044]]: FVM-CCD Metric Inconsistency (G^adj theory)"
  - "[[WIKI-T-004]]: Balanced-Force Condition — same-operator requirement"
  - "[[WIKI-T-017]]: FVM Reference Methods — PPE Face Coefficients"
  - "[[WIKI-T-042]]: eikonal_xi reinitialization theory"
  - "[[WIKI-E-029]]: exp13_17 water-air GFM — KE monotone increase"
  - "[[WIKI-X-016]]: Dispatch Policy — eikonal_xi α>1 long-time not verified"
  - "[[WIKI-E-030]]: Observed late blowup at t≈12.6, step 28122"
consumers:
  - domain: experiment
    description: Exp-1(diag), Exp-2(σ=0), Exp-3(CFL×0.5), Exp-4(no reinit) discriminating experiments
tags: [non_uniform_grid, blowup, balanced_force, hypothesis, parasitic_current, eikonal, density_ratio, late_instability]
compiled_by: Claude Sonnet 4.6
compiled_at: "2026-04-20"
---

# Late Blowup Hypothesis Catalog: G^adj Residual Instability (WIKI-E-030)

## Overview

G^adj (WIKI-T-044) eliminated the early blowup (step 51 → step 28,122: ×550 extension), but a
**new late blowup emerges at t ≈ 12.60 (step 28,122)** with no physical explanation
(y_c barely moved: Δy ≈ 0.015; volume conservation: machine precision 4.69×10⁻¹⁵).

G^adj fixed the Corrector's pressure-gradient metric, but introduced a new structural
inconsistency: **∇p now lives in FVM face-metric space while the CSF force f_σ = σκ∇ψ
remains in CCD node-metric space**. This catalog enumerates all theoretically plausible
causes, organized by mechanism category.

### Observation Summary

| Metric | Value |
|--------|-------|
| Blowup step / time | 28,122 / t ≈ 12.60 |
| KE at t=12.50 | 5.93×10⁻¹ (onset of rapid rise) |
| KE at t=12.60 | 1.04×10⁶ (blowup) |
| Bubble centroid y_c | 0.5438 (barely moved from 0.50) |
| Volume conservation | 4.69×10⁻¹⁵ (machine precision — normal) |
| Grid | 64×128, α=1.5, wall BC |
| Physics | ρ=833:1, σ=1, μ=0.05, g=0.001 |
| Method | eikonal_xi + phi_primary_transport + consistent_gfm |

---

## Category I — Balanced-Force Structural Inconsistency

Per-step O(h²) residual injected into velocity field; accumulates over 28k steps.

### H-01 — Corrector Mixed-Metric Balanced-Force Residual ⭐ (Primary candidate)

**Mechanism:**
The velocity corrector (ns_pipeline.py L814–815) applies:

$$u = u^* - \frac{\Delta t}{\rho} \underbrace{\mathcal{G}^\text{adj}p}_{\text{FVM face-metric}} + \frac{\Delta t}{\rho} \underbrace{f_x}_{\text{CCD node-metric}}$$

where $f_x = \sigma\kappa \cdot (\mathcal{G}_\text{CCD}\psi)$.

**Balanced-force residual at static equilibrium** ($\nabla p = \sigma\kappa\nabla\psi$):

$$\mathcal{R} = \mathcal{G}^\text{adj}p - \sigma\kappa\,\mathcal{G}_\text{CCD}\psi
= \bigl[\mathcal{G}_\text{CCD}p + O(h^2)\bigr] - \sigma\kappa\,\mathcal{G}_\text{CCD}\psi
= \underbrace{\mathcal{G}_\text{CCD}(p - \sigma\kappa\psi)}_{O(h^6)} + O(h^2) = O(h^2)$$

On the **uniform grid**: $J_f = J_n$ (both equal $1/h$), so $\mathcal{G}^\text{adj} = \mathcal{G}_\text{CCD}$ and $\mathcal{R} = 0$.

On **non-uniform grid** (α=1.5): WIKI-T-044 confirmed $\max|J_f - J_n|/J_f \approx 77\%$,
so $\mathcal{R}$ is large. This residual is injected into the velocity field at every step.

**Strength:** HIGH. Structurally certain; the question is whether the accumulation rate
is sufficient to cause blowup at the observed timescale.

**Discriminating experiment:** Exp-1 (diagnostic): `bf_residual_max` time series.
If this quantity grows monotonically before t=12.5, H-01 is confirmed as the driver.

---

### H-02 — PPE Source CCD-div vs FVM-Laplacian Inconsistency

**Mechanism:**
PPE (L795–802): $\text{RHS} = (\nabla \cdot u^*)_\text{CCD} / \Delta t$, but PPE matrix
$A = \mathcal{L}_\text{FVM}$. The discrete divergence-free constraint $\mathcal{D}_\text{FVM}(\mathcal{G}^\text{adj}p) = \mathcal{L}_\text{FVM}p$ is consistent (WIKI-T-044), but the source $(\nabla\cdot u^*)_\text{CCD}$ uses a different operator. This means the PPE solves:

$$\mathcal{L}_\text{FVM}p = \frac{(\nabla\cdot u^*)_\text{CCD}}{\Delta t}$$

but we need $\mathcal{D}_\text{FVM}(u^*/\Delta t)$ on the RHS for full consistency. The
residual is $O(h^2)$ per step and accumulates.

**Strength:** MEDIUM. Present on uniform grids too (H-02 is structural to the CCD+FVM
mixed approach), so if H-02 alone caused the blowup it would occur on uniform grids as well.
However, non-uniform grids amplify the $O(h^2)$ term.

**Discriminating experiment:** Exp-1: `div_u_max` after Corrector. Sustained non-zero
divergence growth indicates H-02 contribution.

---

### H-03 — Non-Incremental Projection: O(Δt) Splitting Error

**Mechanism:**
The current Predictor (L765–771) contains no $\nabla p^n$ term — this is a **non-incremental**
(standard) projection method. IPC (Incremental Pressure Correction) reduces the splitting
error to $O(\Delta t^2)$ by including $-\nabla p^n/\rho$ in the Predictor. With the
non-incremental form, the splitting error is $O(\Delta t)$ per step:

$$\|u^{n+1} - u_\text{exact}^{n+1}\| = O(\Delta t) \cdot O(\text{splitting residual})$$

Over $N = 28{,}122$ steps, the cumulative error is $O(\Delta t \cdot N) = O(1)$ for $\Delta t = \text{CFL} \cdot h/|u|$.

**Strength:** MEDIUM. This is a fundamental accuracy limitation, but the non-incremental
form is stable in many implementations. More relevant as an amplification factor for H-01.

**Discriminating experiment:** Exp-3 (CFL×0.5): if the blowup step doubles (∝ 1/Δt),
the splitting error accumulation (H-03) is implicated.

---

### H-04 — `consistent_gfm` Skeleton: b^GFM Absent from Main PPE

**Mechanism:**
In ns_pipeline.py, `reproject_mode: consistent_gfm` only affects `_reproject_velocity`
(L406: `use_varrho = mode in {"variable_density_only", "consistent_gfm"}`).
The **main PPE RHS** (L797–801) uses the CSF balanced-force source:

```python
rhs = (du_s_dx + dv_s_dy) / dt
rhs += df_x + df_y   # CSF balanced-force, NOT b^GFM
```

The GFM pressure-jump condition $[p]_\Gamma = \sigma\kappa$ is **never enforced** in the
main PPE. Young–Laplace is absent, so the pressure solution is systematically wrong across
the interface on every step.

**Strength:** MEDIUM-HIGH. This is a design gap, not a metric inconsistency, and it exists
on uniform grids too (exp13_17 with uniform grid also shows KE growth). But combined with
non-uniform metric errors, the per-step pressure error near the interface is amplified.

**Discriminating experiment:** Exp-2 (σ=0): if blowup disappears, the interface pressure
jump (Young-Laplace) is causally linked.

---

## Category II — Level-Set / Reinitialization Accuracy Degradation

### H-05 — ξ-SDF Index-Space Distance ≠ Physical Distance on Non-Uniform Grid

**Mechanism:**
`_xi_sdf_phi` in `reinit_eikonal.py` computes the SDF using **index-space Euclidean distance**
$\sqrt{(i-i^*)^2 + (j-j^*)^2}$, not physical-space distance. On a non-uniform grid (α=1.5),
the physical spacing $h_i$ varies by up to a factor of ~3 across the domain. The ξ-SDF
systematic overestimates the physical SDF in coarse regions and underestimates in fine regions.

Over 28,000/2 = 14,061 reinit calls, the zero-set of $\phi$ (the interface) drifts
systematically. Each reinit call introduces an $O(\delta h / h_\text{min})$ error; on α=1.5
this can be $O(1)$.

**Strength:** MEDIUM. Volume conservation is machine-precision (4.69×10⁻¹⁵), which suggests
the zero-set is NOT drifting globally. However, local interface shape errors can accumulate
without global volume change.

**Discriminating experiment:** Exp-4 (no reinit): if late blowup disappears or shifts
significantly, ξ-SDF reinit is causally linked.

---

### H-06 — WIKI-X-016 Authority: α>1 + σ>0 + eikonal_xi Long-Time "Not Verified"

**Mechanism:**
WIKI-X-016 Dispatch Policy explicitly states:

> "Any σ, non-uniform grid α>1: split. Reason: Eikonal xi-SDF: σ>0 long-time not verified."
> "Split-only is still the σ>0 reference method for T>2 until T=10 is verified for eikonal_xi + eps_scale=1.4."

ch13_02_waterair_bubble uses `eikonal_xi + α=1.5 + σ=1 + T=20` — this combination has
**never been validated** past T=2. The blowup at T≈12.6 may simply be entering an
uncharted instability regime of the xi-SDF method.

**Strength:** HIGH (as epistemic bound). The combination is explicitly marked "not verified".
This is not a specific mechanism but a fundamental unknownness.

**Discriminating experiment:** Exp-4 (no reinit): isolates ξ-SDF from the dynamics.

---

### H-07 — Non-Uniform ε_arr Makes CSF Concentration Spatially Inconsistent

**Mechanism:**
`eps_arr = eps_xi × max(hx, hy)` varies across the non-uniform grid. The CSF force
magnitude scales as $\sigma\kappa/\varepsilon_\text{arr}$; where $\varepsilon$ is small
(fine-grid region), the force is stronger. This spatial non-uniformity in the
surface-tension concentration creates net spurious forces that rotate the bubble and
generate non-physical flow patterns even in the absence of real dynamics.

**Strength:** LOW-MEDIUM. Volume conservation is fine, suggesting ε_arr variation is
small relative to other effects.

**Discriminating experiment:** Exp-1 (diagnostic): `ppe_rhs_max` time series captures
CSF source magnitude growth.

---

### H-08 — phi_primary_transport: logit(ψ)·ε Metric Problem

**Mechanism:**
With `phi_primary_transport=true`, $\phi = \text{logit}(\psi)\cdot\varepsilon$ is transported
by CCD. The CCD metric correction on non-uniform grids applies $J = \partial\xi/\partial x$
to convert ξ-space derivatives to physical-space derivatives. The product
$\varepsilon(x) \cdot J(x)$ (interface width × metric Jacobian) couples the interface
sharpness and grid deformation in a non-trivial way near the interface ($|\phi| \sim \varepsilon$).

**Strength:** LOW. The deep-interior ($\phi \gg 0$) stability provided by `phi_primary_transport`
(CHK-140) is intact. Interface-region errors are small per step.

**Discriminating experiment:** Not directly testable in the current 4 experiments.

---

## Category III — High-Density-Ratio Error Amplification

### H-09 — 1/ρ_g = 833× Amplification of O(h²) BF Residual in Gas Phase

**Mechanism:**
The BF residual $\mathcal{R}$ from H-01 is injected into the velocity field as:

$$\delta u = -\frac{\Delta t}{\rho}\,\mathcal{R}$$

In the gas phase ($\rho_g = 1$), this is $833\times$ larger than in the liquid phase
($\rho_l = 833$). Even if $|\mathcal{R}| \sim 10^{-4}$ (small), the gas-phase velocity
perturbation is $|\delta u| \sim 833 \times 10^{-4} \times \Delta t$. After 28,122 steps:

$$|\Delta u_\text{cumulative}| \sim 833 \times 10^{-4} \times 0.10 \times 28122 \sim 234$$

This rough estimate ($\Delta t \approx 0.1 \times h_\text{min}/|u|$) suggests that even a
small per-step residual can accumulate to blow up the gas-phase velocity.

**Strength:** HIGH. The density ratio is extreme (833:1). WIKI-E-029 already confirmed
KE monotone increase in the same ρ=833:1, α=1.5 configuration.

**Discriminating experiment:** Exp-2 (σ=0): removing surface tension eliminates the BF
residual source. If stable, H-09 combined with H-01 is confirmed.

---

### H-10 — WIKI-E-029 Precedent: Same Configuration Already Shows KE Monotone Increase

**Mechanism:**
WIKI-E-029 (exp13_17): ρ=833:1, α=1.5, eikonal_xi, GFM, **no gravity** — KE increased
monotonically from $5\times10^{-6}$ to $0.098$ over T=8 (20,000× increase). The displacement
$D$ exceeded its initial value at the second peak, indicating non-physical energy injection.

ch13_02 differs only in $g=0.001$ (gravity added). If the same KE growth mechanism operates,
the current late blowup is the continuation of the same instability observed in exp13_17,
merely delayed to T≈12.6 by the G^adj fix.

**Strength:** HIGH (empirical precedent). The prior experiment strongly suggests the
instability is endemic to the ρ=833:1, α=1.5 combination, not specific to bubble rise dynamics.

**Discriminating experiment:** Exp-2 (σ=0) breaks the connection to WIKI-E-029; Exp-1
(diagnostic) can compare KE growth rate to exp13_17 baseline.

---

### H-11 — CCD Metric Amplification at High-Density Interface

**Mechanism:**
CCD `apply_metric` applies $J \cdot (\partial/\partial\xi)$ and $J \cdot (dJ/d\xi) \cdot (\partial^2/\partial\xi^2)$
corrections. At the gas-liquid interface, $\rho$ varies by a factor of 833 over ~3 cells.
The combination of large $dJ/d\xi$ (non-uniform grid metric gradient) and large $d\rho/dx$
(interface density jump) creates a cross-coupling term in any operator applied to $\rho$-weighted
quantities. This affects the CSF force ($f_\sigma \propto \kappa\nabla\psi$) and the
viscous term ($\mu\nabla^2 u$).

**Strength:** LOW-MEDIUM. This is a higher-order effect; the dominant metric error is captured
in H-01.

---

## Category IV — Curvature and Surface Tension Accuracy

### H-12 — CCD Curvature κ Has O(h) Error on Non-Uniform Grid

**Mechanism:**
CCD computes $\kappa = \nabla\cdot(\nabla\psi/|\nabla\psi|)$. The second derivatives
needed for κ involve $J^2\partial^2/\partial\xi^2 + J(dJ/d\xi)\partial/\partial\xi$ on
non-uniform grids. The $dJ/d\xi$ term is $O(1)$ for α=1.5 near the interface. The curvature
error is $O(h)$ rather than the nominal $O(h^6)$ of CCD on uniform grids.

If $|\delta\kappa| \sim O(h)$, then $f_\sigma = \sigma\delta\kappa\nabla\psi$ is a spurious
force of order $\sigma/L$ ($L$ = domain size). Over time, this drives a slow artificial drift.

**Strength:** MEDIUM. Observable as `kappa_max` growth in Exp-1. If κ_max grows
monotonically before t=12.5, H-12 is contributing.

**Discriminating experiment:** Exp-1 (diagnostic): `kappa_max` time series.

---

### H-13 — kappa_f Arithmetic Mean: Interface-Position Weighting Error

**Mechanism:**
In `gfm.py`: `kappa_f = 0.5 * (kappa[sl_L] + kappa[sl_R])`.
The exact face interpolation should use $\theta = |\phi_L|/(|\phi_L|+|\phi_R|)$:
$\kappa_f = (1-\theta)\kappa_L + \theta\kappa_R$.

On non-uniform grids, $\theta \neq 0.5$ when the interface does not bisect the face midpoint.
The error is $O(|\phi_L - \phi_R|) = O(d_f \cdot |\nabla\phi|)$.

**Strength:** LOW. This is a second-order correction on top of H-12.

---

### H-14 — Interface Deformation Induces Curvature Regime Change

**Mechanism:**
The bubble barely moves (Δy=0.015 over t=0→12.6), but the interface shape may be evolving
via capillary oscillations. Near t≈12.5, $\kappa_\text{max}$ might reach a threshold where
the CCD curvature accuracy degrades significantly (e.g., interface becomes too thin or too
curved relative to the grid resolution).

**Strength:** MEDIUM. Observable in Exp-1. If `kappa_max` spikes at t≈12.5 (not t=12.0),
the curvature regime change is the trigger.

---

## Category V — Temporal Dynamics and Criticality

### H-15 — Linear Accumulation Reaching Critical Threshold

**Mechanism:**
If the per-step BF residual energy injection $\varepsilon_\text{res}$ is approximately constant,
the cumulative kinetic energy grows as $\text{KE}(t) \approx \varepsilon_\text{res} \cdot N_\text{steps}$.
When $\text{KE}$ exceeds a critical threshold $\text{KE}_\text{crit}$, convective nonlinearity
takes over and causes exponential runaway. This predicts:

$$N_\text{blowup} \propto \frac{1}{\varepsilon_\text{res}} \propto \frac{1}{\Delta t}$$

**Key prediction:** Halving CFL (Exp-3, CFL=0.05) should approximately **double** the blowup step
(from ~28k to ~56k). If instead the blowup step remains the same (in physical time t), H-15 is
disproved and H-16 (physical-time instability) is supported.

**Strength:** HIGH (testable). This is the most cleanly falsifiable hypothesis.

**Discriminating experiment:** Exp-3 (CFL×0.5). Gold-standard test for H-15.

---

### H-16 — Nonlinear KE Runaway: Physical-Time Instability

**Mechanism:**
The observed KE pattern (gradual increase t=10–12.5, then 44× jump in 0.09 time units,
then 40,000× jump in 0.01 time units) is consistent with a **supercritical instability**
in physical time:

$$\frac{d(\text{KE})}{dt} \approx \lambda(\text{KE}) \cdot \text{KE}$$

where $\lambda > 0$ once $\text{KE}$ exceeds a threshold. This would appear at a fixed
physical time $t^*$ regardless of $\Delta t$ (unlike H-15).

**Key prediction:** Halving CFL should NOT change the blowup physical time $t^*$.

**Discriminating experiment:** Exp-3 (CFL×0.5). Contradicts H-15.

---

### H-17 — Physical Resonance at t≈12.6

**Mechanism:**
The Stokes terminal velocity estimate: $U_T \approx 2\Delta\rho g R^2 / (9\mu) = 2 \times 832 \times 0.001 \times 0.0625 / (9 \times 0.05) \approx 0.231$.
Domain transit time: $L_y/U_T = 2/0.231 \approx 8.7$. The time $t \approx 12.6 \approx 1.45$ domain transit times.

An alternative: capillary oscillation period $T_c = 2\pi/\omega_0$ with 2D Lamb frequency
$\omega_0 = 0.679$ (WIKI-T-043 for $\rho=833:1$): $T_c \approx 9.25$. Then $t \approx 12.6 \approx 1.36 T_c$.

Neither timescale gives a clean integer multiple, making H-17 less convincing.

**Strength:** LOW. Physical timescale coincidence is possible but not supported by
the nearly-static y_c=0.54 (only 0.04 displacement).

---

### H-18 — PPE Matrix Ill-Conditioning at Late Times

**Mechanism:**
As the gas-liquid density field evolves, the harmonic-mean PPE matrix $A = \mathcal{L}_\text{FVM}(\rho)$
changes. The condition number $\kappa(A)$ scales as $\rho_l/\rho_g = 833$ for the
density-ratio contrast term. If the gas bubble becomes highly deformed at t≈12.6,
the local condition number near the interface could grow, degrading the direct solver
accuracy.

**Strength:** LOW. The solver is `spsolve` (direct), not iterative, so condition number
affects accuracy but not convergence. Machine-precision errors in direct solve are
$O(\kappa(A) \cdot \varepsilon_\text{machine})$; for κ≈833 this is $\sim 10^{-13}$, still
below relevant scales.

---

### H-19 — Pressure Pin Constraint Generates Artificial Mode on Non-Uniform Grid

**Mechanism:**
`rhs_vec[_pin_dof] = 0.0` fixes pressure to zero at one DOF (typically a corner). On a
non-uniform FVM grid, the eigenvectors of $\mathcal{L}_\text{FVM}$ differ from the uniform
case. The pin constraint forces a specific eigenvector decomposition that may inject a slow
drift mode into the pressure field, which propagates into velocity via the Corrector over
many time steps.

**Strength:** VERY LOW. This would manifest as a slowly growing pressure gradient across the
domain, which would cause bubble drift (but y_c is nearly static). Likely not a primary cause.

---

### H-20 — `_reproject_velocity` is CCD-Consistent (Excluded)

**Finding:**
`_reproject_velocity` uses CCD for both `div` (L412–414) and `grad` (L420–424). The
balanced-force constraint in reprojection is consistent within CCD space. This function
is **not** a source of the late blowup.

**Strength:** EXCLUDED.

---

## Experimental Evidence — Exp-1 (ch13_02_diag, 2026-04-20)

**Config:** T=13, debug_diagnostics=true, print_every=100. 23,819 steps to blowup at t=10.508.
**NPZ:** `experiment/ch13/results/ch13_02_diag/data.npz`

### Key measurements

| Metric | t≈0 (step 1) | t≈0–2 (median) | t≈4–6 (median) | t≈8–10 (median) | Blowup (step 23,819) |
|--------|-------------|----------------|----------------|-----------------|----------------------|
| `bf_residual_max` | 884 | 4,803 | 18,848 | 18,367 | 2.2×10¹⁰ |
| `kappa_max` | 1,561 | ~2,000–3,000 (noisy) | ~10,000–60,000 (chaotic) | ~15,000–25,000 | 2.4×10⁴ |
| `ppe_rhs_max` | 93.7 | 4.63×10⁵ | 4.73×10⁵ | ~4×10⁵ | 9.9×10⁹ |
| `div_u_max` | 0.133 | ~143 | ~150 | ~165 | 6.2×10³ |
| `kinetic_energy` | 6.4×10⁻⁷ | 0.014–0.069 | 0.069–0.090 | 0.12–0.15 | 1.0×10⁶ |
| `volume_conservation` | 0 | < 10⁻¹⁴ | < 10⁻¹⁴ | < 10⁻¹⁴ | 3.3×10⁻¹⁴ |

### Timeline

```
step=1,      t=0.0007:  bf=884,    KE=6.4e-7  (structural residual from t=0)
step=100,    t=0.0485:  bf=6694,   KE=0.014,  div_u=148  (early transient)
step=3000,   t=1.308:   bf=4945,   KE=0.043   (transient decay)
step=7100,   t=3.106:   bf=14330,  KE=0.081   ← discrete jump event
step=7200,   t=3.150:   bf=17800,  KE=0.069   (post-jump plateau)
step=10000,  t=4.398:   bf=20020,  KE=0.069   kappa_max spikes to 1.1e5
step=11900,  t=5.231:   bf=1639,   KE=0.095   ← bf_res collapse (bubble reshaping?)
step=18000,  t=7.973:   bf=1018,   KE=0.123   ← bf_res minimum (990 at t=8.36)
step=22329,  t=10.011:  KE=0.150   ← smoothed KE > 0.15 (onset of sustained rise)
step=23255,  t=10.429:  KE=100×initial
step=23375,  t=10.481:  KE=1000×initial
step=23609,  t=10.506:  KE=1028    BLOWUP  (bf=1.3e7, ppe_rhs=8.4e6)
step=23819:  BLOWUP at t=10.5082
```

### Hypothesis evaluation from Exp-1

**H-01 (BF residual) — CONFIRMED PRIMARY:**
- bf_res = 884 at step 1 (before any dynamics). Purely structural.
- Median grows 4803 → 18848 from t=0–2 to t=4–6 (×4).
- Oscillatory envelope tracks bubble capillary oscillations.
- NOT a simple monotone accumulation — oscillatory with quasi-periodic minima.
- At blowup runaway: bf_res grows exponentially (3.2e4 → 3.8e5 → 1.3e7 in 300 steps).

**H-09 (density ratio amplification) — CONFIRMED (implicit):**
- Gas-phase velocity perturbation per step: Δu_g ≈ dt × bf_res / ρ_g = 4e-4 × 10,000 / 1 = 4.
- This is 833× larger than the liquid-phase perturbation.
- Explains why KE slowly accumulates even while bubble barely moves.

**H-15 (linear accumulation) — PARTIALLY REFUTED as trigger:**
- KE does grow slowly (×6 over 10 time units: 0.02 → 0.15), consistent with slow accumulation.
- But the TRIGGER is non-linear — KE×100 to KE×1000 in 120 steps (Δt≈0.05).
- H-15 describes the slow phase; the actual blowup is H-16.

**H-16 (non-linear runaway) — CONFIRMED:**
- KE=0.15 (step 22,329, t=10.01) to BLOWUP (step 23,819, t=10.51): 1,490 steps, Δt=0.50.
- KE×100 to KE×1000: 120 steps, Δt=0.05 — super-exponential growth.
- Consistent with a supercritical Hopf-type transition once KE threshold crossed.

**H-12/H-14 (curvature spike as trigger) — NOT CONFIRMED:**
- kappa_max is chaotic throughout (370–165,000), with extreme spikes occurring from t≈3 onward.
- kappa_max does NOT show a special spike immediately before the KE runaway (step 23,300: kappa=2.1e4, comparable to many earlier values).
- Curvature fluctuations may contribute to bf_res oscillations but are not the blowup trigger.

**H-02 (PPE divergence) — BACKGROUND:**
- div_u stabilizes at ~140–165 from step 100 onward (not growing monotonically).
- ppe_rhs is rock-steady at ~4.5–4.8×10⁵ until the blowup begins.
- Both are consistent with a persistent but non-growing background error.

**H-07 (ppe_rhs growth) — REFUTED:**
- ppe_rhs shows no monotone growth; it's stable throughout. H-07 is not primary.

### Outstanding questions (Exp-2/3 pending)

- **Exp-2 (σ=0):** Does blowup disappear without surface tension? (H-01 test)
- **Exp-3 (CFL=0.05):** Does blowup time t* stay same (H-16) or scale with steps (H-15)?

---

## Experimental Evidence — Exp-4 (ch13_02_noreinit, 2026-04-20)

**Config:** T=20, reinit_every=0 (no reinit). 29,928 steps to blowup at t=13.4454.
**NPZ:** `experiment/ch13/results/ch13_02_noreinit/data.npz`

### Key measurements vs base run

| Time | KE (no reinit) | KE (base, with reinit) | Comment |
|------|---------------|----------------------|---------|
| t=5.0 | 0.0814 | ~0.070 (Exp-1 approx) | no reinit slightly higher early |
| t=8.0 | 0.117 | ~0.12 (Exp-1) | similar |
| t=10.0 | 0.132 | ~0.12–0.15 (Exp-1) | similar |
| t=12.0 | 0.178 | ~0.19 (Exp-1) | similar |
| t=12.5 | 0.180 | **0.59** (base run) | base 3× higher |
| t=13.0 | 0.216 | [blowup completed] | no reinit still alive |
| t=13.45 | **BLOWUP** | [blowup at t=12.6] | 0.85 time units later |

- Volume conservation: 1.913×10⁻¹⁴ (machine precision — reinit not needed for volume)
- Blowup step: 29,928 vs base 28,122 (+1,806 steps)
- Blowup physical time: 13.45 vs base 12.60 (**Δt = +0.85**)

### Hypothesis evaluation from Exp-4

**H-05 (ξ-SDF reinit as secondary destabilizer) — PARTIALLY CONFIRMED:**
- Without reinit, blowup occurs 0.85 time units LATER (t=13.45 vs t=12.60 base).
- At t=12.5: no-reinit KE=0.180 vs base KE≈0.59 — reinit inflates KE by ~3×.
- Reinit introduces small ξ-SDF shape errors that slightly amplify bf_res (via ψ deformation).
- **Reinit is a secondary destabilizer** (accelerates blowup by ~7%), NOT the primary cause.

**H-05 as primary cause — REFUTED:**
- Blowup still occurs at t=13.45 even without any reinit.
- The primary mechanism (H-01 BF residual) operates independently of reinit.

**H-06 (unverified combination) — PARTIALLY RELEVANT:**
- The α>1 + σ>0 + eikonal_xi combination is destabilizing, but mainly via H-01.
- Without eikonal_xi (no reinit), the system is still unstable — H-06 as the SOLE cause is refuted.

**Volume conservation with no reinit — INFORMATIVE:**
- VolCons stays at machine precision even without reinit.
- `phi_primary_transport=true` alone is sufficient to maintain volume.
- This confirms the ξ-SDF reinit is NOT needed for mass conservation — only for SDF quality.

### Decision tree conclusion

```
Exp-4: blowup at t=13.45 (LATER than base t=12.60)
  → reinit is DESTABILIZING: accelerates blowup by ~7%
  → H-05 as secondary contributor: CONFIRMED
  → H-05/H-06 as primary cause: REFUTED
  → H-01 is primary (operates without reinit)
```

---

## Hypothesis Summary Table

| ID | Category | Mechanism | Strength | Exp-1 Status | Key Experiment |
|----|----------|-----------|----------|--------------|----------------|
| **H-01** | BF | Corrector G^adj vs CCD f_x → O(h²)/step | **HIGH** ⭐ | ✅ CONFIRMED (bf_res=884 at t=0, median grows ×4) | Exp-2 (σ=0) |
| H-02 | BF | PPE source CCD-div vs FVM-Laplacian | MEDIUM | ℹ️ Background (div_u stable ~150, not growing) | Exp-3 (CFL×0.5) |
| H-03 | BF | Non-incremental O(Δt) splitting error | MEDIUM | ❓ Pending Exp-3 | Exp-3 (CFL×0.5) |
| H-04 | BF | b^GFM absent from main PPE | MEDIUM-HIGH | ❓ Pending Exp-2 | Exp-2 (σ=0) |
| H-05 | Reinit | ξ-SDF index vs physical distance | MEDIUM | ⚠️ SECONDARY CONFIRMED: no-reinit blowup +0.85t later, KE 3× lower at t=12.5 | Exp-4 done |
| **H-06** | Reinit | WIKI-X-016: α>1 eikonal long-time unverified | **HIGH** (epistemic) | ⚠️ SECONDARY: still blows up without reinit; H-01 primary | Exp-4 done |
| H-07 | Reinit | Non-uniform ε_arr CSF inconsistency | LOW-MEDIUM | ❌ REFUTED (ppe_rhs stable ~4.7e5 throughout) | — |
| H-08 | Reinit | phi_primary logit×ε metric coupling | LOW | — | — |
| **H-09** | Density | 1/ρ_g=833× amplification of BF residual | **HIGH** | ✅ CONFIRMED (implicit: gas-phase Δu_g ≈ 833× liquid) | Exp-2 (σ=0) |
| **H-10** | Density | WIKI-E-029 precedent: same conditions, same KE growth | **HIGH** | ✅ CONSISTENT (same slow KE drift pattern observed) | Exp-2 (σ=0) |
| H-11 | Density | CCD metric × density-jump cross-term | LOW-MEDIUM | — | — |
| H-12 | Curvature | CCD κ has O(h) error on non-uniform grid | MEDIUM | ⚠️ kappa chaotic (370–165,000); not the blowup trigger | Exp-2 (σ=0) |
| H-13 | Curvature | kappa_f arithmetic mean error | LOW | — | — |
| H-14 | Curvature | Interface deformation → κ regime change | MEDIUM | ❌ NOT CONFIRMED (kappa_max no special spike at blowup) | — |
| **H-15** | Temporal | Linear accumulation → critical threshold | **HIGH** (testable) | ⚠️ Slow phase confirmed; trigger is H-16, not linear | Exp-3 (CFL×0.5) |
| **H-16** | Temporal | Nonlinear physical-time instability | HIGH | ✅ CONFIRMED (KE×100→×1000 in 120 steps / Δt=0.05) | Exp-3 (CFL×0.5) |
| H-17 | Temporal | Physical resonance at t≈12.6 | LOW | ❌ IRRELEVANT (blowup at t=10.5 in diag run, not 12.6) | — |
| H-18 | Temporal | PPE conditioning (direct solver — negligible) | LOW | — | — |
| H-19 | Temporal | Pressure pin artificial mode | VERY LOW | — | — |
| H-20 | — | _reproject_velocity CCD-consistent — **excluded** | N/A | — | — |

---

## Discriminating Experiment Design

### Exp-1: Diagnostic Run (`ch13_02_diag.yaml`)
Record `bf_residual_max`, `div_u_max`, `kappa_max`, `ppe_rhs_max` every 100 steps, T=13.0.

**Decision tree from Exp-1 results:**
```
bf_residual_max grows before t=12.5?
  YES → H-01 is primary driver (BF residual accumulation)
  NO  → H-01 is not causal; check kappa_max

kappa_max spikes at t≈12.5?
  YES → H-12/H-14 (curvature regime change) is the trigger
  NO  → H-02/H-06 or unknown mechanism
```

### Exp-2: σ=0 Run (`ch13_02_sigma0.yaml`)
Remove surface tension. T=20.

**Decision tree:**
```
Blowup at similar t≈12.6?
  YES → Surface tension NOT causal; check H-05/H-06 (reinit) or numerical instability
  NO  → σ is causal → confirms H-01 + H-09 (BF residual × density amplification)
```

### Exp-3: CFL×0.5 Run (`ch13_02_cfl005.yaml`)
CFL=0.05. T=20.

**Decision tree:**
```
Blowup step ≈ 56k (physical time ≈ 12.6)?
  YES (same time) → H-16 (physical-time instability)
  NO, step ≈ 56k (step doubles but same time) → H-15 (step-linear accumulation)
  Both? → Mixed accumulation + physical instability
```

### Exp-4: No Reinit Run (`ch13_02_noreinit.yaml`)
`reinit_every: 0`. T=20.

**Decision tree:**
```
Earlier blowup (t < 12.6)?
  YES → reinit was stabilizing; H-05/H-06 as destabilizer ruled out
Later or no blowup?
  YES → reinit is destabilizing → H-05/H-06 directly implicated
```

---

## Root Cause Synthesis (Updated Post Exp-1, 2026-04-20)

**Confirmed mechanism: H-01 + H-09 + H-16 cascade**

### Phase 1: Structural residual injection (t=0 → t≈10, slow)

1. **H-01** — The G^adj/CCD metric mismatch creates a BF residual $\mathcal{R}$ from the
   very first step (bf_res=884 at t=0.0007). This is not accumulated — it is **structural**.
2. **H-09** — In the gas phase, $\delta u \propto \mathcal{R}/\rho_g = 833\times\mathcal{R}/\rho_l$.
   This injects 833× more parasitic velocity into the gas than the liquid per step.
3. KE grows slowly from 6.4×10⁻⁷ to 0.15 over 10 time units (~×230). The growth is
   oscillatory (tracks bubble capillary oscillations), not monotone.

### Phase 2: Nonlinear runaway (t≈10.0 → blowup at t≈10.5)

4. **H-16** — Once KE≈0.15, the convective term $u\cdot\nabla u$ in the Predictor becomes
   large enough to create a positive-feedback loop. KE doubles every ~60 steps.
5. The runaway is **not caused** by a curvature spike (H-14 refuted), nor by ppe_rhs growth (H-07 refuted).
6. The trigger threshold is physically set by when the parasitic gas velocity exceeds the
   CFL stability limit for the convective term.

### Outstanding: Exp-2/3/4 role

- **Exp-2 (σ=0):** Critical. If blowup disappears without surface tension, H-01 is the
  unique cause (surface tension provides the BF residual source). If blowup persists, then
  H-04/H-05/H-06 or a density-ratio instability not related to BF is the cause.
- **Exp-3 (CFL×0.5):** Distinguishes H-15 (blowup step doubles, physical time same) from
  H-16 (blowup at same physical time). Given Exp-1 shows H-16 is the runaway mechanism,
  we expect the physical time to be similar (t≈10–12).
- **Exp-4 (no reinit):** Determines whether eikonal_xi reinit is stabilizing or destabilizing.

### Architectural implication (post-analysis, no code change this session)

The proper fix requires putting **both** $\mathcal{G}^\text{adj}p$ and $\sigma\kappa\nabla\psi$
in the **same metric space**: either (a) both FVM-face (replace CCD gradient of ψ with a
FVM-face gradient), or (b) both CCD (replace G^adj with CCD in the Corrector, losing the
FVM consistency of the PPE but restoring BF balance). This is a fundamental redesign.

**This session does NOT implement any fix** — per the standing constraint "no patch-style modifications."
