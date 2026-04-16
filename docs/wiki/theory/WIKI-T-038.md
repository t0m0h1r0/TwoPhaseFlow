---
ref_id: WIKI-T-038
title: "Bandwidth Constraint for Non-Uniform Grid Rebuild: eps_g_factor-dt Coupling"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: "experiment/ch11/exp11_34_alpha_bandwidth.py"
    description: "eps_g_factor sweep experiment confirming bandwidth constraint"
  - path: "src/twophase/core/grid.py"
    description: "Grid density function omega = 1 + (alpha-1)*exp(-phi^2/eps_g^2)"
consumers:
  - domain: E
    usage: "Parameter selection for non-uniform grid experiments"
  - domain: T
    usage: "Extends WIKI-T-037 with quantitative constraint; relates to WIKI-T-035 error taxonomy"
depends_on:
  - "[[WIKI-T-037]]"
  - "[[WIKI-T-031]]"
  - "[[WIKI-T-035]]"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-17
---

# Bandwidth Constraint for Non-Uniform Grid Rebuild

## 1. Grid Density Function

The interface-fitted grid uses a Gaussian density:

    omega(phi) = 1 + (alpha - 1) * exp(-phi^2 / eps_g^2)
    eps_g = eps_g_factor * eps

- alpha controls the **peak density** (h_min = h_uniform / alpha at interface)
- eps_g_factor controls the **bandwidth** (spatial extent of the fine region)
- These are independent: raising alpha does NOT widen the fine region

Fine-region half-width (where omega > 1 + (alpha-1)/e):

    W_fine = eps_g = eps_g_factor * eps

## 2. Bandwidth Constraint Derivation

Between grid rebuilds (every reinit_freq steps), the interface moves:

    delta_x = |u_max| * reinit_freq * dt

For the remap to use fine-grid source data at the new interface location:

    delta_x < W_fine                                         ... (*)
    |u_max| * reinit_freq * dt < c * eps_g_factor * eps

Substituting CFL condition dt = C_CFL * h and eps = eps_ratio * h:

    |u_max| * reinit_freq * C_CFL * h < c * eps_g_factor * eps_ratio * h

h cancels — the constraint is **resolution-independent**:

    reinit_freq < (c * eps_g_factor * eps_ratio) / (|u_max| * C_CFL)   ... (**)

Or equivalently, for fixed reinit_freq:

    eps_g_factor > (|u_max| * C_CFL * reinit_freq) / (c * eps_ratio)

## 3. Evaluation with Current Parameters

| Parameter     | Value | Role                    |
|---------------|-------|-------------------------|
| c             | 1.0   | Gaussian 1/e width      |
| eps_g_factor  | 2.0   | Current default         |
| eps_ratio     | 0.5   | Interface width eps/h   |
| \|u_max\|     | 0.5   | Zalesak rigid rotation  |
| C_CFL         | 0.45  | Advective CFL number    |
| reinit_freq   | 20    | Steps between rebuilds  |

From (**): reinit_freq < (1.0 * 2.0 * 0.5) / (0.5 * 0.45) = 4.4

**reinit_freq = 20 violates the constraint by factor 4.5x.**

To satisfy with reinit_freq=20: eps_g_factor > 9.0 (c=1) or > 4.5 (c=2).

## 4. Experimental Verification (exp11_34)

| eps_g_factor | W_fine/delta_x | area_err  | vs uniform |
|-------------|---------------|-----------|------------|
| 1.0         | 0.22          | 5.04e-02  | 132x       |
| 2.0         | 0.44          | 3.63e-02  | 95x        |
| 4.0         | 0.89          | 2.12e-02  | 56x        |
| 6.0         | 1.33          | 1.58e-02  | 41x        |
| 8.0         | 1.78          | 1.20e-02  | 31x        |
| uniform     | ---           | 3.82e-04  | 1x         |

Observations:
1. area_err improves monotonically with eps_g_factor (theory confirmed)
2. Radiating grid-rebuild artifacts disappear at W_fine/delta_x > 1 (egf >= 6)
3. **31x gap persists at egf=8** — bandwidth is necessary but not sufficient

## 5. Two-Layer Error Structure

The residual 31x gap after bandwidth satisfaction reveals two independent error sources:

1. **Bandwidth constraint** (eps_g_factor): whether the new interface falls within
   the old fine region. Violation causes catastrophic interpolation error (radiating
   artifacts). **Solved by eps_g_factor >= 5-6.**

2. **Resolution constraint** (alpha * eps_ratio): whether h_local within the fine
   region is small enough to resolve the Heaviside transition. With eps/h=0.5 and
   alpha=2, h_min = h/2 gives eps/h_min = 1.0 — still only 2 cells across the
   interface. **Requires alpha >> 2 or eps_ratio >> 0.5 to resolve.**

## 6. Parameter Design Guidelines

For a given problem with max velocity |u_max| and CFL number C_CFL:

    eps_g_factor >= (|u_max| * C_CFL * reinit_freq) / (c * eps_ratio)

Alternatively, choose reinit_freq adaptively:

    reinit_freq = floor((c * eps_g_factor * eps_ratio) / (|u_max| * C_CFL))

## Related

- [[WIKI-T-037]] — Interpolation order limit (why cubic doesn't help)
- [[WIKI-T-035]] — 5-component error taxonomy
- [[WIKI-T-031]] — Non-uniform grid CLS corrections
- [[WIKI-X-014]] — Stability map and recommended defaults
