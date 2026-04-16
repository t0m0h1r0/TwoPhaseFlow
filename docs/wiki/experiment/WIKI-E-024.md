---
ref_id: WIKI-E-024
title: "Ch13 Non-Uniform Interface Sharpness Sweep: eps=1.0 Sweet Spot (exp13_90)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: "experiment/ch13/exp13_90_nonuniform_interface_sharpness_sweep.py"
    description: "3-case eps_factor sweep on non-uniform rising bubble"
depends_on:
  - "[[WIKI-T-034]]"
  - "[[WIKI-E-022]]"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-16
---

# Ch13 Non-Uniform Interface Sharpness Sweep (exp13_90)

---

## Setup

Rising bubble ($\text{Re}=35$, $\text{Eo}=10$, $\rho_l/\rho_g=10$) on $64 \times 128$
non-uniform grid ($\alpha=2.0$). `reproject_mode=consistent_iim`, 180 steps,
CFL=0.03.

**Hypothesis:** reducing `eps_factor` sharpens the interface and improves solution
quality, bounded below by a stability threshold.

---

## Results

| Case | $\varepsilon_\text{factor}$ | reinit_every | $f_{0.1-0.9}$ (final) | IIM accept_ratio | IIM backtrack_ratio | Failed |
|---|---|---|---|---|---|---|
| baseline_eps1p5_re2 | 1.5 | 2 | 0.3263 | 1.00 | 18.75% | No |
| sharp_eps1p0_re1 | **1.0** | 1 | **0.2025** | 1.00 | 6.25% | No |
| sharp_eps0p8_re1 | 0.8 | 1 | 0.1982 | 0.933 | 42.9% | **Yes** (step 159) |

---

## Key Findings

### 1. eps=1.0 is the practical sweet spot

Reducing $\varepsilon$ from 1.5 to 1.0 shrinks mid-band occupancy by 38%
($0.326 \to 0.203$). Further reduction to 0.8 yields only marginal additional
sharpening ($0.203 \to 0.198$) but causes numerical failure.

### 2. backtrack_ratio as instability predictor

| $\varepsilon$ | backtrack_ratio | Outcome |
|---|---|---|
| 1.5 | 18.75% | Stable |
| 1.0 | **6.25%** | Stable (best) |
| 0.8 | **42.9%** | Failure at step 159 |

The jump from 6% to 43% signals imminent instability. Operationally:

- `backtrack_ratio > 0.5` sustained $\to$ enter conservative mode
- `accept_ratio < 1.0` $\to$ IIM solver under severe stress

### 3. eps=0.8 is the stability boundary

At $\varepsilon=0.8$, `accept_ratio` drops to 0.933 — the first case in this
experimental series where IIM cannot always accept. The simulation fails at
step 159.

---

## Implications

- **Recommended default:** `eps_factor=1.0` with `reinit_every=1` for non-uniform
  grids ([[WIKI-X-014]]).
- **backtrack_ratio** should be included in runtime monitoring as an early-warning
  signal alongside `mass_err` and `u_peak`.
- Interface sharpening alone does not resolve the underlying kinetic energy growth
  in the non-uniform rising bubble — this is a separate instability ([[WIKI-E-022]]).

---

## Cross-References

- [[WIKI-T-034]] — IIM acceptance gate theory
- [[WIKI-E-022]] — Ch13 readiness (context for benchmark configurations)
- [[WIKI-X-014]] — Deployment defaults (eps_factor=1.0 recommendation)
