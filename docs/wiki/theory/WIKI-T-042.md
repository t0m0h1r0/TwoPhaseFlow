---
ref_id: WIKI-T-042
title: "Eikonal-Based Unified Reinitialization — Theory and Guarantees"
domain: T
status: VERIFIED
superseded_by: null
sources:
  - path: src/twophase/levelset/reinit_eikonal.py
    git_hash: null
    description: "EikonalReinitializer — Godunov upwind sweep + local-ε reconstruction"
  - path: paper/sections/07b_reinitialization.tex
    git_hash: null
    description: "§統一再初期化: Eikonal 法 subsection"
consumers:
  - domain: L
    description: "reinitialize.py — 'eikonal' method dispatch"
  - domain: E
    description: "exp13_01_a1.0_eikonal.yaml — Prosperetti benchmark verification (CHK-136)"
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

| Method | Zero-set | |∇φ|=1 | Local ε | σ>0 capillary | Cost (CCD solves) |
|--------|----------|---------|---------|---------------|-------------------|
| Split only | ✓ | ✗ (~1.4×) | ✗ | ✓ correct | 8 |
| DGR only | ✗ (folds) | ✓ | ✗ | ✗ blowup | 4 |
| Hybrid (split+DGR) | ✓ | ✓ | ✗ | ✗ wrong D(t) | 12 |
| **Eikonal (this)** | **✓** | **✓** | **✓** | **pending CHK-136** | **0** |

**Cost note**: Eikonal uses first-order finite differences only (no CCD solves).
n_iter=20 iterations on a 64×64 grid ≈ 20×4096 = 82k multiplications.
Compare: split (8 CCD solves) = 8×64 tridiagonal LU each axis.
Eikonal is approximately 3-5× cheaper than split.

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

## Implications and Future Directions

**Status**: Eikonal (n_iter=20, every-2) is equivalent to hybrid+φ-space on σ>0:
stable, VolCons good, but D(t) wrong.

**Potential fixes** (not yet implemented):
1. **Zero-set protection**: Don't update cells where |φ₀| < h/2.
   Eliminates zero-set drift exactly; preserves |∇φ|→1 correction for off-interface cells.
   Implementation: mask in `_godunov_sweep` skipping cells near the zero-set.
2. **Fewer iterations**: n_iter=5 vs 20 reduces per-call drift; may be enough for |∇φ| correction.
3. **Less frequent reinit**: every-20 instead of every-2; reduces accumulated drift but
   risks fold blowup (same tradeoff as hybrid in CHK-135 Set D experiments).
4. **Adaptive trigger**: Only reinit when ε_eff drifts >5% — naturally reduces call frequency.

## Assumptions

- Profile retains sigmoid form near interface (valid under DCCD advection)
- n_iter=20 provides |∇φ|→1 convergence within the band; however, each call introduces
  O(Δτ) discrete zero-set drift — 20 iterations is NOT sufficient to avoid accumulated
  drift over O(10³) reinit calls in σ>0 simulations
- Roll BC introduces negligible error for interfaces well inside the domain
- CFL for pseudo-time: Δτ = 0.5·h_min (stability condition for first-order upwind)
