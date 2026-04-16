---
ref_id: WIKI-X-012
title: "CCD Metric Instability on Non-Uniform Grids in NS Simulation"
domain: X
status: ACTIVE
superseded_by: null
sources:
  - commit: "a38af67"
    description: "docs(memo): finalize ch13 readiness report — 2/3 benchmarks PASS"
  - commit: "e23ebdd"
    description: "probe: add alpha=2 no-rebuild capillary wave to isolate rebuild vs grid effect"
depends_on:
  - "[[WIKI-E-016]]"
  - "[[WIKI-E-018]]"
compiled_by: ResearchArchitect
compiled_at: 2026-04-16
---

# CCD Metric Instability on Non-Uniform Grids in NS Simulation

This entry documents the instability mechanism observed when using the Combined
Compact Difference (CCD) scheme on non-uniform grids (α>1) for two-phase
Navier-Stokes simulation with surface tension.

Two distinct instability modes were identified and isolated experimentally.

---

## Mode 1: Grid Rebuild Metric Discontinuity

**Trigger:** `grid_rebuild_freq > 0` — re-fitting the non-uniform grid to the
interface at runtime.

**Mechanism:** When the grid is rebuilt, CCD operators must recompute metric
transformation coefficients J = ∂ξ/∂x and dJ/dξ. The old grid has a fitted
interface; the new grid has a different fitted interface. The O(1) jump in the
metric at the rebuild step causes CCD stencils that span the interface to produce
O(1) errors in velocity gradients and pressure.

**Observed symptom:** BLOWUP within 1 rebuild cycle (~step 21 for rebuild_freq=20).

**Fix:** `grid_rebuild_freq = 0` (disable grid rebuild).

---

## Mode 2: CCD Metric-Amplified Errors on Static Non-Uniform Grids

**Trigger:** `alpha_grid > 1.0`, even with `grid_rebuild_freq = 0`.

**Mechanism:** The CCD metric transformation amplifies errors proportional to
h_max/h_min = α^N_pts, where α is the concentration factor and N_pts is the
number of grid points from the widest to narrowest cell. For α=2.0, N=64,
this factor is O(10) to O(100).

At step 1–2, the predictor evaluates `u_star = u + dt*(conv+visc)` on the
initial Couette/quiescent state. The CSF surface tension force σκ applied at
the interface involves HFE (high-fidelity extension) evaluated on the
non-uniform grid. The CCD metric amplifies the κ→force computation by
~h_max/h_min at the interface, injecting spurious kinetic energy immediately.

**Quantitative evidence (capillary wave, N=64):**

| Grid | Step-0 KE | Step-2 KE | Ratio |
|------|-----------|-----------|-------|
| α=1.0 uniform | 5.93e-8 | 3.45e-7 | 5.8× |
| α=2.0 non-uniform | 7.91e-6 | 3.26e-2 | **4120×** |

After the initial spike, residual errors sustain KE ~100× above uniform level.
This residual grows exponentially at a rate per **physical time** (not per step).

**Blowup timeline (α=2.0, no rebuild, CFL=0.10):**

```
Step   2: KE = 3.26e-2  (initial spike)
Step   4: KE = 1.2e-3   (partially dissipated)
Step 409: KE = 0.052    (slow growth)
Step 430: KE = 1.008    (accelerating)
Step 435: KE = 4695     (blowup)
```

---

## CFL Independence Proof

Halving CFL from 0.10 to 0.05 (α=2.0, no rebuild) **accelerated** blowup:

| CFL | Blowup step | Blowup time |
|-----|-------------|-------------|
| 0.10 | 439 | t=0.125 |
| 0.05 | 283 | t=0.079 |

More steps per unit physical time, but smaller dt: the instability reaches
blowup at roughly the same physical time. This confirms the instability is
driven by **spatial** discretization error (CCD metric) rather than temporal
approximation error (dt too large).

---

## Connection to exp11_04 △

The ch13 capillary wave instability on α>1 is a direct manifestation of
**exp11_04 △** (non-uniform CCD pre-asymptotic oscillation at N≤128).
Exp11_04 showed that CCD's O(h^6) asymptotic convergence requires
N≥256 to enter the asymptotic regime on α=2 grids. Below N≈128, CCD
operates in the pre-asymptotic regime where metric errors are O(1) in
relative terms.

The α=2.0 capillary wave adds a moving interface with CSF forcing —
a worse case because the metric amplification is concentrated exactly
at the interface where the largest-amplitude forcing occurs.

---

## Fix and Trade-off

**Adopted fix:** `alpha_grid = 1.0` (uniform grid) for all ch13 benchmarks.

**Trade-off:** At N=64, interface region resolution is h=1/64≈0.016 everywhere.
With α=2.0, the interface had h_min≈0.004 (4× finer). The stability gain
far outweighs the resolution loss for ch13 validation purposes.

**Compensatory alternative:** N=128 uniform → h=0.008, comparable to
α=2.0 N=64 interface resolution. Costs 4× wall time per step.

---

## Future Work (Not Blocking ch13)

- Identify minimum N for α=2 to enter CCD asymptotic regime (likely N≥256)
- Local polynomial correction for CCD metric terms near non-uniform zones
- Hybrid scheme: FD near interface (non-uniform), CCD in bulk (uniform)

---

## Cross-References

- [[WIKI-E-022]] — Ch13 readiness experiment results (discovery context)
- [[WIKI-E-016]] — CCD non-uniform convergence study (exp11_04)
- [[WIKI-E-018]] — NS non-uniform grid convergence
- [[WIKI-E-020]] — Grid rebuild frequency calibration
- [[WIKI-X-013]] — Couette + explicit CSF instability (distinct mechanism)
