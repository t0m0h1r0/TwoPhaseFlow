---
ref_id: WIKI-E-008
title: "§12 Integration Tests: Split-PPE Failure Diagnosis and Curvature Filter Validation"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch12/exp12_02_laplace_bf.py
    git_hash: HEAD
    description: "Balanced-force Laplace pressure test with HFE curvature filter (rho=1000)"
  - path: experiment/ch12/exp12_07_static_droplet.py
    git_hash: HEAD
    description: "Static droplet 200-step convergence with HFE curvature filter (rho=2)"
  - path: experiment/ch12/exp12_12_rt_instability.py
    git_hash: HEAD
    description: "RT instability benchmark (sigma=0, no curvature filter)"
  - path: experiment/ch12/exp12_11_split_ppe.py
    git_hash: HEAD
    description: "Split-PPE manufactured solution comparison (reference)"
consumers:
  - domain: T
    usage: "Split-PPE theory: smoothed Heaviside incompatibility evidence"
  - domain: A
    usage: "§12 verification chapter: curvature filter methodology, split-PPE scope"
  - domain: L
    usage: "Solver configuration: when to use split-PPE vs variable-density PPE"
depends_on:
  - "[[WIKI-T-026]]"
  - "[[WIKI-T-005]]"
  - "[[WIKI-T-004]]"
  - "[[WIKI-E-007]]"
compiled_by: KnowledgeArchitect
verified_by: null
compiled_at: 2026-04-09
---

## Experiment: Split-PPE Conversion Attempt (2026-04-09)

### Hypothesis
All §12 two-phase integration tests should use split-PPE (constant-density Laplacian) + HFE curvature filter, matching the paper's recommended solver strategy.

### Method
Replaced variable-density PPE operator `∇·[(1/ρ)∇p] = div(u*)/dt` with constant-density Laplacian `∇²p = ρ·div(u*)/dt` in 7 experiment files. Used PPEBuilder.build(ones) + splu() for LU-factored constant-density matrix.

### Result: FAILURE

**exp12_02 (ρ_l/ρ_g = 1000, single step):**
- Without ρ scaling: Δp ≈ 0.02 (99.5% error) — pressure jump collapses
- With ρ scaling: Δp = −8.3 (307% error) — wrong sign, diverging

**exp12_07 (ρ_l/ρ_g = 2, 200 steps):**
- Δp error ~1% (acceptable)
- Parasitic currents **grow** with grid refinement (0.07 → 0.28 for N=32→128) — unstable

### Root Cause Analysis

The split-PPE approach drops the cross-term `(∇ρ·∇p)/ρ²` from the variable-density operator:

    Variable-density: ∇·[(1/ρ)∇p] = (1/ρ)∇²p − (1/ρ²)(∇ρ·∇p)
    Split-PPE:        ∇²p = ρ · RHS   (cross-term dropped)

This cross-term is O(Δρ/h) at the interface. For ρ_l/ρ_g = 1000, the error is catastrophic. Even at ρ_l/ρ_g = 2, the error accumulates over timesteps:

1. ∇·u^{n+1} ≠ 0 at the interface (velocity not divergence-free)
2. Divergence error feeds back as mass source in next step
3. Parasitic currents grow monotonically instead of saturating

### Key Insight

**Split-PPE ≠ constant-density Laplacian with smoothed density.**

Split-PPE solves ∇²p = f_k **independently in each phase** where ρ = ρ_k = const. This eliminates the cross-term because ∇ρ = 0 within each phase. But it requires **sharp interface jump conditions** ([p] = σκ) via GFM or equivalent.

In the smoothed Heaviside framework, ρ varies continuously through the interface region (width ~3h). There are no separate "phases" — the single PPE includes density variation implicitly. Replacing the variable-density operator with a constant-density one is not split-PPE; it is simply dropping a term.

### Implementation Path

| Approach | PPE Operator | Interface Treatment | Status |
|----------|-------------|-------------------|--------|
| Smoothed Heaviside (current) | ∇·[(1/ρ)∇p] = RHS | Implicit (ε-regularized) | ✓ Working |
| Split-PPE + GFM | ∇²p = f_k per phase | [p] = σκ at Γ (GFM) | ✓ exp12_3 (SimulationBuilder) |
| Constant-density + smoothed | ∇²p = ρ·RHS | None (cross-term dropped) | ✗ **Failed** |

## Experiment: InterfaceLimitedFilter Curvature Validation (2026-04-09)

### Method
Added `InterfaceLimitedFilter(C=0.05)` to curvature computation in all surface-tension experiments. Filter equation: κ* = κ + C h² w(ψ) ∇²κ, w(ψ) = 4ψ(1−ψ).

### Results: PASS (neutral)

| Experiment | Metric | Without Filter | With Filter |
|------------|--------|----------------|-------------|
| exp12_02 (ρ=1000, N=256) | Δp error | 0.22% | 0.22% |
| exp12_02 (ρ=1000, N=256) | u_para | 2.3e-4 | 2.3e-4 |
| exp12_07 (ρ=2, N=128) | Δp error | 1.0% | 0.97% |
| exp12_07 (ρ=2, N=128) | u_para | 6.3e-4 | 6.3e-4 |
| exp12_12 (RT, σ=0) | ω_measured | 1.77 | N/A (no σ) |

### Conclusion

InterfaceLimitedFilter has **negligible effect** on static/near-static droplet tests because:
1. Single-step tests: curvature is computed once, filter smoothing is O(C h²) ≈ 10⁻⁵
2. Low density ratios (ρ=2): curvature is already smooth at N≥64
3. Static interface: no curvature evolution to accumulate errors

The filter is expected to become significant for:
- Moving interfaces where curvature oscillations grow over time
- High curvature regions (small droplets, thin filaments)
- Higher density ratios where CSF force errors are amplified

### Files Modified

**HFE curvature filter added (PPEBuilder kept):**
- `experiment/ch12/exp12_02_laplace_bf.py`
- `experiment/ch12/exp12_07_static_droplet.py`
- `experiment/ch12/exp12_rc_high_order.py`
- `experiment/ch12/viz_ch12_droplet_fields.py`
- `experiment/ch12/viz_ch12_density_fields.py`

**No change (σ=0 or special purpose):**
- `experiment/ch12/exp12_12_rt_instability.py` — σ=0, no curvature
- `experiment/ch12/viz_ch12_rt_fields.py` — σ=0
- `experiment/ch12/exp12_08_hfe_ablation.py` — already has HFE study
- `experiment/ch12/exp12_3_gfm_static_droplet.py` — GFM path
- `experiment/ch12/exp12_crc_static_droplet.py` — CCD-PPE path

**Archived (superseded):**
- `experiment/ch12/exp12_1_rayleigh_taylor.py` → `_archive/` (superseded by exp12_12)
- `experiment/ch12/exp12_2_static_droplet_convergence.py` → `_archive/` (superseded by exp12_07)

**Paper updated:**
- `paper/sections/12a_force_balance.tex` — curvature filter in methodology
- `paper/sections/12d_coupling.tex` — HFE field extension vs curvature filter distinction
- `paper/sections/12e_interface_crossing.tex` — split-PPE GFM requirement note
