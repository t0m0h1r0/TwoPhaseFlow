---
ref_id: WIKI-E-019
title: "Local Epsilon Validation: Fixed ε vs ε(x) on Non-Uniform Grids (Exp 12-18)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: "experiment/ch12/exp12_18_local_eps_validation.py"
    description: "3-way comparison (A: uniform, B: fixed-ε, C: local-ε) at N=32,48,64"
consumers:
  - domain: A
    usage: "Paper §12.5b local-ε validation subsection"
  - domain: T
    usage: "Verifies WIKI-T-032 spatially varying ε theory"
depends_on:
  - "[[WIKI-T-032]]"
  - "[[WIKI-E-018]]"
  - "[[WIKI-T-009]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-11
---

# Local Epsilon Validation (Exp 12-18)

First numerical verification of WIKI-T-032 spatially varying ε theory. Compares three configurations on the static droplet benchmark.

## Setup

- Static droplet R=0.25, ρ_l/ρ_g=10, σ=1.0, μ=0.05, wall BC
- N=32, 48, 64; 200 steps; CFL=0.10
- **A:** uniform grid (α=1), scalar ε = 1.5·h
- **B:** non-uniform (α=2), fixed ε = 1.5·h_uniform
- **C:** non-uniform (α=2), ε(x) = 1.5·h_local(x)

## Results (N=64)

| Config | max|u| | Δp err | mass err |
|--------|--------|--------|----------|
| A: uniform | 9.5e-1 | **34%** | 9.6e-5 |
| B: fixed ε | **9.0e-2** | 68% | **2.6e-7** |
| C: local ε | 9.4e-2 | **60%** | 1.6e-7 |

## Findings

### 1. Laplace pressure improved (C vs B)

Consistent 8-9 percentage point improvement at all resolutions:
- N=32: 100% → 91%
- N=48: 84% → 77%
- N=64: 68% → 60%

Confirms WIKI-T-032 prediction: restoring ε/h_local = C_ε reduces CSF force broadening.

### 2. Parasitic currents unchanged

B and C produce nearly identical parasitic currents (9.0e-2 vs 9.4e-2 at N=64). Local ε does not introduce new instabilities. Confirms WIKI-T-032 §5 (balanced-force independence of ε).

### 3. Mass conservation maintained

C achieves same-order mass conservation as B (1.6e-7 vs 2.6e-7). Confirms WIKI-T-032 §3.5 (CSF force integral preserved).

### 4. Improvement is moderate at α=2

At α=2, h_min/h_uniform ≈ 0.9, so the ε-mismatch is mild. The 8pt improvement is consistent but small. At α=4 (h_min/h_uniform ≈ 0.08), the effect would be dramatically larger — the original negative result showed 400× parasitic current amplification from fixed ε.

## Theory Verification Status

WIKI-T-032 predictions:
- [x] Laplace pressure improves (confirmed: 8-9pt)
- [x] Parasitic currents unchanged (confirmed)
- [x] Mass conservation maintained (confirmed)
- [x] Balanced-force preserved (confirmed: no new instabilities)
- [ ] O(h²) convergence independent of α (not yet tested at high α)

**WIKI-T-032 status: PROPOSED → VERIFIED** (at α=2; high-α verification pending).

## Implementation Notes

- `heaviside()` and `delta()` required NO code changes (NumPy broadcast handles array eps)
- `invert_heaviside()` was already array-capable
- Only added: `_make_eps_field()`, `use_local_eps` flag, curvature eps update after grid rebuild
- Reinitializer keeps scalar ε_min (Option C from theory memo §4.2)
