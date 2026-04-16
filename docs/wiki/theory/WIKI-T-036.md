---
ref_id: WIKI-T-036
title: "Phi-Primary Transport: Machine-Precision Mass Conservation via SDF Transport"
domain: T
status: ACTIVE
superseded_by: null
sources:
  - path: "src/twophase/simulation/ns_pipeline.py"
    description: "Implementation: phi_primary_transport path in NS pipeline"
  - path: "experiment/ch13/exp13_91_phi_primary_reconstruct_trial.py"
    description: "Experimental validation: 13 orders of magnitude mass error reduction"
consumers:
  - domain: E
    usage: "exp13_91/92 experimental evidence; future non-uniform grid transport"
  - domain: X
    usage: "WIKI-X-014 recommended transport strategy"
depends_on:
  - "[[WIKI-T-007]]"
  - "[[WIKI-T-029]]"
  - "[[WIKI-T-030]]"
  - "[[WIKI-X-003]]"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-16
---

# Phi-Primary Transport

---

## 1. Motivation

Standard Conservative Level Set (CLS) transports the volume fraction $\psi \in [0,1]$
and reinitializes periodically. Each reinitialization cycle accumulates $O(\varepsilon_\text{reinit})$
mass error. Over $O(100)$ steps, this produces mass drift $\sim 10^{-3}$
([[WIKI-T-029]] documents the $\varepsilon$-dependent error metric).

**Alternative:** transport the signed distance function $\phi$ directly,
reconstruct $\psi = H_\varepsilon(\phi)$ each step. Since $H_\varepsilon$ is
deterministic given $\phi$, no additional mass error is introduced by the
reconstruction.

---

## 2. Algorithm

At each time step:

1. **Invert** $\psi \to \phi$ via $\phi = H_\varepsilon^{-1}(\psi)$ (logit inversion).
2. **Advect** $\phi$ using DCCD advection (smooth scalar, no [0,1] bound).
3. **Clip** $\phi$ to $[-c \cdot \varepsilon_\text{eff},\;+c \cdot \varepsilon_\text{eff}]$
   where $c$ = `clip_factor` (prevents SDF domain drift).
4. **Reconstruct** $\psi = H_\varepsilon(\phi)$.
5. **Every $N_r$ steps:** reinitialize $\psi$ (DGR), then round-trip
   $\psi \to \phi \to \psi$ to maintain Heaviside profile consistency.
6. **Mass correction** applied to final $\psi$.

Standard `reinit_every` logic is bypassed when `phi_primary_transport=True`.

---

## 3. Mass Conservation Analysis

$\phi$ is smooth ($C^\infty$ away from the interface) — CCD transport error is
$O(h^6)$ per step. The reconstruction $\psi = H_\varepsilon(\phi)$ is a
deterministic pointwise function of $\phi$ — it introduces zero additional error.

| Transport Method | Mass Error (180 steps) | Mechanism |
|---|---|---|
| $\psi$-transport | $\sim 1.37 \times 10^{-3}$ | Reinitialization accumulation |
| $\phi$-primary | $\sim 3 \times 10^{-16}$ | Machine epsilon bound |

**Improvement: 13 orders of magnitude.**

The $\psi$-transport mass error grows monotonically from $\sim 10^{-4}$ (early)
to $\sim 1.4 \times 10^{-3}$ (step 180), confirming accumulation.
The $\phi$-primary error remains at floating-point epsilon throughout.

---

## 4. Interface Sharpness

Mid-band occupancy fraction $f_{0.1-0.9}$ (fraction of cells with $0.1 < \psi < 0.9$):

| Method | $f_{0.1-0.9}$ |
|---|---|
| $\psi$-transport | 0.2005 |
| $\phi$-primary | 0.1987 |
| $\phi$-primary tuned (softH) | 0.1945 |

Improvement is modest ($\sim 1.5\%$). The primary benefit is mass conservation,
not sharpness.

---

## 5. Trade-offs

| Aspect | Pro | Con |
|---|---|---|
| Mass conservation | Machine-precision ($\sim 10^{-16}$) | — |
| Smoothness | $\phi$ is smoother than $\psi$ for CCD | Loses natural $[0,1]$ property |
| Clipping | Prevents SDF domain explosion | `clip_factor` requires tuning |
| Redistancing | Every $N_r$ steps (not every step) | Interface can drift without correction |
| Non-uniform grids | Reduced $E_\text{HF-noise}$ and $E_\text{metric}$ | Same $E_\text{time-coupling}$ |

---

## 6. Interaction with Non-Uniform Grids

On non-uniform grids, $\phi$ (a smooth signed-distance field) produces less
high-frequency noise and smaller metric amplification errors than $\psi$ (which
has a Heaviside front). This reduces $E_\text{HF-noise}$ and $E_\text{metric}$
in the level-set solve ([[WIKI-T-035]]).

---

## 7. Implementation Parameters

| Parameter | Default | Description |
|---|---|---|
| `phi_primary_transport` | `False` | Enable $\phi$-primary path |
| `phi_primary_redist_every` | 4 | Redistancing cadence (steps) |
| `phi_primary_clip_factor` | 12.0 | SDF domain bound in $\varepsilon$ units |
| `phi_primary_heaviside_eps_scale` | 1.0 | Heaviside width multiplier |

The pipeline constructs two `HeavisideInterfaceReconstructor` instances:
`_reconstruct_base` ($\varepsilon_\text{scale}=1.0$) for grid rebuild and IIM,
`_reconstruct_phi_primary` (configurable scale) for the transport path.

---

## One-Line Summary

Transporting $\phi$ (SDF) instead of $\psi$ (volume fraction) and reconstructing
$\psi = H_\varepsilon(\phi)$ each step achieves machine-precision mass conservation
at a modest 1.5% sharpness improvement.
