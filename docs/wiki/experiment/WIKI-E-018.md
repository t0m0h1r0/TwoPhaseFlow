---
ref_id: WIKI-E-018
title: "Non-Uniform Grid NS Convergence: Static Droplet Multi-Resolution (Exp 12-17)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: "experiment/ch12/exp12_17_static_droplet_nonuniform.py"
    description: "Static droplet grid convergence: uniform vs interface-fitted (N=32,48,64)"
consumers:
  - domain: A
    usage: "Paper §12.5b non-uniform grid NS convergence"
  - domain: E
    usage: "Baseline for §13 production benchmarks with non-uniform grids"
depends_on:
  - "[[WIKI-E-017]]"
  - "[[WIKI-E-007]]"
  - "[[WIKI-T-009]]"
  - "[[WIKI-T-031]]"
compiled_by: KnowledgeArchitect
compiled_at: 2026-04-11
---

# Non-Uniform Grid NS Convergence (Exp 12-17)

System-level grid convergence study extending exp11_29 (100 steps, N=32) to multi-resolution (N=32,48,64) with 200 steps each. Compares uniform (α=1) and interface-fitted (α=2) grids on the static droplet benchmark.

## Key Results

| N | α | max|u| | Δp err | mass err | h_min |
|---|---|--------|--------|----------|-------|
| 32 | 1 | 2.6e-1 | 77% | 1.4e-3 | 0.031 |
| 32 | 2 | **1.2e-1** | 100% | **4.8e-6** | 0.029 |
| 48 | 1 | 1.9e-1 | 54% | 4.3e-4 | 0.021 |
| 48 | 2 | **1.3e-1** | 84% | **4.5e-6** | 0.019 |
| 64 | 1 | 9.5e-1 | **34%** | 9.6e-5 | 0.016 |
| 64 | 2 | **9.0e-2** | 68% | **2.6e-7** | 0.014 |

## Three Key Findings

### 1. Parasitic currents IMPROVED (unexpected)

α=2 reduces parasitic currents at ALL resolutions: 2× at N=32, 10× at N=64. This **contradicts** the static non-uniform grid result (400× worse at α=4, documented in `docs/memo/grid_refinement_negative_result.md`).

**Root cause of difference:** Per-timestep rebuild keeps the grid aligned with the interface at all times. The static grid becomes misaligned as the interface moves (even due to parasitic currents), amplifying CCD interpolation errors. Per-step rebuild eliminates this misalignment.

### 2. Mass conservation dramatically improved

α=2 achieves 100-300× better mass conservation: N=64 gives 2.6e-7 vs 9.6e-5. The per-step mass correction during remapping (via `apply_mass_correction`) accumulates less error than CLS advection on a fixed grid.

### 3. Laplace pressure accuracy degraded

α=1 consistently better: 34% vs 68% at N=64. Root cause: fixed ε = 1.5·h_uniform makes CSF force distribution ~1.7× wider than optimal near the interface (ε/h_local ≈ 1.7 at α=2). This broadened force cannot be exactly balanced by the pressure gradient.

**Remedy:** Spatially varying ε(x) = 1.5·h_local(x) would match the force width to local grid resolution. This requires changes to `heaviside()`, `CurvatureCalculator`, and `InterfaceLimitedFilter` — documented as future work.

## Trade-off Summary

| Metric | α=1 better | α=2 better | Magnitude |
|--------|-----------|-----------|-----------|
| Parasitic currents | | YES | 2-10× |
| Mass conservation | | YES | 100-300× |
| Laplace pressure | YES | | 1.5-2× |

**Recommendation:** Use α=2 when mass conservation is critical (rising bubble, RT instability). Use α=1 when pressure accuracy dominates (capillary wave frequency).

## Connection to Static Grid Negative Result

The `grid_refinement_negative_result.md` memo reported 400× worse parasitic currents with α=4 on a **static** non-uniform grid (no rebuild). This experiment shows per-step rebuild **reverses** that finding: the grid-interface alignment maintained by rebuild outweighs the CSF ε-mismatch penalty at moderate α.

The crossover point (where ε-mismatch dominates even with rebuild) is expected at higher α values where h_min/h_uniform becomes extreme. At α=2, h_min/h_uniform ≈ 0.9 — well within the beneficial regime.
