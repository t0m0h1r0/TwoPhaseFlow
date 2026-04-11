---
id: WIKI-E-016
title: "§13 Benchmark Execution Results: 1 PASS, 1 PARTIAL, 1 FAIL"
status: ACTIVE
created: 2026-04-11
updated: 2026-04-11
depends_on: [WIKI-E-015, WIKI-L-014, WIKI-X-007]
---

# §13 Benchmark Execution Results

**Note (2026-04-11):** Results below are the **uniform-grid (α=1) baseline**.
Non-uniform grid reruns with rebuild frequency calibration documented in
[[WIKI-E-020]]. Paper §13.4 reflects the non-uniform results.

## Result Summary (uniform grid baseline)

| Exp | Name | Status | Key Metric |
|-----|------|--------|------------|
| §13.1 | Capillary wave | PARTIAL | KE oscillation correct; D(t) diagnostic inadequate |
| §13.2 | Rising bubble | **PASS** | v_term=0.160, |ΔV|/V₀=2.87×10⁻⁵ |
| §13.3 | Taylor deformation | **FAIL** | All 8 cases BLOWUP at t<0.02 |

## §13.1 Capillary Wave — PARTIAL

**What worked:** 15505 steps to T=10, KE oscillation+decay observed, simulation stable.

**What failed:** `_deformation()` (second-moment D=(L−B)/(L+B)) produces noisy signal; measured "period" ~0.02 vs theory T₀=0.92 (46× discrepancy).

**Root cause:** Second-moment method is a global shape measure, not a modal decomposition. It captures grid-noise oscillations instead of the l=2 capillary mode.

**Fix:** Replace with Fourier modal amplitude:
```
A_l(t) = ∫ (ψ − ψ₀) cos(l θ) dA
```
This directly projects onto the l=2 mode and filters grid noise.

**Volume conservation:** |ΔV|/V₀ = 1.89% at T=10.0 — acceptable for 15k steps but larger than §13.2's 0.003%.

## §13.2 Rising Bubble — PASS

**Results (4978 steps, T=3.0):**
- Terminal velocity: v_c = 0.160 (converged over last 500 steps)
- Centroid rise: y_c = 0.500 → 0.672 (Δy = 0.172)
- Volume conservation: |ΔV|/V₀ = 2.87 × 10⁻⁵ (**excellent**)
- No blowup, stable throughout

**Physics assessment:**
- Bubble accelerates under buoyancy, decelerates as drag increases, reaches terminal velocity
- Modified Hysing parameters (ρ_l/ρ_g=10 instead of 1000) produce qualitatively correct behavior
- Quantitative comparison with Hysing reference requires ρ_l/ρ_g=1000 → split PPE (future work)

## §13.3 Taylor Deformation — FAIL (All Cases)

**All 8 cases BLOWUP at t < 0.02.** Not a single case reached steady-state deformation.

| λ | Cases | t_final range | Root cause |
|---|-------|--------------|------------|
| 1 | 4/4 FAIL | 0.006–0.007 | Explicit viscous CFL at N=128 |
| 5 | 4/4 FAIL | 0.014–0.015 | Same (slightly more stable due to higher μ_l) |

**Root cause chain:**
1. Couette BC imposes u = ±1.0 at y-boundaries from step 1 → u_max = 1.0
2. At N=128, h = 0.0078; viscous CFL limit: dt < h²/(4ν) = 1.5×10⁻⁴
3. Capillary CFL at σ=0.5: dt_σ ~ 8×10⁻⁵
4. Combined CFL drives dt ~ 10⁻⁵, but explicit convective nonlinearity amplifies errors
5. BLOWUP within 600–1300 steps

**This is a known limitation:** §12.3e documented explicit viscous temporal degradation near interfaces. The Taylor experiment requires implicit viscous treatment (Crank-Nicolson), which is validated in exp11_25 but **not yet integrated into `TwoPhaseNSSolver`**.

**Remediation paths (ordered by effort):**
1. **N=32–64** — 4–16× CFL headroom; validates physics at lower resolution
2. **Reduce γ̇ to 0.5** — halves u_max, quadruples viscous CFL margin
3. **Crank-Nicolson in ns_pipeline** — removes viscous CFL entirely; proper fix
4. **Semi-implicit surface tension** — removes capillary CFL; future work (§WIKI-T-023)

## Key Insights

### 1. Explicit Viscous Scheme is the Primary Bottleneck
- Rising bubble (N=64×128, low shear) → stable
- Couette shear (N=128, u_max=1.0 at boundary) → BLOWUP
- The difference is u_max / h: bubble has u~0.16 at h=0.016; Couette has u=1.0 at h=0.008

### 2. Deformation Diagnostic Needs Modal Decomposition
- `_deformation()` (second moments) works for steady-state shapes (Taylor) but fails for oscillating modes (capillary wave)
- Need `_modal_amplitude(psi, l, center)` for Prosperetti comparison

### 3. Volume Conservation Depends on Run Length
- 5000 steps (bubble): |ΔV|/V₀ = 3×10⁻⁵
- 15000 steps (capillary): |ΔV|/V₀ = 2×10⁻²
- Reinitialization frequency and interface complexity affect long-term conservation
