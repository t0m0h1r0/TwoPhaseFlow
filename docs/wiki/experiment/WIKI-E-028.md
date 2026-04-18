---
ref_id: WIKI-E-028
title: "Eikonal/ZSP/ξ-SDF/FMM/ε-Widening: Prosperetti Benchmark Results (CHK-136..139)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch13/config/exp13_01_a1.0_eikonal.yaml
    description: "CHK-136 baseline — Godunov reinit no ZSP, T=2"
  - path: experiment/ch13/config/exp13_01_a1.0_eikonal_zsp.yaml
    description: "CHK-137A — Zero-Set Protection band freeze"
  - path: experiment/ch13/config/exp13_01_a1.0_eikonal_xi.yaml
    description: "CHK-137B — ξ-SDF non-iterative, T=2 and T=10"
  - path: experiment/ch13/config/exp13_01_a1.0_eikonal_xi_t10.yaml
    description: "CHK-137B T=10 long run"
  - path: experiment/ch13/config/exp13_01_a1.0_eikonal_fmm.yaml
    description: "CHK-138 — Fast Marching Method, T=1 quick check"
  - path: experiment/ch13/config/exp13_01_a1.0_eikonal_xi_wideeps.yaml
    description: "CHK-139 T=1 — ξ-SDF with eps_scale=1.4"
  - path: experiment/ch13/config/exp13_01_a1.0_eikonal_xi_wideeps_t2.yaml
    description: "CHK-139 T=2 — ξ-SDF with eps_scale=1.4"
depends_on:
  - "[[WIKI-T-042]]: Eikonal unified reinitialization theory (CHK-136..139 root causes)"
  - "[[WIKI-E-027]]: DGR blowup + CHK-135 hybrid failure baseline"
  - "[[WIKI-E-015]]: §13 benchmark suite — Prosperetti capillary wave definition"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-18
---

# Eikonal/ZSP/ξ-SDF/FMM/ε-Widening: Prosperetti Benchmark Results (CHK-136..139)

All experiments use §13.1 Prosperetti (1981) capillary wave benchmark:
NX=NY=64, α=1.0 (uniform), ρ_l=10, ρ_g=1, σ=1.0, μ=0.05,
initial mode-2 perturbation with ε=0.05, radius=0.25.
Analytical solution: D(t) = D₀·exp(−βt)·cos(ω₀t), ω₀=6.824, β=0.048, D₀=0.05.
Targets: D(T=2) < 0.05, VolCons < 1%.

---

## CHK-136: Godunov Eikonal Baseline (n_iter=20, reinit_every=2)

**Config**: `exp13_01_a1.0_eikonal.yaml`, `reinit_method: eikonal`, T=2.

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| D(T=2) | 0.245 | < 0.05 | ✗ |
| VolCons max | 0.15% | < 1% | ✓ |
| Blowup | None | — | ✓ |

**Root cause** (WIKI-T-042 §CHK-136): Discrete Godunov sweep does not exactly preserve
the φ=0 contour. For cells near φ=0 with |∇φ_raw| < 1 (split-broadened interface
gives |∇φ| ≈ 1/1.4 after logit inversion):
```
phi -= dtau * sgn0 * (sqrt(Godunov) - 1)
≈ phi += dtau * (1 - 0.714) > 0  [for positive-phi cells near zero-set]
```
The φ=0 contour shifts ~dtau×0.286/h per iteration. Over 20 iter × every-2 × ~3700 steps
≈ 37000 total updates, systematic mode-2 correlation accumulates to D≈0.24.

---

## CHK-137A: Zero-Set Protection (ZSP)

**Config**: `exp13_01_a1.0_eikonal_zsp.yaml`, `reinit_method: eikonal` (with `zsp=True`), T=2.

| Metric | CHK-137A (ZSP) | CHK-136 (no ZSP) |
|--------|----------------|------------------|
| D(T=2) | 0.129 | 0.245 |
| VolCons max | 0.15% | 0.15% |

ZSP freezes cells with |φ₀| < h/2 during the Godunov sweep.
D improves 0.245→0.129 but does not pass the 0.05 target.
Residual drift from cells at h/2 < |φ| < 3h/2 which receive asymmetric
Godunov updates correlated with mode-2 geometry.

---

## CHK-137B: ξ-Space SDF (non-iterative)

**Config**: `exp13_01_a1.0_eikonal_xi.yaml`, `reinit_method: eikonal_xi`, T=2 and T=10.

Algorithm: zero-crossings located by linear interpolation → ξ-Euclidean distance field
(no iteration). Reconstruction: ψ = H_{ε_ξ}(φ_ξ), ε_ξ = ε/h_min.

### T=2 Result

| Metric | ξ-SDF | Target |
|--------|-------|--------|
| D(T=2) | 0.050 | < 0.05 |
| VolCons max | 1.46% | < 1% |

Borderline: D(T=2)=0.050 exactly at threshold, VolCons 1.46% marginally fails.

### T=10 Result

| Metric | ξ-SDF T=10 | Target |
|--------|------------|--------|
| D(T=10) | 0.226 | < 0.02 |
| VolCons max | 3.5% | < 1% |

Both targets fail at T=10.

### Static Mass Conservation Test

200 reinit calls on fixed circular interface (no advection): VolCons ≈ 0%.
→ **Per-call mass correction is exact**; drift is entirely from advection stage.

---

## CHK-138: Fast Marching Method (FMM)

**Config**: `exp13_01_a1.0_eikonal_fmm.yaml`, `reinit_method: eikonal_fmm`, T=1.

**Hypothesis being tested**: ξ-SDF's Voronoi kinks (C⁰ discontinuities) corrupt CCD
curvature → spurious surface tension → VolCons drift.

FMM produces C¹ SDF (Dijkstra priority-queue propagation, quadratic Godunov update):
```
if |ax − ay| < 1:    d = ½(ax + ay + √(2 − (ax − ay)²))
else:                d = min(ax, ay) + 1          ← caustic fallback (O(30%) error at 45°)
```

| Metric | FMM (T=1) | ξ-SDF (T=0.5) |
|--------|-----------|---------------|
| D | 0.024 | 0.008 |
| VolCons | **8.2%** ✗ | 0.8% |
| φ_xx std in band | 2.83 (lower) | 3.93 |

**Key finding**: FMM has *lower* second-derivative noise than ξ-SDF (2.83 vs 3.93)
but *worse* VolCons by 5×. This **directly refutes** the Voronoi kink hypothesis.

**Revised root cause** (WIKI-T-042 §CHK-138): Interface width effect.
- ξ-SDF, FMM: effective width ε → surface tension concentrated over O(ε) band
- PPE RHS = ∇·u* has large magnitude ~σκ/ρε → non-zero divergence residual
- ΔV/V₀ ≈ (Δt/ρ) ∫ψ ∇·u* dV grows with time
- Split-only's ~1.4ε interface diffuses surface tension → reduces PPE residual

FMM's extra VolCons penalty attributed to caustic fallback (d=1.5 at 45° vs Euclidean
√1.25≈1.12), creating grid-anisotropic ψ → larger PPE anisotropy.

---

## CHK-139: ξ-SDF with eps_scale=1.4 (Interface Widening)

**Configs**: `exp13_01_a1.0_eikonal_xi_wideeps.yaml` (T=1),
`exp13_01_a1.0_eikonal_xi_wideeps_t2.yaml` (T=2).
`reinit_method: eikonal_xi`, `reinit_eps_scale: 1.4`.

**Fix**: Set ε_eff = 1.4·ε in reconstruction (ψ = H_{1.4·ε_ξ}(φ_ξ)),
explicitly matching split-only's natural PDE-diffusion broadening.

### T=1 Result

| Metric | ξ-SDF+1.4 | ξ-SDF+1.0 | Target |
|--------|-----------|-----------|--------|
| D(T=1) | 0.018 ✓ | — | < 0.05 |
| VolCons | 0.802% ✓ | ~0.8% | < 1% |

T=1 passes both targets.

### T=2 Result

| Metric | ξ-SDF+1.4 | ξ-SDF+1.0 | split-only | Target |
|--------|-----------|-----------|------------|--------|
| D(T=2) | **0.028** ✓ | 0.050 ✓ | 0.037 ✓ | < 0.05 |
| VolCons t=0.5 | 0.794% | — | — | |
| VolCons t=1.0 | 0.778% | — | — | |
| VolCons t=1.5 | 0.678% | — | — | |
| VolCons t=2.0 | 1.384% | — | — | |
| VolCons max | 1.384% ✗ | 3.5%@T=10 | <1%@T=10 | < 1% |

VolCons oscillates non-monotonically with the capillary wave cycle (decreases t=0.5→1.5,
then rises at t=2.0), suggesting phase-coupled PPE residual fluctuations rather than
monotonic accumulation.

D(T=2)=0.028 is the best value among all methods including split-only (0.037).

### Summary Table (All Methods)

| Method | D(T=2) | VolCons | Status |
|--------|--------|---------|--------|
| Split only | 0.037 | <1%@T=10 ✓ | ✓ reference |
| DGR only | blowup | — | ✗ |
| Hybrid | 0.129 | low | ✗ D |
| Eikonal/ZSP (CHK-137A) | 0.129 | 0.15% | ✗ D |
| ξ-SDF f=1.0 (CHK-137B) | 0.050 | 1.46%@T=2 | borderline |
| FMM f=1.0 (CHK-138) | — | 8.2%@T=1 | ✗ |
| **ξ-SDF f=1.4 (CHK-139)** | **0.028** ✓ | **1.38%@T=2** | **partial ✓** |

---

## Open Questions

1. T=10 stability of ξ-SDF + eps_scale=1.4: not yet tested.
   VolCons extrapolation suggests ~3-4% at T=10 (sub-linear growth), but ε-widening
   may provide more stabilization at longer times due to reduced mode-2 accumulation.

2. Optimal eps_scale: f=1.4 was chosen to match split-only's diffusion broadening.
   f∈{1.5, 1.6} might further reduce VolCons at the cost of D precision.

3. FMM caustic branch fix: 8-connected stencil would remove the 20% distance error
   at 45°. This improves σ=0 accuracy (shape preservation) but limited benefit for
   σ>0 since root cause is interface width, not anisotropy.
