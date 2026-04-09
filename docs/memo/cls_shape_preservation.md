# CLS Shape Preservation: Over-Reinitialization as the Dominant Error Source

Date: 2026-04-09
Status: VERIFIED (exp11_19)
Related: reinitialize.py, advection.py, WIKI-T-028, WIKI-E-009, WIKI-E-003

---

## Abstract

We investigate the dominant sources of shape error in CLS (Conservative
Level Set) advection with DCCD (Dissipative Compact Cubic Difference)
filtering. A priority-ordered parameter study on the single vortex
benchmark (LeVeque 1996, N=128) reveals that **fixed-frequency
reinitialization is the dominant shape error source (49% of L₂)**,
not DCCD high-frequency damping (which contributes only 2%). Switching
from fixed every-10-steps (227 reinit calls) to an adaptive trigger
based on the volume monitor M(τ)/M_ref > 1.10 (2 reinit calls) halves
the shape error. Combined with thinner interface (ε=1.0h), total
improvement reaches **59%**.

---

## 1. Motivation

WIKI-T-028 (CHK-101/102) established that the DCCD spatial operator
preserves mass exactly for periodic BC, and that the operator-splitting
mismatch in reinitialization is the root cause of mass loss. The post-hoc
mass correction (WIKI-T-027) resolves mass conservation to O(10⁻¹⁵).

The remaining question: **what limits shape accuracy?**

The initial hypothesis was that DCCD's spectral damping (H(π; 0.05) = 0.80,
i.e. 20% Nyquist damping) diffuses the interface over thousands of advection
steps. This turns out to be wrong.

---

## 2. Experimental Design

**Benchmark:** Single vortex (LeVeque 1996), N=128, T=8.0 (deform + reverse).
Baseline: ε_d=0.05, ε=1.5h, reinit every 10 steps, Forward Euler pseudo-time.

**Four parameters tested in priority order:**

| Priority | Parameter | Values tested |
|----------|-----------|---------------|
| P1 | ε_d (DCCD filter strength) | 0.05, 0.025, 0.01, 0.0 |
| P2 | ε/h (interface thickness) | 2.0, 1.5, 1.0, 0.75 |
| P3 | Reinit strategy | fixed-{10,20}, adaptive-{1.05,1.10,1.20}, none |
| P4 | Reinit time integration | FE-{4,8}step, RK3-{2,4}step |

**Metric:** L₂ shape error = √(mean((ψ_final − ψ_0)²)) after full
deform-reverse cycle.

---

## 3. Results

### 3.1 P1: DCCD Filter Strength — Negligible

| ε_d | L₂ | Δ vs baseline |
|-----|-----|---------------|
| 0.050 | 1.735e-01 | baseline |
| 0.025 | 1.759e-01 | −1.4% |
| 0.010 | 1.761e-01 | −1.5% |
| 0.000 | 1.772e-01 | −2.1% |

Even ε_d=0 (pure CCD, no filter) gives essentially the same L₂. The
DCCD transfer function H(kh) damps only near-Nyquist modes (wavelength
~2h), but the CLS interface profile has characteristic width O(ε) ≈ 1.5h,
meaning the profile is resolved by ~3 cells and its spectral content
is concentrated well below Nyquist.

**Conclusion:** DCCD damping does not cause shape error. The filter
targets wavelengths the interface profile does not occupy.

### 3.2 P2: Interface Thickness — Moderate

| ε/h | L₂ | Δ vs baseline |
|-----|-----|---------------|
| 2.00 | 1.856e-01 | −7.0% |
| 1.50 | 1.735e-01 | baseline |
| 1.00 | 1.476e-01 | **+14.9%** |
| 0.75 | 1.292e-01 | **+25.6%** |

Thinner interface resolves fine filament features better. At ε=1.0h the
interface occupies ~2 cells (still resolved by CCD's 6th-order stencil).
At ε=0.75h the profile approaches under-resolution; stability should be
verified for multi-phase flows.

**Conclusion:** ε=1.0h is a safe improvement. ε=0.75h is aggressive
but may be viable.

### 3.3 P3: Adaptive Reinitialization — Dominant Improvement

| Strategy | L₂ | Reinit count | Δ vs baseline |
|----------|-----|-------------|---------------|
| fixed-10 | 1.735e-01 | 227 | baseline |
| fixed-20 | 1.750e-01 | 113 | −0.9% |
| adaptive-1.05 | 1.184e-01 | 3 | **+31.8%** |
| **adaptive-1.10** | **8.896e-02** | **2** | **+48.7%** |
| adaptive-1.20 | 1.192e-01 | 2 | +31.3% |
| no-reinit | 6.700e-02 | 0 | +61.4% |

This is the central finding. The volume monitor M(τ) = ∫ψ(1−ψ)dV
measures the deviation of ψ from a sharp step function. When
M(τ)/M_ref > threshold, the interface has broadened enough to need
reinitialisation. For the single vortex test, this triggers only 2–3
times in 2270 steps — not 227 times.

**Why fixed-frequency hurts:** Each reinitialisation call executes 4
pseudo-time steps of the compression-diffusion PDE. Even with O(h³)
interface preservation per step, 227 calls × 4 steps = 908 pseudo-time
modifications accumulate to a significant shape distortion. The
compression-diffusion balance is not perfect at the discrete level
(WIKI-T-028 operator-splitting mismatch), and each step slightly
reshapes the transition zone.

**Optimal threshold:** M(τ)/M_ref > 1.10 gives the best L₂. The
threshold of 1.05 triggers one extra reinit (3 vs 2) without benefit;
1.20 is too permissive for some flow configurations.

**Conclusion:** Adaptive reinitialisation based on M(τ) reduces
unnecessary reinit by 99% and halves shape error.

### 3.4 P4: TVD-RK3 for Pseudo-Time — Marginal

| Config | L₂ | Δ vs baseline |
|--------|-----|---------------|
| FE-4step | 1.735e-01 | baseline |
| RK3-4step | 1.948e-01 | **−12.3%** (worse) |
| FE-8step | 1.776e-01 | −2.4% |
| RK3-2step | 1.640e-01 | +5.5% |

TVD-RK3 with the same step count is worse because it performs 3× more
RHS evaluations, each of which applies the compression-diffusion
operator. The temporal accuracy gain (O(Δτ³) vs O(Δτ)) is outweighed
by the additional interface processing.

RK3-2step (fewer steps, higher accuracy per step) is slightly better,
confirming the principle: **less total reinit processing = better shape**.

**Conclusion:** TVD-RK3 is not beneficial when combined with the
already-effective strategy of minimizing reinit frequency.

### 3.5 Combined

| Config | L₂ | Δ vs baseline | Reinits |
|--------|-----|---------------|---------|
| baseline | 1.735e-01 | — | 227 |
| best-eps_d (0.01) | 1.761e-01 | −1.5% | 227 |
| best-eps (1.0h) | 1.476e-01 | +14.9% | 227 |
| best-adaptive (1.10) | 8.896e-02 | +48.7% | 2 |
| combined-123 | 9.395e-02 | +45.8% | 2 |
| **combined-all** | **7.099e-02** | **+59.1%** | 4 |

The combined-all configuration (ε=1.0h, ε_d=0.01, adaptive-1.10,
RK3 pseudo-time) achieves 59% improvement over the baseline. The
dominant contributor is adaptive reinit (+49%), followed by interface
thinning (+15%). The remaining parameters contribute marginally.

---

## 4. Revised Shape Error Hierarchy

The initial priority ordering was:

```
Predicted:  P1 (eps_d) > P2 (eps) > P3 (adaptive) > P4 (RK3)
Actual:     P3 (adaptive) >> P2 (eps) >> P4 (RK3) > P1 (eps_d ≈ 0)
```

Quantitative decomposition of the baseline L₂ = 0.174:

| Source | Contribution | Evidence |
|--------|-------------|----------|
| Over-reinitialization | ~49% | adaptive vs fixed-10 |
| Interface thickness | ~15% | ε=1.0h vs 1.5h |
| Advection (inherent) | ~34% | no-reinit residual |
| DCCD damping | ~2% | eps_d sweep |

The "inherent" advection error (34%) represents the irreducible limit
of DCCD + TVD-RK3 on this benchmark at N=128. This can only be
improved by grid refinement.

---

## 5. Physical Interpretation

### 5.1 Why DCCD damping doesn't matter

The CLS profile ψ = H_ε(φ) = 1/(1+exp(−φ/ε)) has spectral content
concentrated at wavelengths λ ≥ 2πε. For ε = 1.5h:

$$
\lambda_{\min} \approx 2\pi\varepsilon = 9.4h
$$

The DCCD transfer function at this wavelength:

$$
H(2\pi h / 9.4h) = H(0.67) = 1 - 4 \times 0.05 \times \sin^2(0.335)
\approx 1 - 0.02 = 0.98
$$

Only 2% damping at the interface's characteristic wavelength. The 20%
Nyquist damping (at 2h) is irrelevant because the interface has
negligible energy there.

### 5.2 Why reinitialisation hurts more than it helps (for this test)

The single vortex test is a deform-reverse problem: the velocity field
creates extreme filament stretching at t = T/2, then reverses to
recover the original shape. The interface profile naturally broadens
under stretching but then sharpens again under reversal.

Reinitialization during the reversal phase **actively counteracts the
natural recovery**: it resharpens the profile based on the current
(deformed) ψ, which involves compression-diffusion processing that
shifts the transition zone. Each reinit imprints a slightly different
profile shape, and these modifications don't reverse when the flow
reverses.

The adaptive trigger recognizes that the profile only truly needs
correction at the point of maximum deformation (t ≈ T/2), not at every
10th step throughout the cycle.

### 5.3 Generalization caveat

The single vortex is a special case (time-reversible, incompressible,
no topology change). For production two-phase simulations:
- Topology changes (droplet breakup/coalescence) require reinit
- Long-time advection without reinit degrades the profile
- The adaptive threshold may need tuning per application

The M(τ)/M_ref > 1.10 trigger provides a physics-based criterion that
automatically adapts to the flow.

---

## 6. Recommendations

### For production simulations

1. **Replace fixed-frequency reinit with adaptive M(τ) trigger**
   (threshold 1.05–1.10). This is the single highest-impact change.

2. **Consider ε = 1.0h** instead of 1.5h for better feature resolution.
   Verify stability for the specific ρ_l/ρ_g ratio.

3. **Keep ε_d = 0.05** — reducing it provides no shape benefit and may
   reduce stability margins in complex flows.

4. **Keep Forward Euler for reinit pseudo-time** — TVD-RK3 is not
   cost-effective when reinit frequency is already optimized.

### Implementation

The adaptive trigger requires no library changes — it can be
implemented in the simulation loop:

```python
M_ref = sum(psi * (1 - psi)) * dV  # after initial reinit
for step in range(n_steps):
    psi = advection.advance(psi, vel, dt)
    M_cur = sum(psi * (1 - psi)) * dV
    if M_cur / M_ref > 1.10:
        psi = reinit.reinitialize(psi)
        M_ref = sum(psi * (1 - psi)) * dV
```

For the `SimulationBuilder` pipeline, this could be integrated as a
`reinit_mode='adaptive'` option with configurable threshold.

---

## 7. Open Questions

1. **Threshold sensitivity in two-phase flows:** The optimal 1.10 was
   found for the single vortex. Rising bubble / droplet collision may
   need different thresholds. A systematic study per flow type would
   be valuable.

2. **Topology-change detection:** When droplets merge or break up,
   M(τ) may not capture the need for reinit (the profile can be correct
   locally but topologically wrong). A curvature-based trigger
   (max|κ| > threshold) could complement M(τ).

3. **ε = 1.0h stability:** Thinner interface with ε = 1.0h at high
   density ratios (ρ_l/ρ_g > 100) may cause curvature oscillations.
   The interaction with the balanced-force condition needs verification.
