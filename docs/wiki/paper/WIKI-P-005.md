---
ref_id: WIKI-P-005
title: "§10-§12 verification architecture: 27 component tests + 13 NS consistency tests"
domain: P
status: ACTIVE
superseded_by: null
sources:
  - path: "paper/sections/10_full_algorithm.tex"
    description: "§10 algorithm specification"
  - path: "paper/sections/11_chapter.tex"
    description: "§11 component verification chapter"
  - path: "paper/sections/12_verification.tex"
    description: "§12 NS physical consistency chapter"
  - path: "paper/sections/12f_error_budget.tex"
    description: "§12.6 error budget"
consumers:
  - domain: A
    usage: "Paper narrative structure and completeness"
  - domain: E
    usage: "Experiment coverage mapping"
depends_on:
  - "[[WIKI-P-001]]"
  - "[[WIKI-P-004]]"
  - "[[WIKI-E-013]]"
  - "[[WIKI-E-014]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-10
---

# §10-§12 Verification Architecture

## Three-Layer Verification Structure

| Chapter | Purpose | Tests |
|---------|---------|-------|
| §10 | Algorithm specification | 7-step loop, DCCD parameters, bootstrap |
| §11 | Component mathematical verification | 19 base + 8 supplementary = **27 tests** |
| §12 | NS physical consistency verification | **13 tests** (6 base + 4 new + 3 failure-mode) |

## §11 Component Verification Coverage Map

### Base Tests (19)
| Stage | Components | Tests |
|-------|-----------|-------|
| Spatial foundation | CCD periodic/wall/non-uniform, GCL, DCCD filter, DCCD advection 1D, curvature 3-path, C/RC bracket | 7 |
| Interface pipeline | CLS advection (Zalesak+vortex), DCCD mass conservation, CLS remapping, HFE 1D/2D, Young-Laplace | 6 |
| Pressure solver | DC k-accuracy, DC vs FD, DC ω-relaxation, PPE Neumann, split-PPE density sweep, variable-density reference | 6 |
| Time integration | TVD-RK3, AB2 | 2 → total 19 |

### Supplementary Tests (8, added 2026-04-10)
| Test | Gap Filled | Key Result |
|------|-----------|------------|
| Mixed partial ∂²f/∂x∂y | §6b 2D CCD extension | O(h^6.0) periodic |
| DGR verification | §7b thickness correction | Idempotent; 92× improvement |
| WENO5 vs DCCD | §7 advection motivation | DCCD trades accuracy for conservation |
| CN temporal | §5 implicit viscous | O(Δt^2.0), unconditionally stable |
| Pressure filter prohibition | §8c filter warning | O(h²) divergence error quantified |
| PPE condition number | §9c operator scaling | κ = 2.2×10⁷ at ρ=1000, N=64 |

## §12 NS Physical Consistency Coverage

| Section | Test | Key Result |
|---------|------|------------|
| §12.1 | Hydrostatic equilibrium | ‖u‖∞ < 10⁻⁹ at N≥64 |
| §12.1 | Laplace pressure | Δp = 3.99 (0.22% error) at N=256 |
| §12.1 | **CCD vs FD parasitic** | FD/CCD = 11× at N=64 |
| §12.2 | TGV energy decay | E_k error 3.9×10⁻⁸, ‖∇·u‖ < 10⁻¹³ |
| §12.3a | TGV temporal convergence | O(Δt^2.00) |
| §12.3b | Kovasznay spatial | NS residual O(h^3.97) |
| §12.3c | High-Re DCCD non-invasiveness | |E_CCD - E_DCCD|/E < 10⁻⁸ |
| §12.3d | **Cross-viscous CFL** | C_cross ≈ 0.23 (constant) |
| §12.3e | **Interface temporal degradation** | Bulk O(Δt^1.9), interface O(Δt^1.7) |
| §12.4a | Static droplet long-term | Stable 200+ steps (ρ≤5) |
| §12.4b | Galilean invariance (σ=0) | ‖u_para‖ < 10⁻¹⁵ |
| §12.4c | **Capillary CFL** | Exponent 1.505 ≈ 3/2 |
| §12.4d | RT instability | ω_meas = 1.82 (2.8% error) |

Bold = newly added in 2026-04-10 gap-filling session.

## Error Budget Summary (§12.6)

**Rate-limiting factors by regime:**
- Single-phase NS: CCD boundary scheme → effective O(h^4); AB2+IPC → O(Δt²)
- Two-phase (ρ_l/ρ_g ≤ 5): CSF model error O(ε²) ≈ O(h²) dominates
- Two-phase (ρ_l/ρ_g ≥ 10): Variable-density PPE diverges → split PPE required

**CCD high-order significance:**
- Direct: Does NOT improve overall accuracy under CSF O(h²) limit
- Indirect: (1) Reduces parasitic current coefficient by ~10⁷× at h=1/64, (2) Split PPE removes CSF limit, recovering CCD O(h⁶)

## Known Limitations (from §12.4-§12.5)

1. Moving interface + surface tension + IPC: diverges at 2 steps (∇p^n crosses interface jump)
2. Variable-density PPE: DC diverges at ρ_l/ρ_g ≥ 10 (κ too large)
3. Both resolved by split PPE + HFE (demonstrated in §11.3 split-PPE tests)
