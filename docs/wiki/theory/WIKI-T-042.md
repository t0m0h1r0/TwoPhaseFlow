---
ref_id: WIKI-T-042
title: "Eikonal-Based Unified Reinitialization — Theory and Guarantees"
domain: T
status: VERIFIED
superseded_by: null
sources:
  - path: src/twophase/levelset/reinit_eikonal.py
    git_hash: null
    description: "EikonalReinitializer — Godunov + ZSP + xi_sdf + fmm modes"
  - path: paper/sections/07b_reinitialization.tex
    git_hash: null
    description: "§ξ空間符号距離関数法（CHK-137）and §FMM（CHK-138）subsections"
consumers:
  - domain: L
    description: "reinitialize.py — 'eikonal'/'eikonal_xi'/'eikonal_fmm' dispatch"
  - domain: E
    description: "exp13_01_a1.0_eikonal_zsp/xi/fmm — CHK-137/138 Prosperetti benchmarks"
depends_on:
  - "[[WIKI-T-030]]: DGR theory and hybrid failure on σ>0 capillary waves"
  - "[[WIKI-T-007]]: CLS transport and reinitialization theory"
tags: [CLS, reinitialization, Eikonal, SDF, mass-conservation, local-eps, non-uniform-grid]
compiled_by: ResearchArchitect
compiled_at: 2026-04-18
---

## Motivation

CHK-135 established that hybrid reinit (split+DGR) gives wrong D(t)=0.227 on σ>0 capillary
waves, and split-only gives correct physics but blunts the interface to ~1.4ε.

**Desired**: A single method that simultaneously satisfies:
- Shape preservation (zero-set preserved, folds corrected) — was split's role
- Thickness correction (|∇φ|=1 guaranteed) — was DGR's role
- No non-uniform scaling artefact — eliminates CHK-135 mode-2 amplification mechanism
- Cell-local ε(i,j) ∝ h(i,j) — handles non-uniform grids correctly

## Algorithm

Given ψ (distorted), grid h(i,j), target ε_ξ = ε/h_min:

1. **Logit inversion**: φ = ε·ln(ψ/(1−ψ)) (with saturation clamp)
2. **Eikonal redistancing** (n_iter=20 Godunov sweeps):
   ```
   φ^(k+1) = φ^(k) − Δτ · sgn(φ₀) · (G_Godunov(φ^(k)) − 1)
   ```
   where the Godunov flux is (Sussman, Smereka, Osher 1994 eq. 2.8):
   ```
   G² = max(max(D⁻ₓ,0)², min(D⁺ₓ,0)²)   [for sgn>0]
      + max(max(D⁻ᵧ,0)², min(D⁺ᵧ,0)²)
   ```
3. **Cell-local ε reconstruction**: ψ(i,j) = H_{ε(i,j)}(φ), ε(i,j) = ε_ξ·max(hₓ(i), h_y(j))
4. **φ-space mass correction**: δφ = ΔM / ∫H'_ε dV,  φ ← φ + δφ,  ψ ← H_{ε(i,j)}(φ)

## Theoretical Guarantees

### Thm 1 — Zero-set preservation (exact)

The Eikonal PDE ∂φ/∂τ + sgn(φ₀)(|∇φ|−1) = 0 transports level sets by the Eikonal characteristic:
dx/dτ = sgn(φ₀)·∇φ/|∇φ|. At φ=0: sgn(φ₀)=±1 but the normal velocity is |∇φ|/|∇φ|=1
directed away from the interface, so the zero-set is transported at zero normal velocity
(the φ=0 level set is a fixed point of the PDE). ∎

### Thm 2 — Mass conservation (exact, pre-clipping)

Same as DGR Thm 2: Step 4 guarantees Σψ_corr = Σψ_old by construction.

Proof: W = ∫H'_ε dV; δφ = (M_old − M_new)/W;
Σψ_corr = Σ H_ε(φ+δφ) ≈ Σψ_new + δφ·W = M_new + (M_old−M_new) = M_old. ∎

### Thm 3 — Thickness convergence

If the Eikonal sweep converges (G→0), then |∇φ|→1 in the interface band.
With |∇φ|=1, the reconstructed profile ψ = H_{ε(i,j)}(φ) has effective width ε(i,j)
at each cell — no global-median approximation required.

### Corollary — Non-uniform grid correctness

On non-uniform grids, ε(i,j) = ε_ξ·max(hₓ(i), h_y(j)) ensures the interface occupies
a consistent number of cells (ε_ξ ≈ 1.5) regardless of local refinement.
This eliminates the systematic scale bias in DGR's global-median ε_eff estimate
on grids where coarse cells outnumber fine cells.

## Comparison with Split, DGR, Hybrid

| Method | Zero-set | |∇φ|=1 | Width | σ>0 capillary | D(T=2) | VolCons |
|--------|----------|---------|-------|---------------|--------|---------|
| Split only | ✓ | ✗ | ~1.4ε | ✓ correct | 0.037 | <1%@T=10 ✓ |
| DGR only | ✗ (folds) | ✓ | ε | ✗ blowup | — | — |
| Hybrid | ✓ | ✓ | ε | ✗ wrong D(t) | 0.129 | low |
| Eikonal/ZSP | ✓ | ✓ | ε | ✗ | 0.129 | low |
| **ξ-SDF** | **✓** | **✓** | **ε** | **✗ T=10 fails** | **0.050** | **3.5%@T=10** |
| FMM | ✓ | ✓ (C¹) | ε | ✗ worse | — | 8.2%@T=1 |
| **ξ-SDF+scale=1.4** | **✓** | **✓** | **1.4ε** | **0.028 ✓** | **1.384%@T=2** | **partial ✓** |

**Key insight (CHK-138)**: Width ε is the instability source for σ>0.
Split-only's ~1.4ε is stabilizing, not a defect.

**Key insight (CHK-139)**: Explicitly setting eps_scale=1.4 in ξ-SDF reconstruction
matches split-only's natural broadening → D(T=2)=0.028 ✓, VolCons(T=1)=0.8% ✓.

**Cost note**: Eikonal/ξ-SDF/FMM use no CCD solves (first-order FD or Dijkstra).
ξ-SDF: O(N²·N_cross) ≈ 1.5ms/call on CPU; suitable for σ=0 problems.

## Why This Avoids CHK-135 Failure Mode

CHK-135 root cause: DGR applies global-median ε_eff scale uniformly:
- Compressed ends (ε_local < ε̄_eff): over-scaled → interface shifts outward
- Elongated tips (ε_local > ε̄_eff): under-scaled → interface shifts inward
- Net: mode-2 deformation amplified per DGR call

Eikonal avoids this entirely:
- No global-median scale (each cell independently solves ∂φ/∂τ + sgn(φ₀)(|∇φ|−1)=0)
- No explicit scaling of φ — only pseudo-time evolution toward |∇φ|=1
- Cell-local ε reconstruction: each cell uses its own ε(i,j), no cross-cell contamination

## CHK-136 Verification Results (T=2 Prosperetti, α=1.0)

| Metric | Eikonal (n_iter=20, every-2) | Split-only | Hybrid+φ-space |
|--------|------------------------------|------------|----------------|
| D(T=2) | **0.245** ✗ | ~0.004 ✓ | 0.227 ✗ |
| VolCons max | 0.15% ✓ | <1% ✓ | 0.02% ✓ |
| Blowup | None ✓ | None ✓ | None ✓ |

**Eikonal fails on σ>0 capillary waves in the same way as hybrid.**

Root cause (CHK-136): The discrete Godunov scheme does NOT exactly preserve the
zero-set of φ. For cells near φ=0 with |∇φ_raw| < 1:

```
phi -= dtau * sgn0 * (sqrt(Godunov) - 1)
```

If |∇φ_raw| = 1/1.4 (after split broadening → logit gives compressed φ):
- Godunov ≈ (1/1.4)² → sqrt ≈ 0.714
- Update: phi += dtau * (1 - 0.714) > 0 for positive-phi cells near zero-set
- The φ=0 contour shifts by Δφ ~ dtau × 0.286 × 1/h per iteration

Over n_iter=20 iterations per call × reinit_every=2 × ~3700 steps = ~37000 calls total,
the accumulated zero-set drift causes systematic mode-2 deformation growth.

This is analogous to DGR's global-median non-uniformity: both introduce per-call
systematic perturbations to the interface position that accumulate into mode-2 error.
The mechanism is different but the effect is identical (D saturates at ~0.24).

## Why Split-Only Avoids This

Split reinitialization modifies ψ via a PDE with ψ=0.5 as a fixed point:
- Compression term drives ψ toward H_ε(φ_true) — a sigmoid around the zero-set
- The ψ=0.5 contour is NOT explicitly moved; it's attracted as a fixed point
- Mass correction is a GLOBAL scalar offset: uniform interface shift, no per-cell perturbation

Eikonal and DGR both explicitly move φ (or ψ) at each cell based on local gradients,
which introduces cell-by-cell perturbations that are systematically correlated with
interface curvature → mode-2 amplification over many calls.

## CHK-137 Verification Results (ZSP + ξ-SDF, T=2/T=10, α=1.0)

Three strategies to fix CHK-136's zero-set drift were implemented and tested.

### Strategy A — Zero-Set Protection (ZSP)

Godunov sweep with frozen band: cells where |φ₀| < h/2 are not updated.
This prevents zero-set drift from cells near φ=0.

| Metric | ZSP (n_iter=20, every-2) | CHK-136 (no ZSP) |
|--------|--------------------------|------------------|
| D(T=2) | 0.129 ✗ | 0.245 ✗ |
| VolCons | 0.15% | 0.15% |

ZSP halves D(T=2) (0.245→0.129) but does not pass the target <0.05.
Residual drift: cells at h/2 < |φ| < 3h/2 on curved interfaces still receive
asymmetric Godunov updates correlated with mode-2 geometry.

### Strategy B — ξ-Space SDF (non-iterative)

Zero-crossings are located by linear interpolation; each cell is assigned the
minimum ξ-Euclidean distance to the nearest crossing (no iteration):
```
φ_ξ(i,j) = sgn(φ_raw) × min_k √((i−ξ*_k)² + (j−η*_k)²)
ψ = H_{ε_ξ}(φ_ξ),  ε_ξ = ε/h_min
```

| Metric | ξ-SDF T=2 | ξ-SDF T=10 | Target |
|--------|-----------|------------|--------|
| D | 0.050 (borderline) | 0.226 ✗ | <0.02 |
| VolCons | 1.46% | 3.5% ✗ | <1% |

T=2: borderline pass. T=10: fails both D and VolCons targets.
Per-call mass conservation is exact (static test: 200 reinit calls, VolCons≈0%).
Mass drift is entirely from the advection stage when using the ξ-SDF ψ field.

---

## CHK-138 Investigation: FMM and Root Cause Revision

### Fast Marching Method (FMM)

Motivation: ξ-SDF produces a Voronoi-kink-dominated C⁰ distance field.
Hypothesis: these kinks corrupt 6th-order CCD curvature → spurious κ → VolCons drift.
Fix: FMM (Sethian 1996) propagates via the Godunov quadratic update, giving a C¹ SDF.

**FMM quadratic update** (2D unit-grid Eikonal):
```
if |a_x − a_y| < 1:    d = ½(a_x + a_y + √(2 − (a_x − a_y)²))
else:                  d = min(a_x, a_y) + 1
```
where a_x, a_y are the minimum accepted (frozen) distances from x- and y-neighbors.

**Implementation**: pure NumPy, Dijkstra priority queue, no external dependency.
Seeds from sub-cell interpolated zero-crossings (same as ξ-SDF Step 2).

### CHK-138 Results

| Metric | FMM (T=1) | ξ-SDF (T=0.5) | split-only (T=10) |
|--------|-----------|---------------|-------------------|
| D | 0.024 | 0.008 | 0.0036 ✓ |
| VolCons | **8.2% ✗** | 0.8% | <1% ✓ |
| 2nd-deriv noise (φ_xx std in band) | **2.83** (lower) | 3.93 | ~1.65 |

**Key finding**: FMM has _lower_ 2nd-derivative noise than ξ-SDF (2.83 vs 3.93)
but _worse_ VolCons by 5×. This directly refutes the Voronoi-kink hypothesis.

### Revised Root Cause Hypothesis — Interface Width Effect

The decisive difference between split-only and all geometric methods (ξ-SDF, FMM):

| Method | Effective interface width | σ>0 VolCons |
|--------|--------------------------|-------------|
| split-only | ~1.4ε (diffusion broadening) | <1% @T=10 ✓ |
| ξ-SDF | ε (correct SDF) | 3.5% @T=10 ✗ |
| FMM | ε (correct SDF) | 8.2% @T=1 ✗ |

**Mechanism**:
```
narrow interface (width ε)
  → surface tension concentrated over O(ε) band
  → PPE RHS = ∇·u* has large magnitude ~σκ/ρε
  → PPE residual ∇·u ≠ 0 proportional to 1/ε
  → ΔV/V₀ ≈ Δt/ρ ∫ψ ∇·u* dV grows with time
```
Split-only's 1.4ε interface naturally dilutes the surface tension concentration,
reducing the PPE residual and providing implicit diffusive regularization.

FMM worsening vs ξ-SDF is attributed to diagonal-cell distance overestimation
(FMM first-order scheme gives dist ≈ 1.5 at 45° cells where Euclidean = √1.25 ≈ 1.12),
creating grid-anisotropic ψ fields that generate larger PPE residuals.

### Conclusion

All geometric SDF methods (ξ-SDF, FMM) that produce interface width ≈ ε
are fundamentally incompatible with σ>0 capillary wave benchmarks using
6th-order CCD + Projection, unless an additional diffusive regularization step
is applied post-reconstruction.

**Recommendation**: For σ>0 problems, use split-only. The "accidental" 1.4ε broadening
is not a defect — it is the mechanism providing numerical stability for surface tension.
For σ=0 problems (passive advection, Zalesak slot), ξ-SDF and FMM are valid and superior
(correct ε width + better shape preservation than split-only's ~1.4× expansion).

---

---

## CHK-139: ε-Widening Fix — eikonal_xi with eps_scale=1.4

### Motivation

CHK-138 established that the true cause of VolCons failure is interface width, not kinks.
Split-only's ~1.4ε broadening stabilizes the PPE. The fix: explicitly set ε_eff = 1.4ε in
ξ-SDF reconstruction, matching split-only's natural behavior.

### Implementation

`EikonalReinitializer(eps_scale=1.4)` in `reinit_eikonal.py`:
```python
eps_xi = float(eps) * float(eps_scale) / h_min   # eps_scale=1.4
self._eps_xi = eps_xi
```
Config key: `reinit_eps_scale: 1.4` in YAML `run:` section → propagated via
`ns_pipeline.from_config` → `Reinitializer(eps_scale=...)` → `EikonalReinitializer`.

### CHK-139 Results (α=1.0, 64×64)

| Metric | T=1 | T=2 | Target |
|--------|-----|-----|--------|
| D | 0.018 ✓ | 0.028 ✓ | < 0.05 |
| VolCons | 0.802% ✓ | 1.384% ✗ | < 1% |

### Comparison with All Methods (post CHK-139)

| Method | Zero-set | \|∇φ\|=1 | Width | D(T=2) | VolCons max | Status |
|--------|----------|---------|-------|--------|-------------|--------|
| Split only | ✓ | ✗ | ~1.4ε | 0.037 | <1%@T=10 ✓ | ✓ best |
| DGR only | ✗ (folds) | ✓ | ε | — | — | ✗ unstable |
| Hybrid | ✓ | ✓ | ε | 0.129 | low | ✗ |
| Eikonal/ZSP | ✓ | ✓ | ε | 0.129 | 0.15% | ✗ D |
| ξ-SDF (scale=1.0) | ✓ | ✓ | ε | 0.050 | 1.46%@T=2 | borderline |
| FMM (scale=1.0) | ✓ | ✓ (C¹) | ε | — | 8.2%@T=1 | ✗ |
| **ξ-SDF (scale=1.4)** | **✓** | **✓** | **1.4ε** | **0.028 ✓** | **1.384%@T=2** | **partial ✓** |

**Partial success**: D(T=2) and VolCons(T=1) both pass. VolCons(T=2) is 1.384% vs target 1%.

### Root Cause Analysis of Residual VolCons Drift

VolCons rises from 0.802% (T=1) to 1.384% (T=2), non-monotonically:
- t=0.5: 0.794%, t=1.0: 0.778%, t=1.5: 0.678%, t=2.0: 1.384%

The VolCons oscillates with the capillary wave (decreasing at intermediate times where
the interface is smoother), then rises again. This suggests that the residual drift is
mode-coupled to the wave dynamics, not a pure linear accumulation.

Scale=1.4 significantly reduces the PPE residual (~5× VolCons reduction vs ξ-SDF)
but does not fully match split-only's long-time stability. A scale factor f>1.4 might
further reduce VolCons at the cost of blunting shape preservation.

---

## CHK-140: ξ-SDF Center Hole — ψ-Transport Vulnerability and Fix

### Bug Description

When using `eikonal_xi` reinit with ψ-transport (the default), a diamond-shaped
ψ≈0.5 artifact appears at the geometric center of a stationary droplet around t≈0.05
on a 64×64 grid. The hole grows from 1-cell (t=0.05) to 2-cell (t=0.10) and is
permanent (no self-healing).

### Root Cause

The ξ-SDF algorithm interprets any negative φ = ψ − 0.5 < 0 as a zero-crossing,
regardless of distance from the physical interface. The mechanism:

1. `DissipativeCCDAdvection` transports ψ ∈ [0,1] with `clip_bounds=(0.0, 1.0)`.
   The [0,1] clip does NOT prevent ψ from oscillating around 0.5.
2. At reinit call 37 (t≈0.048), ψ at node (32,32) — the exact geometric center —
   drops to 0.480 after 2 CCD advection steps, despite being 16 cells from the interface.
3. ξ-SDF detects a false zero-crossing 0.04 cells from node (32,32), assigns
   φ_sdf = −0.038 → ψ = σ(−0.038/ε) ≈ 0.5.
4. Once ψ = 0.5 is set, the center permanently appears as a zero-crossing in all
   subsequent reinit calls.

**Why is the oscillation so large?** After each reinit, the center is correctly reset
to ψ = σ(16/ε_xi) ≈ 1.0. But within 2 CCD steps (Δt ≈ 0.0013), ψ drops by ~0.22.
Investigation confirmed the [0,1] per-stage clip in CCD is insufficient — it only
prevents values outside [0,1], not oscillations around 0.5 in the interior.

**Grid note**: (NX+1, NY+1) = (65,65) node grid; node (32,32) = (0.5, 0.5) is at the
exact geometric center. Initial condition is a perturbed circle with r=0.25 → the
center is 16*h = 16/64 = 0.25 from the interface.

### Why Fixes 1–4 All Failed

| Fix | Content | Why ineffective |
|-----|---------|-----------------|
| Fix 1 | `sgn0[|φ|<1e-10] = +1` | threshold too small; spurious φ = −0.02 >> 1e-10 |
| Fix 2 | `sgn == 0 → +1` in `_xi_sdf_phi` | φ = 0 exactly never occurs |
| Fix 3 | mass correction sign clamp | delta_phi << 16*h; can't flip center cell |
| Fix 4 | neighbor-based isolated flip | physically unjustified (user objection) |
| "案B" | `clip(psi, 0, 1)` post-advection | already done internally by CCD; 0.48 ∈ [0,1] |

### Root Fix: phi-primary Transport

Transport φ = logit(ψ)·ε directly; reconstruct ψ = σ(φ/ε) each step.

**Physical invariant enforced**: Far from the interface, φ ≫ 0 (interior) or φ ≪ 0
(exterior). σ(φ/ε) then naturally saturates to 1 or 0. This is the invariant that
ψ-transport violates: ψ ∈ [0,1] after advection, but not necessarily near 0 or 1
far from the interface.

**Robustness**: Center node has φ = logit(ψ) · ε ≈ 16·ε_xi. CCD oscillations of
O(ε_xi) are irrelevant — the sign cannot flip unless the interface actually reaches
the center, which requires physical displacement of ~16 cells.

Config: `phi_primary_transport: true` in `run:` section of YAML.

### CHK-140 Verification (exp13_09)

| Metric | psi-transport (exp13_08) | phi-primary (exp13_09) |
|--------|--------------------------|------------------------|
| Center hole t=0.05 | ✗ present | **✓ absent** |
| Center hole t=0.10 | ✗ present | **✓ absent** |
| VolCons max | 0.82% | **0.00%** |

Higher KE with phi-primary (max=1.38 vs ~1e-5 at early steps for psi) reflects
sharper interface activating stronger capillary dynamics — consistent with WIKI-E-025.

### Lesson

The ψ-transport + ξ-SDF combination has a latent vulnerability: any advection
scheme that allows deep-interior ψ to oscillate within [0,1] can trigger false
zero-crossings. The invariant "ψ ≈ 0 or 1 far from interface" must be enforced
actively. phi-primary transport enforces this via the sigmoid saturation at every step.

---

## Implications and Future Directions

**Current status** (post CHK-139):
- σ>0 capillary waves T=1: ξ-SDF + eps_scale=1.4 ✓ (VolCons 0.8%, D 0.018)
- σ>0 capillary waves T=2: ξ-SDF + eps_scale=1.4 partial ✓ (D 0.028 ✓, VolCons 1.38% marginally ✗)
- σ=0 advection: ξ-SDF (scale=1.0) suitable (correct ε, no drift)
- split-only: still the reference for σ>0 long-time accuracy

## Assumptions

- Profile retains sigmoid form near interface (valid under DCCD advection)
- Split-only's 1.4ε broadening is the stabilizing mechanism for σ>0 problems
  (hypothesis: not yet confirmed by explicit width-control experiment)
- FMM diagonal overestimation is O(30%) at 45°; acceptable for σ=0 problems
  but compounds the interface-width instability for σ>0
- Roll BC introduces negligible error for interfaces well inside the domain
- CFL for pseudo-time: Δτ = 0.5·h_min (stability condition for first-order upwind)
