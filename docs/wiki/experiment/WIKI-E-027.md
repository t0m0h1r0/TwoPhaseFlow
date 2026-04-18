---
ref_id: WIKI-E-027
title: "DGR Blowup Root-Cause: Interface Fold Cascade in Capillary Wave Benchmark"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: experiment/ch13/config/exp13_01_a1.0_dgr_noreinit.yaml
    description: "Set A1 — no reinit isolation"
  - path: experiment/ch13/config/exp13_01_a1.0_dgr_hybrid.yaml
    description: "Set A2 — hybrid isolation"
  - path: experiment/ch13/config/exp13_01_a1.0_dgr_sigma0.yaml
    description: "Set A3 — sigma=0 isolation"
  - path: experiment/ch13/config/exp13_01_a1.0_dgr_every20.yaml
    description: "Set A4 — every-20 isolation"
  - path: experiment/ch13/diag/exp13_diag_dgr_step1.py
    description: "Set C — global vs pointwise eps_local comparison at IC"
  - path: experiment/ch13/diag/exp13_diag_dgr_sdf_comparison.py
    description: "Set C — old global-scale vs pointwise phi_sdf"
  - path: src/twophase/levelset/reinit_dgr.py
    description: "DGRReinitializer — instrumented for Set B diagnostics"
depends_on:
  - "[[WIKI-T-030]]: DGR theory, hybrid scheme, and fold cascade limitations"
  - "[[WIKI-T-008]]: Curvature computation via CCD"
  - "[[WIKI-E-015]]: §13 benchmark suite definition"
  - "[[WIKI-E-022]]: Prior ch13 readiness investigation (first α=2.0 blowup observation)"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-18
---

# DGR Blowup Root-Cause: Interface Fold Cascade in Capillary Wave Benchmark

---

## Blowup Observation (baseline)

All four DGR reinitialization variants of exp13_01 (§13.1 capillary wave decay,
Prosperetti 1981, ρ_l=10, ρ_g=1, σ=1.0, μ=0.05, mode=2 perturbation ε=0.05)
blow up within t < 0.2 for all grid concentration parameters:

| Variant | t_blowup | step_blowup | KE_max | Note |
|---|---|---|---|---|
| a1.0_dgr | 0.069 | 114 | 1.1e+07 | uniform grid |
| a1.2_dgr | 0.153 | ~250 | 4.3e+06 | |
| a1.5_dgr | 0.161 | ~270 | 2.9e+06 | |
| a2.0_dgr | 0.071 | ~120 | 6.3e+06 | |

**Volume conservation is tight (~2%) at blowup** → not a mass-loss issue.
**α=1.0 (uniform grid) also blows up** → non-uniform grid is not the cause.

The split-reinit variants (exp13_01_a{1.0,1.2,1.5,2.0}, no _dgr suffix) all run
the full T=10 without blowup.

---

## Set A — Isolation Experiments

All configs use α=1.0 (uniform grid), exp13_01 physics (σ=1.0), single modification.

| Exp | Modification | Result | Conclusion drawn |
|---|---|---|---|
| A1 | `reinit_every=0` (no reinit) | BLOWUP step=114 | Fold forms regardless; DGR at least delays |
| A2 | `reinit_method: hybrid` | **STABLE T=10** | Split shape correction prevents fold amplification |
| A3 | `sigma=0.0` + DGR | **STABLE T=10** | CSF is the amplification mechanism |
| A4 | DGR every-20 steps | BLOWUP step=100 | Frequency doesn't fix root cause |

**Interpretation chain:**
- A1 (no reinit → BLOWUP at same step as DGR): the fold forms from capillary advection alone,
  not from any reinit artifact
- A2 (hybrid → STABLE): split's compression-diffusion PDE actively spreads the fold back to
  a normal sigmoid, preventing κ amplification
- A3 (σ=0 → STABLE): without surface tension, the fold produces no force → no blowup.
  CSF is the amplification mechanism, not the fold itself
- A4 (every-20 → BLOWUP): reduced DGR frequency doesn't help; the fold recurs between calls
  and DGR still cannot repair it

---

## Set B — Instrumented DGR Diagnostics

`DGRReinitializer.reinitialize()` instrumented to print per-call diagnostics.
Run: exp13_01_a1.0_dgr (α=1.0, DGR, T=0.10, max_steps=200, print_every=20).

Key log output:

```
[DGR#0001] eps_eff=0.02338  scale=0.9977  band_n=884  |∇ψ|_band: mean=6.56 min=2.06 max=10.70
[DGR#0011] eps_eff=0.02339  scale=0.9981  band_n=884  |∇ψ|_band: mean=6.57 min=1.78 max=10.77
[DGR#0021] eps_eff=0.02341  scale=0.9990  band_n=884  |∇ψ|_band: mean=6.57 min=1.15 max=10.83
[DGR#0031] eps_eff=0.02343  scale=0.9996  band_n=885  |∇ψ|_band: mean=6.55 min=0.0000 max=10.89  ← FOLD
step=60  KE=1.524e-02
[DGR#0041] eps_eff=0.02347  scale=1.0015  band_n=940  |∇ψ|_band: mean=6.96 min=1.009 max=57.18
step=80  KE=8.838e-01  ← 59× jump in 20 steps
step=114  BLOWUP (KE > 1e6)
```

**Key observations:**
- `eps_eff` remains 0.0234 throughout (median robust to outliers → fold cells invisible)
- `scale` ≈ 1.000 throughout (DGR is a near-no-op after fold onset)
- `|∇ψ|_band min` → 0 at step=62 (fold onset confirmed by |∇ψ|=0 in band)
- KE jumps 59× in 20 steps after fold → CSF amplification is exponential

**Root cause chain (confirmed):**

```
1. Capillary advection → interface fold (|∇ψ|→0 in band) at step ~62
2. DGR: fold cells are outliers → median ε_eff unchanged → scale≈1 → fold NOT repaired
3. CCD Laplacian stencil over fold cell → unphysical κ spike
4. CSF: F = σ·κ·δ(ψ)·∇ψ → exponential KE growth → BLOWUP (step=114)
```

**DGR design boundary:** DGR corrects interface THICKNESS (the ε_eff → ε mapping),
not SHAPE (sigmoid profile deformation). A fold is a shape defect. The global median
is intentionally robust — it is designed to ignore spatially-local outliers (e.g.,
isolated noise cells). Unfortunately, fold cells ARE outliers to the median, making
DGR structurally blind to them.

---

## Set C — Null Fix: Pointwise Normalization Also Fails

### Hypothesis

Replace global median ε_eff with per-cell normalization:

```python
# Hypothesis: paper-exact pointwise normalization
phi_sdf = phi_raw / |∇phi_raw|   (with safety floor g_min=0.1)
```

This matches WIKI-T-030 §Algorithm Step 2 literally and accounts for spatial variation
of ε_eff. Scale CV at IC: std/mean ≈ 0.002 (small), so the global median seemed adequate
at IC — but the hypothesis was that it fails mid-simulation when fold curvature grows.

### Result

WORSE: blowup at step=23 (vs original step=174 for global scale).

### Why It Fails

| Location | φ_raw | |∇φ_raw| | φ_sdf (global) | φ_sdf (pointwise) |
|---|---|---|---|---|
| Interface band | ±0.05 | ~0.024 | ±0.05 | ±0.05 |
| Bulk (ψ≈0 or 1) | ±0.32 | ~0 → g_min=0.1 | ±0.32 | **±3.2** |

- `invert_heaviside` saturates: ψ≈0 → φ_raw = ε·ln(δ/(1-δ)) ≈ ±13.8ε ≈ ±0.32
- In bulk cells, |∇φ_raw| ≈ 0 → g_min=0.1 floor activates
- φ_sdf_bulk = 0.32/0.1 = **±3.2**: 10× larger than the interface values ±0.05
- CCD Laplacian (O(h⁶), 6-point stencil in each axis) couples bulk and interface cells
  within a 3-cell band
- Sharp bulk/interface transition (3.2 → 0.05 in 2-3 cells) creates phantom curvature
  in the interface region even at t=0
- max|κ| at t=0: pointwise=7.29 vs global=6.34 (15% worse from the very first step)
- ψ_new difference: max|Δψ|=0.001107 → max|Δκ|=10.69 in band → faster blowup

**Lesson:** For DGR on logit-inverted fields, the g_min floor creates bulk φ_sdf
amplification that poisons CCD Laplacian via stencil coupling across the band boundary.
The global median scale avoids this by keeping φ_sdf bounded (≈φ_raw × 1.00) everywhere.

The DGR design limitation is **fundamental** (it cannot repair folds because folds are
shape defects), not **algorithmic** (changing the normalization method doesn't help and
can make things worse). The correct fix is architectural: use hybrid reinit so split
corrects shape first.

---

## Fix Applied

All four exp13_01 DGR variant configs changed `reinit_method: dgr` → `reinit_method: hybrid`.
This is consistent with WIKI-T-030 §Hybrid Scheme ("recommended for production").

**Verification results (T=10 full runs, remote GPU, 64×64 grid):**

| Variant | T_final | KE_max | BLOWUP | Status |
|---|---|---|---|---|
| a1.0_dgr (hybrid) | 10.00 | 1.43e+00 | False | PASS |
| a1.2_dgr (hybrid) | 10.00 | 4.18e-02 | False | PASS |
| a1.5_dgr (hybrid) | *pending* | — | — | — |
| a2.0_dgr (hybrid) | *pending* | — | — | — |

Test suite: 206 passed, 7 skipped, 2 xfailed. No regressions (2026-04-18).

---

## Cross-References

- `[[WIKI-T-030]]` §Limitations — theoretical derivation of DGR fold blindness and cascade
- `[[WIKI-X-013]]` — second ch13 blowup mechanism: Couette shear + explicit CSF (Taylor deformation)
- `[[WIKI-E-022]]` — prior ch13 readiness investigation that first observed α=2.0 DGR blowup at step ~21
- `[[WIKI-E-011]]` — hybrid reinitialization discovery: comp-diff splitting defect + DGR fix
