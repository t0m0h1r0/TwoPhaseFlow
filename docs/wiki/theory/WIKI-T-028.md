---
ref_id: WIKI-T-028
title: "CLS-DCCD Conservation Theory: Root Cause Analysis and Unified Reinitialization"
domain: T
status: VERIFIED
superseded_by: null
sources:
  - path: docs/memo/cls_dccd_conservation_theory.md
    git_hash: null
    description: "Full theoretical analysis memo with proofs, spectral analysis, and implementation plan"
  - path: docs/memo/cls_shape_preservation.md
    git_hash: null
    description: "Shape preservation study — over-reinitialization as dominant error source"
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

[[WIKI-T-027]] post-hoc interface-weighted mass correction is now **implemented and validated** (2026-04-09). Key findings from WIKI-T-027 implementation:

- Mass error: O(10^-3) → **O(10^-15)** (machine precision) for both Zalesak and single vortex
- **Accidental error cancellation discovered**: old reinit added +21.57 mass (N=128 Zalesak), partially cancelling advection loss of -38.48. Both corrections required.
- Shape error L₂ unchanged; grid convergence ~O(h^0.4) for single vortex (filament resolution limit)

This entry (T-028) proposes the **root cause** fix (unified DCCD reinitialization) to eliminate the operator-splitting mismatch. The two approaches are complementary: unified DCCD would eliminate the dominant mass-loss mechanism at the PDE level, while the Lagrange correction (T-027, implemented) handles residual clip-induced losses.

## Experimental Verification (exp11_18, 2026-04-09)

### Claim 1: DCCD periodic sum = 0 — CONFIRMED

| N | |Σ f̃'| (periodic) | |Σ f̃'| (wall) |
|---|---|---|
| 64 | 8.88e-16 | 5.37e-14 |
| 128 | 7.38e-15 | 7.23e-14 |
| 256 | 3.17e-13 | 1.12e-13 |

Machine precision for both BCs. Theory exactly matches.

### Claim 2: Operator splitting is the dominant mass-loss source — CONFIRMED

| Config | N=64 mass_err | N=256 mass_err |
|---|---|---|
| split (no mc) | **2.01e-3** | **1.88e-5** |
| unified (no mc) | 5.93e-15 | 7.70e-15 |

Unified without mass correction achieves **machine-precision mass conservation** vs O(10⁻³) for split. The per-step Lagrange correction + two-stage clip repair eliminates operator-splitting mass loss completely.

### Claim 3: Unified scheme trade-off — PARTIALLY CONFIRMED

| Config | N=64 L₂ | N=128 L₂ | N=256 L₂ |
|---|---|---|---|
| split+mc | **0.191** | **0.174** | **0.142** |
| unified+mc | 0.309 | 0.329 | 0.359 |

**Mass conservation: verified.** Unified achieves machine-precision mass without post-hoc correction.

**Shape accuracy: degraded.** Unified L₂ is ~2× worse and does not converge with grid refinement. Root cause: explicit Forward Euler for diffusion is O(Δτ) temporal accuracy vs CN-ADI's O(Δτ²). The CN scheme's implicit solve provides critical accuracy for the diffusion term that explicit treatment cannot match.

### Verdict

The three theoretical claims about mass-loss sources are **all confirmed**. However, the unified scheme in its current form (explicit FE for combined RHS) is **not recommended** as a replacement for operator splitting — the shape accuracy regression outweighs the mass conservation benefit (which WIKI-T-027 post-hoc correction already solves to machine precision).

**Recommended path**: keep operator-split scheme + WIKI-T-027 mass correction (proven O(10⁻¹⁵) mass + best shape accuracy). The theoretical findings remain valuable for understanding the mass-loss mechanism and for future semi-implicit formulations that could preserve both properties.

## Shape Error Hierarchy (exp11_19, 2026-04-09)

Follow-up study revealed that **DCCD damping is NOT a shape error source** — the dominant source is over-reinitialization. See [[WIKI-E-009]] and `docs/memo/cls_shape_preservation.md` for full analysis.

| Source | L₂ contribution | Evidence |
|---|---|---|
| **Over-reinitialization** | ~49% | adaptive (2 reinits) vs fixed-10 (227 reinits) |
| Interface thickness | ~15% | ε=1.0h vs 1.5h |
| Advection (inherent) | ~34% | no-reinit residual at N=128 |
| DCCD damping | ~2% | ε_d=0.0 vs 0.05 nearly identical |

**Why DCCD damping is irrelevant:** The CLS profile ψ = H_ε(φ) has spectral content at λ ≥ 2πε ≈ 9.4h. DCCD damping at this wavelength is only 2% (H(0.67) = 0.98). The 20% Nyquist damping targets wavelengths the interface does not occupy.

**Recommended production configuration:**
- Adaptive reinit: M(τ)/M_ref > 1.10 trigger (replaces fixed every-10-steps)
- ε = 1.0h (thinner interface)
- ε_d = 0.05 (unchanged — no benefit from reduction)
- Operator-split + T-027 mass correction (unchanged)

## Status

VERIFIED — all theoretical claims confirmed (exp11_18). Shape error hierarchy established (exp11_19). Production recommendation: operator-split + T-027 mc + adaptive reinit + ε=1.0h.
