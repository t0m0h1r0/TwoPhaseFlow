---
ref_id: WIKI-T-028
title: "CLS-DCCD Conservation Theory: Root Cause Analysis and Unified Reinitialization"
domain: T
status: PROPOSED
superseded_by: null
sources:
  - path: docs/memo/cls_dccd_conservation_theory.md
    git_hash: null
    description: "Full theoretical analysis memo with proofs, spectral analysis, and implementation plan"
  - path: src/twophase/levelset/advection.py
    git_hash: null
    description: "DissipativeCCDAdvection — DCCD advection (periodic sum property verified)"
  - path: src/twophase/levelset/reinitialize.py
    git_hash: null
    description: "Reinitializer — operator-split scheme (root cause of mass loss)"
consumers:
  - domain: L
    description: "reinitialize.py — target for unified DCCD reinitialization"
  - domain: E
    description: "exp11_6 — validation target (mass error < 1e-3 at reinit_freq=1)"
depends_on:
  - "[[WIKI-T-002]]: DCCD filter theory (transfer function, spectral properties)"
  - "[[WIKI-T-007]]: CLS transport and reinitialization theory"
  - "[[WIKI-T-027]]: Post-hoc mass correction (symptom-level fix, superseded by this analysis)"
tags: [CLS, DCCD, mass-conservation, reinitialization, operator-splitting, Lagrange-multiplier]
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-09
---

## Key Finding

**DCCD does NOT break mass conservation for periodic BC.** The CCD block-circulant system produces Σ d1 = 0 (exact), and the DCCD second-difference filter preserves this (telescoping). The observed mass loss has three distinct sources, none of which is the DCCD spatial operator itself.

## Three Actual Mass-Loss Sources

### S1. clip(ψ, 0, 1) — Primary in advection

DCCD has no TVD guarantee. Overshoots/undershoots after each RK3 stage are clipped away without mass redistribution. This is the **sole** mass-loss source for periodic advection.

### S2. Operator-Splitting Mismatch — Primary in reinitialization

The reinitialization equilibrium identity:

```
ψ(1-ψ)n̂ = ε∇ψ   →   ∇·[ψ(1-ψ)n̂] = ε∇²ψ
```

Current scheme computes LHS with DCCD (CCD d1 + filter) and RHS with CN-ADI (CCD d2, no filter). **Different discrete operators break the equilibrium**: at the steady-state profile, the discrete LHS ≠ RHS, creating a non-zero residual that drives ψ away from equilibrium and loses mass. Spectral signature: compression is damped by H(kh; εd) at high-k, diffusion is unfiltered.

### S3. Hardcoded Neumann Padding — Moderate

`reinitialize.py:155` hardcodes `'neumann'` for the DCCD filter padding even when the CCD solver uses periodic BC. This breaks the telescoping sum property (Σ f̃' ≠ 0).

## Proof: DCCD Periodic Sum = 0

1. **CCD sum**: Periodic CCD RHS uses antisymmetric (d1) and symmetric (d2) stencils, both summing to zero. The non-singular 2×2 block system forces Σ d1 = Σ d2 = 0.
2. **Filter sum**: Σ[d1 + εd·Δ(d1)] = Σd1 + εd·Σ(d1[i+1] − 2d1[i] + d1[i−1]) = 0 + 0 = 0.

## Proposed Fix: Unified DCCD Reinitialization

Replace operator splitting with unified explicit RHS:

```
C = D_DCCD[ψ(1-ψ)n̂]              (compression, existing DCCD)
D = ε · Σ_ax ψ''_ax               (diffusion, CCD d2 from same call)
R = -C + D                         (combined, no splitting)
R̂ = R - (ΣR / Σw) · w             (Lagrange conservation correction, w=4ψ(1-ψ))
ψ^new = clip(ψ + Δτ·R̂, 0, 1)      (update + clip)
+ post-clip mass repair             (two-stage correction)
```

### Properties

| Property | Status | Mechanism |
|----------|--------|-----------|
| Equilibrium fixed point | **Preserved** | Same CCD input at equilibrium → same output → R = 0 |
| Discrete mass conservation | **Exact** (pre-clip) | Σ R̂ = 0 by construction |
| Post-clip mass repair | **Exact** | Two-stage interface-weighted correction |
| CFL penalty | **Zero** | Current Δτ already at parabolic CFL; CN stability was not exploited |
| Computational cost | **Reduced** | Eliminates CN-ADI Thomas sweeps; ψ'' reused from gradient computation |

### Downstream Impact

All downstream processes (curvature, HFE, CSF, material properties, PPE) benefit or are unaffected. No adverse effects identified. Key improvements: better equilibrium profile → less parasitic currents; better mass conservation → improved NS mass balance.

## Relation to WIKI-T-027

[[WIKI-T-027]] proposed post-hoc interface-weighted mass correction (now implemented). This entry addresses the **root cause** (operator-splitting mismatch) rather than the symptom (mass drift). The two approaches are complementary: unified DCCD eliminates the dominant mass-loss mechanism, while the Lagrange correction handles residual clip-induced losses.

## Status

PROPOSED — theoretical analysis complete, implementation pending. See full derivations and proofs in `docs/memo/cls_dccd_conservation_theory.md`.
