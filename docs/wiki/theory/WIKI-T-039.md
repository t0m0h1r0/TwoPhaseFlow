---
ref_id: WIKI-T-039
title: "ξ-Space CCD Metric Limitation: Under-Resolution Impossibility for Localized Grids"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: "src/twophase/ccd/ccd_solver.py"
    description: "_apply_metric: d2_x = J²·d2_ξ + J·dJ·d1_ξ (cross-term formula)"
  - path: "src/twophase/core/metrics.py"
    description: "J and dJ/dξ computation — CCD O(h^6) or FD O(h^2)"
  - path: "src/twophase/tests/test_ccd.py"
    description: "MMS characterization tests for non-uniform d1/d2"
consumers:
  - domain: E
    usage: "Explains why non-uniform grid accuracy cannot be improved by formula changes alone"
  - domain: T
    usage: "Establishes that Approach A (direct non-uniform CCD) is the required path"
depends_on:
  - "[[WIKI-T-037]]"
  - "[[WIKI-T-038]]"
  - "[[WIKI-T-001]]"
compiled_by: ResearchArchitect
verified_by: MMS experiment (test_ccd.py::test_nonuniform_d2_bounded)
compiled_at: 2026-04-17
---

# ξ-Space CCD Metric Limitation

## 1. Problem Statement

The CCD solver operates on a uniform computational grid (ξ-space, spacing h = 1/N)
and converts to physical space via metric transform:

    df/dx   = J · df/dξ
    d²f/dx² = J² · d²f/dξ² + J · (dJ/dξ) · df/dξ     ... (§4.9)

For interface-fitted grids with Gaussian density ω(φ) = 1 + (α−1)·exp(−φ²/ε_g²),
the metric J = dξ/dx varies rapidly near the interface.

**Question**: Can a different algebraic formula for d²f/dx² (e.g., Two-Pass)
eliminate the accuracy loss on localized grids?

**Answer**: No. The root cause is ξ-space under-resolution of J, not the
algebraic form of the conversion formula.

## 2. Two-Pass Approach (Tested and Disproven)

### Theory

Replace the cross-term formula with a two-step composition:

    Pass 1: g = J · f_ξ  (= df/dx, physical first derivative)
    Pass 2: CCD(g, ξ) → g_ξ, then d²f/dx² = J · g_ξ

This avoids the explicit cross-term J·(dJ/dξ)·f_ξ.

### Formal Analysis

Algebraically, this is exact: g_ξ = d(df/dx)/dξ and J · g_ξ = d²f/dx².
However, the accuracy depends on CCD's ability to differentiate g in ξ-space.

The function g(ξ) = J(ξ) · f_ξ(ξ) inherits the rapid variation of J(ξ).
When ε_g = eps_g_factor × ε and eps_ratio = 0.5:

    Transition width in ξ-cells = ε_g × N = eps_g_factor × eps_ratio = 1.0

**g varies over ~1 cell in ξ-space** — exactly as under-resolved as J itself.

### MMS Verification

f(x) = sin(πx), d²f/dx² = −π²sin(πx), alpha=2, eps_g_factor=2:

| N    | d2 Two-Pass err | d2 old formula err | transition cells |
|------|----------------:|-------------------:|-----------------:|
|  16  |       2.47e-01  |         2.96e-01   |             1.0  |
|  32  |       2.33e-01  |         2.86e-01   |             1.0  |
|  64  |       2.30e-01  |         2.83e-01   |             1.0  |
| 128  |       2.29e-01  |         2.83e-01   |             1.0  |

**Neither converges.** Both saturate at O(0.2-0.3) because J is under-resolved.

With eps_g_factor scaling proportional to N (8 cells fixed):

| N    | egf  | d2 Two-Pass err | d2 old formula err |
|------|------|----------------:|-------------------:|
|  16  |  2.0 |       2.47e-01  |         2.96e-01   |
|  32  |  4.0 |       3.36e-02  |         3.15e-02   |
|  64  |  8.0 |       1.29e-02  |         7.68e-03   |
| 128  | 16.0 |       2.50e-02  |         1.51e-02   |

When the transition is well-resolved, the old formula is **better** than Two-Pass
(it uses one CCD solve vs two, accumulating less discretization error).

## 3. Root Cause: Fixed ξ-Space Transition Width

The density function's Gaussian profile has physical width ε_g:

    eps_g = eps_g_factor × eps = eps_g_factor × eps_ratio × h

In ξ-space (uniform spacing dξ = 1/N):

    transition_cells = eps_g / dξ = eps_g × N = eps_g_factor × eps_ratio

With eps_g_factor=2, eps_ratio=0.5: **transition = 1 cell regardless of N**.

This is the fundamental impossibility:

1. Any CCD stencil (uniform or two-pass) needs ~4+ cells to resolve a function
2. J transitions over 1 cell in ξ-space (fixed by eps_g_factor)
3. Increasing N does NOT help — the transition stays at 1 cell
4. Any formula involving J (cross-term, two-pass, or any composition) inherits
   this under-resolution

## 4. What DOES Help (Scaling eps_g_factor with N)

If eps_g_factor scales with N (keeping transition at K cells):

    eps_g_factor(N) = K / eps_ratio = 2K

With K=8 cells, egf=16 for N=128. This makes dJ/dξ = O(1) and both
formulas converge. But this eliminates the localization benefit — the
fine-grid region spans K/N = 8/128 = 6% of the domain.

The trade-off: accuracy ↔ localization. No formula change resolves this.

## 5. Implications for Future Work

### 5a. Direct Non-Uniform CCD (Approach A)

The only approach that avoids ξ-space entirely. Build CCD with physical-space
node-dependent spacings h₋ᵢ, h₊ᵢ directly. Taylor expansion about each node:

    Eq-I: α_L^i f'_{i-1} + f'_i + α_R^i f'_{i+1} = RHS(f, h₋, h₊)
    Eq-II: β_L^i f''_{i-1} + f''_i + β_R^i f''_{i+1} = RHS(f, h₋, h₊)

Coefficients (α_L, α_R, etc.) are rational functions of ρ = h₊/h₋,
derived per-node by solving a 6×6 Taylor matching system.

Block-tridiagonal structure is preserved but blocks are node-dependent:
- Lower[i]: [[α_L^i, b₁^i·h₋^i], [b₂^i/h₋^i, β₂^i]]
- Upper[i]: [[α_R^i, −b₁^i·h₊^i], [−b₂^i/h₊^i, β₂^i]]

Cost: O(N) for block-Thomas solve (same as uniform), but refactorization
needed at every grid rebuild.

### 5b. Limiting α to Reduce Metric Variation

For mild non-uniformity (α ≤ 1.1), J transition is gentler and the ξ-space
approach works acceptably. The max |dJ/dξ| scales as:

    max|dJ/dξ| ≈ (α−1) × N / (eps_g_factor × eps_ratio)

For |dJ/dξ| < 1: α < 1 + eps_g_factor × eps_ratio / N

At N=128, egf=2, eps_ratio=0.5: α < 1.008. Impractically small.

## 6. Summary

| Approach | Cross-term removed? | Under-resolution fixed? | Practical? |
|----------|:------------------:|:-----------------------:|:----------:|
| Current metric formula | No | No | Baseline |
| Two-Pass | Yes (algebraically) | No | No benefit |
| Scale egf with N | No | Yes | Loses localization |
| Direct non-uniform CCD | N/A (no metric) | N/A (no ξ-space) | **Required** |

The ξ-space CCD + metric approach is fundamentally incompatible with
localized grid refinement. The path forward is Approach A.

## Related

- [[WIKI-T-037]] — Grid remap interpolation order limit
- [[WIKI-T-038]] — Bandwidth constraint for grid rebuild
- [[WIKI-T-001]] — CCD method design rationale
- [[WIKI-T-035]] — 5-component error taxonomy
