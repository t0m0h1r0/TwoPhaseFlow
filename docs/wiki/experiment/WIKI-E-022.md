---
ref_id: WIKI-E-022
title: "Ch13 Readiness Investigation: 2/3 Benchmarks PASS, Taylor Deformation FAIL"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - commit: "a38af67"
    description: "docs(memo): finalize ch13 readiness report — 2/3 benchmarks PASS"
  - commit: "69bdc66"
    description: "config(ch13): switch all benchmarks to uniform grid (α=1.0)"
  - commit: "23ed967"
    description: "Merge worktree-research-ch13-readiness: ch13 readiness diagnosis"
depends_on:
  - "[[WIKI-E-017]]"
  - "[[WIKI-X-012]]"
  - "[[WIKI-X-013]]"
compiled_by: ResearchArchitect
compiled_at: 2026-04-16
---

# Ch13 Readiness Investigation

Branch `worktree-research-ch13-readiness` (2026-04-16) diagnosed which ch11 △
items block the three ch13 physical benchmarks, ran countermeasure experiments
on remote GPU, and verified results.

**Primary finding:** exp11_04 △ (non-uniform CCD pre-asymptotic oscillation) is
the blocker for capillary wave and rising bubble. Resolved by setting `alpha_grid=1.0`.
Taylor deformation has a separate, fundamental instability (see [[WIKI-X-013]]).

---

## Summary Table

| Benchmark | Status | Key Metric | Primary Blocker |
|-----------|--------|------------|-----------------|
| §13.1 Capillary wave | **PASS** | T=10.0 stable, KE oscillation+decay | exp11_04 → α=1.0 |
| §13.2 Rising bubble | **PASS** | v_c=0.160, \|ΔV\|/V₀=0.003% | exp11_04 → α=1.0 |
| §13.3 Taylor deformation | **FAIL** | All cases blowup at t<0.03 | Couette+explicit CSF |

---

## Exp13_01: Capillary Wave — PASS

**Config:** α=1.0, N=64, T=10.0, CFL=0.10 (`exp13_01_capillary_wave.yaml`)

| Metric | Value | Assessment |
|--------|-------|------------|
| Simulation stability | 15498 steps to T=10.0 | PASS |
| dt | constant 6.5e-4 | No CFL crisis |
| KE oscillation | Clear oscillation + viscous decay | Physics correct |
| KE peak | 0.139 at t≈0.6 | Decays to ~0.003 by t=8 |
| Vol conservation (T=1) | 0.11% | Good |
| Vol conservation (T=10) | 1.80% | Acceptable at N=64 |
| FFT deformation period | ~1.2 (theory: 0.92) | ~30% error (O(h¹) curvature) |

**Isolation experiments confirming root cause:**

| Config | Step-2 KE | Blowup |
|--------|-----------|--------|
| α=2.0, rebuild_freq=20 | 3.26e-2 (4120× spike) | Step ~21 |
| α=2.0, rebuild_freq=0 | 3.26e-2 (4120× spike) | Step ~439 |
| α=2.0, CFL=0.05 | 3.26e-2 | Step ~283 (earlier!) |
| α=1.0 | 3.45e-7 (5.8×) | Never — stable to T=10 |

CFL halving accelerated blowup (283 < 439), confirming CFL-independence.
The instability grows per physical time, not per step — it is a spatial
discretization error in CCD metric transformation (see [[WIKI-X-012]]).

---

## Exp13_02: Rising Bubble — PASS

**Config:** α=1.0, N=64×128, T=3.0, CFL=0.15, Re=35, Eo=10
(`exp13_02_rising_bubble.yaml`)

| Metric | Value | Assessment |
|--------|-------|------------|
| Simulation stability | 4978 steps to T=3.0 | PASS |
| Terminal velocity | v_c = 0.160 | Reaches steady state by t≈2 |
| Centroid rise | y_c: 0.500 → 0.673 | Physical bubble motion |
| Vol conservation (T=3) | 3.1e-5 (0.003%) | Outstanding |
| KE (steady state) | 0.037 | No spurious growth |

H2 (variable-density PPE degradation) not observed at ρ_l/ρ_g=10.
H3 (balanced-force breakdown on moving interface) not observed.
Both hypotheses rejected for this configuration.

---

## Exp13_03: Taylor Deformation — FAIL

**Configs tested:**
- N=128, α=1.0, cn_viscous=true: 8 cases, all BLOWUP at t<0.01
- N=64, α=1.0, cn_viscous=true (`exp13_03_taylor_deformation_N64.yaml`): 4 cases, all BLOWUP at t<0.03

**Failure mechanism:** Couette flow (KE≈0.177) is established stably in steps 1–N.
When CSF activates at step N+1, surface tension σκ creates a velocity perturbation
at the interface. Convective upwind amplifies this perturbation within 2–3 steps.

```
Step 1:   KE = 1.719e-1  (Couette established)
Step 2:   KE = 1.773e-1  (CSF onset)
Step 200: KE = 6.641e+3  (exponential growth)
Step 329: BLOWUP
```

Onset is **resolution-independent** (N=64 and N=128 fail at similar physical times)
and **CFL-independent** (cn_viscous=true, dt correctly bounded, same instability).
This is a scheme-level instability of the explicit predictor-corrector for
Couette+σ. See [[WIKI-X-013]] for full analysis.

**Countermeasures tried and failed:** cn_viscous=true, N=64 fallback, α=1.0.

**Required future work:** Semi-implicit σκ treatment; gradual σ ramp-up;
or full implicit coupling.

---

## Hypothesis Testing Summary

| Hypothesis | Result |
|------------|--------|
| H1: Non-incremental projection stable for moving σ>0 | **SUPPORTED** |
| H2: Variable-density PPE degradation at ρ=10 | **NOT OBSERVED** |
| H3: Balanced-force breakdown on moving interface | **NOT OBSERVED** |
| H4: Capillary CFL violation causes blowup | **REJECTED** |
| H5/H6: O(h¹) curvature impact (quantitative) | **DEFERRED** |
| H7: μ cross-terms cause Taylor failure | **NOT THE CAUSE** |
| H8: Uniform μ not needed for Taylor | **SUPPORTED** |

---

## △ Impact Assessment

| △ | Impact on ch13 | Mitigation |
|---|----------------|------------|
| exp11_03: O(h¹) curvature | Capillary wave period ~30% error at N=64 | Accept; validate qualitatively |
| exp11_04: Non-uniform CCD | **PRIMARY BLOCKER** (α>1 unstable) | Use α=1.0 |
| exp11_07: HFE upwind NaN | Not triggered at N=64 | No action needed |
| exp11_28: PPE κ∝N³ | FD PPE policy already in effect | No action needed |
| exp11_31: Reinit shift O(h²) | Contributes to volume conservation error | Accept; monitor |
| ASM-122-A: GPU drift | Lyapunov chaos amplification | DGR default (CHK-130) |

---

## Cross-References

- [[WIKI-X-012]] — CCD metric instability on non-uniform grids (root cause of α>1 failure)
- [[WIKI-X-013]] — Couette + explicit CSF instability mechanism
- [[WIKI-E-018]] — NS nonuniform grid convergence (related context)
- [[WIKI-E-020]] — Grid rebuild frequency calibration
- [[WIKI-E-017]] — NS grid rebuild (DGR fix, CHK-130)
