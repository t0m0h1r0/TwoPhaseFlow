---
ref_id: WIKI-T-030
title: "Direct Geometric Reinitialization (DGR): Thickness-Preserving CLS Reinit with Mass Conservation"
domain: T
status: PROPOSED
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
depends_on:
  - "[[WIKI-T-007]]: CLS transport and reinitialization theory"
  - "[[WIKI-T-029]]: CLS error metric — φ-space comparison required"
tags: [CLS, reinitialization, thickness, SDF, mass-conservation, DGR]
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-09
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

## Cost Comparison

| Method | CCD solves per reinit |
|--------|----------------------|
| Compression-diffusion (n=4, 2D) | 8 |
| **DGR (2D)** | **4** |

## Assumptions

- Profile retains sigmoid form ψ ≈ H_{ε_eff}(φ) (valid under DCCD advection)
- |∇φ_true| ≈ 1 near interface (SDF property; holds for smooth interfaces)
- CCD gradient accuracy (O(h⁶)) ensures reliable normalization
