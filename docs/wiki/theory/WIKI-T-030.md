---
ref_id: WIKI-T-030
title: "Operator-Split Defect, DGR Theory, and Hybrid Reinitialization"
domain: T
status: VERIFIED
superseded_by: null
sources:
  - path: docs/memo/direct_geometric_reinit.md
    git_hash: null
    description: "Full derivation with 3 theorems and proofs"
  - path: src/twophase/levelset/heaviside.py
    git_hash: null
    description: "invert_heaviside — logit extraction with saturation clamp"
consumers:
  - domain: L
    description: "reinitialize.py — new DGR method to replace compression-diffusion"
  - domain: E
    description: "exp11_6, exp11_20 — thickness maintenance validation"
  - domain: E
    description: "WIKI-E-027 — DGR blowup isolation experiments confirming fold cascade mechanism"
depends_on:
  - "[[WIKI-T-007]]: CLS transport and reinitialization theory"
  - "[[WIKI-T-029]]: CLS error metric — φ-space comparison required"
tags: [CLS, reinitialization, thickness, SDF, mass-conservation, DGR]
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-18
---

## Key Finding

Current compression-diffusion reinitialization (n_steps=4) fails to maintain interface thickness: ε_eff ≈ 3ε_target after T/4. Direct Geometric Reinitialization (DGR) restores thickness in **one step** via logit inversion + gradient normalization, with **provable mass conservation**.

## Algorithm

Given ψ (distorted), target ε:

1. **Logit inversion**: φ_raw = ε · ln(ψ/(1−ψ)) (with saturation clamp)
2. **Gradient normalization**: φ_sdf = φ_raw / |∇φ_raw| (CCD gradient, safety floor g_min=0.1)
3. **Reconstruction**: ψ_new = H_ε(φ_sdf) = 1/(1+exp(−φ_sdf/ε))
4. **Mass correction**: ψ_corr = ψ_new + (δM/W)·4ψ_new(1−ψ_new)

## Theoretical Guarantees

### Thm 1 — Thickness restoration (exact)

If ψ = H_{ε_eff}(φ_true) with |∇φ_true|=1, then Steps 1–3 yield ψ_new = H_ε(φ_true).

Proof: φ_raw = (ε/ε_eff)·φ_true, |∇φ_raw| = ε/ε_eff, φ_sdf = φ_true. ∎

### Thm 2 — Mass conservation (exact, pre-clipping)

Σψ_corr = Σψ_old.

Proof: Σψ_corr = Σψ_new + δM = Σψ_old. ∎

### Thm 3 — Profile-preserving correction

The mass correction ≈ uniform interface shift Δφ = 4λε; does not change thickness.

Proof: w = 4ψ(1−ψ) = 4ε·(∂ψ/∂φ), so ψ + λw ≈ H_ε(φ + 4λε). ∎

### Corollary — ε_inv independence

The inversion ε cancels in Step 2: φ_sdf = φ_true regardless of ε used in Step 1.

## Operator-Split Defect (discovered 2026-04-09)

Comp-Diff reinit broadens interface by ~40% per call on a **perfect static profile**:
1 call → ε_eff/ε = 1.40, 89 calls → 3.98. Cause: sequential compression (FE) then
diffusion (CN-ADI) — compression sharpens to ε' < ε, diffusion overshoots to ε'' > ε.
n_steps increase worsens it (more splitting iterations).

## Hybrid Scheme (recommended)

    hybrid_reinit(ψ) = DGR(comp_diff_reinit(ψ))

Comp-Diff provides shape restoration (profile → tanh form).
DGR corrects the ~1.4× broadening back to ε.

Result (Zalesak N=128, ε/h=1.0, every-20):
- ε_eff/ε = 1.02 (vs 4.01 Comp-Diff, 0.99 DGR)
- Area error = 1.46e-3 (**5× better** than Comp-Diff 7.00e-3)

## Cost Comparison

| Method | CCD solves per reinit |
|--------|----------------------|
| Compression-diffusion (n=4, 2D) | 8 |
| DGR (2D) | 4 |
| **Hybrid (2D)** | **12** |

## Limitations — DGR Alone Fails for σ>0 Capillary Dynamics (discovered 2026-04-18)

**DGR corrects interface THICKNESS only — not SHAPE.**  Under σ>0 capillary wave
dynamics (e.g., exp13_01), the advected ψ field develops **interface folds**:
regions where |∇ψ|→0 inside the band (0.05<ψ<0.95).  A fold means ψ has a local
extremum within the interface — physically an interface self-intersection or crease.

**Why DGR fails to detect folds**: The median-based ε_eff estimate is robust to
outliers.  Fold cells (|∇ψ|→0 → ε_local→∞) are outliers in the band — the median
is unaffected.  DGR computes scale≈1 and returns ψ_new≈ψ — effectively a no-op.

**Cascade mechanism** (confirmed by isolation experiments, exp13_01 α=1.0):

1. Capillary advection creates fold in band at step ~62 (|∇ψ|_min→0)
2. DGR: median ε_eff unchanged → scale≈1 → fold not repaired
3. CCD Laplacian over fold → unphysical κ (curvature) spike
4. CSF force σ·κ·δ·∇ψ → exponential KE growth → blowup (t<0.2, KE>1e6)

**Isolation experiments**:

| Exp | Change | Result |
|---|---|---|
| A1 | no reinit | BLOWUP step=114 (fold forms regardless) |
| A2 | hybrid reinit | **STABLE** T=10 — split corrects fold shape |
| A3 | σ=0 + DGR | **STABLE** — confirms CSF as amplification mechanism |
| A4 | DGR every-20 | BLOWUP step=100 (frequency doesn't fix the root cause) |

**Conclusion (CHK-133)**: For any simulation with σ>0 where the interface can fold,
**use hybrid, not DGR alone**.  DGR alone is safe only for σ=0 or as post-split cleanup.

## Limitations — Hybrid Reinit Also Fails for σ>0 Capillary Waves (discovered 2026-04-18, CHK-135)

**Hybrid reinit (split+DGR) prevents hard blowup but gives wrong physics.**
After fixing the DGR blowup with hybrid reinit (CHK-133), the 2D results show:

- α=1.0, hybrid every-2: D(t) saturates at 0.226 (should decay to ~0 per Prosperetti)
- α=1.0, split-only every-2: D_final=0.0036 (correct ✓)

**Root cause — DGR global-median sharpening is non-uniform on curved interfaces:**

After split reinit (ε_eff ≈ 1.4ε), DGR sharpens using global median scale:
- Compressed ends (|∇ψ| large → ε_local small): over-scaled → interface shifts outward
- Elongated tips (|∇ψ| small → ε_local large): under-scaled → interface shifts inward
- Net: mode-2 deformation amplified per DGR call

**This is the sharpening step itself, not the mass correction.**
Confirmed by implementing φ-space mass correction (CHK-135, 2026-04-18):
```
δφ = ΔM / ∫H'_ε dV    (replaces ψ-space λ·4q(1-q) correction)
```
Result: VolCons=0.02% (fixed) but D_final=0.227 (unchanged). The sharpening is the cause.

**Frequency sensitivity experiments** (Set D, CHK-135, α=1.0 hybrid):

| Config | reinit_every | t_blowup | D_final | VolCons | Conclusion |
|---|---|---|---|---|---|
| every-2 (ψ-space) | 2 | — | 0.226 | 347% | Wrong physics + mass injection |
| every-2 (φ-space) | 2 | — | 0.227 | 0.02% | Wrong D(t); VolCons fixed |
| every-20 | 20 | 0.102 | — | — | BLOWUP (fold not prevented) |
| every-500 | 500 | 0.043 | — | — | BLOWUP (fold at step~62) |
| split-only | 2 | — | 0.003 | <1% | **Correct ✓** |

No sweet spot for hybrid: too infrequent → blowup; too frequent → wrong D(t) regardless of mass correction method.

**Why split-only works and hybrid does not:**
- Split-only: mass correction is a GLOBAL uniform offset applied once; no per-cell scaling. Interface broadens to ~1.4ε but this does not distort the zero-set shape.
- Hybrid: DGR applies CELL-WISE scale (global median ε_eff) followed by φ-space correction. Even with φ-space correction, the sharpening itself is non-uniform on curved interfaces → zero-set shifts non-uniformly → mode-2 amplified.

**Current status**: For σ>0 capillary wave decay (Prosperetti benchmark):
1. DGR alone: BLOWUP (fold blowup, CHK-133)
2. Hybrid+ψ-space: stable but WRONG D(t) + mass injection (3-4× VolCons)
3. Hybrid+φ-space: stable, correct VolCons, but WRONG D(t) (mechanism not fully resolved)
4. **Split-only: CORRECT physics** ← pragmatic fix for ch13 §13.1

**Open problem:** Why hybrid+φ-space still gives wrong D(t) is not fully understood.
Theoretically, DGR sharpening preserves the ψ=0.5 zero-set (ε̄_eff/ε_local > 0 always),
and φ-space correction adds uniform shift. Candidate mechanism: non-uniform interface
thickness after sharpening (∝ ε_local/ε̄_eff) → spatially non-uniform CSF force →
spurious mode-2 driving. Full theoretical explanation pending.

**Applicability of hybrid/DGR:**
- Zalesak, passive advection, σ=0 rising bubble → hybrid appropriate (static/low curvature)
- σ>0 high-curvature capillary dynamics → split-only (DGR adds spurious energy)
- DGR is NOT discarded; it is correct for the cases it was designed for.

**Future directions (not yet implemented):**
- Per-band-cell DGR: apply local ε_eff(i,j) only within interface band; keep bulk unchanged.
  Avoids bulk amplification (Set C failure) while correcting non-uniform thickness.
- Adaptive DGR trigger: call DGR only when ε_eff drifts >5% from ε_target.
  Reduces call frequency; may reduce accumulated shape error for curved interfaces.

## Assumptions

- Profile retains sigmoid form ψ ≈ H_{ε_eff}(φ) (valid under DCCD advection)
- |∇φ_true| ≈ 1 near interface (SDF property; **broken by folds under σ>0**)
- CCD gradient accuracy (O(h⁶)) ensures reliable normalization
- DGR correction is small (~1.4×) after one Comp-Diff call → median ε_eff estimate accurate
