---
ref_id: WIKI-E-025
title: "Ch13 Phi-Primary Transport Trial and Uniformized Visualization (exp13_91, exp13_92)"
domain: E
status: ACTIVE
superseded_by: null
sources:
  - path: "experiment/ch13/exp13_91_phi_primary_reconstruct_trial.py"
    description: "3-case phi-primary vs psi transport comparison"
  - path: "experiment/ch13/exp13_92_nonuniform_to_uniform_visualization.py"
    description: "Grid remap pipeline validation and visual comparison"
depends_on:
  - "[[WIKI-T-036]]"
  - "[[WIKI-L-018]]"
  - "[[WIKI-E-022]]"
compiled_by: ResearchArchitect
verified_by: null
compiled_at: 2026-04-16
---

# Ch13 Phi-Primary Trial and Uniformized Visualization

---

## Exp13_91: Phi-Primary Transport Trial

### Setup

Rising bubble ($\text{Re}=35$, $\text{Eo}=10$, $\rho_l/\rho_g=10$) on $64\times128$
non-uniform grid ($\alpha=2.0$). `reproject_mode=consistent_iim`, `eps_factor=1.0`,
180 steps.

### Results

| Case | $f_{0.1-0.9}$ (final) | mass_final | accept_ratio |
|---|---|---|---|
| psi_transport | 0.2005 | $1.37\times10^{-3}$ | 1.00 |
| phi_primary_transport | 0.1987 | $\sim 3\times10^{-16}$ | 1.00 |
| phi_primary_tuned_softH | 0.1945 | $\sim 3\times10^{-16}$ | 1.00 |

**Tuned softH parameters:** `redist_every=8`, `clip_factor=16`, `heaviside_eps_scale=2.0`.

### Key findings

1. **13 orders of magnitude improvement in mass conservation:**
   $\psi$-transport accumulates drift from $\sim 10^{-4}$ (early) to $1.37\times10^{-3}$
   (step 180). $\phi$-primary stays at machine epsilon ($\sim 3\times10^{-16}$) throughout.

2. **Modest sharpness gain:** mid-band occupancy improves $\sim 1.5\%$
   ($0.2005 \to 0.1987$). The softH variant gives best sharpness ($0.1945$).

3. **IIM accept_ratio = 1.00 for all three cases:** phi-primary transport does
   not introduce additional IIM rejection pressure.

4. **Mass conservation mechanism:** $\psi = H_\varepsilon(\phi)$ is recomputed
   deterministically each step — no reinitialization-induced mass leak.
   See [[WIKI-T-036]] for theoretical analysis.

---

## Exp13_92: Uniformized Visualization

### Setup

Rising bubble quickshot configs ($T_\text{final}=7.5\times10^{-4}$, 18 steps)
run with baseline and phi_primary, then remapped to uniform $65\times129$ grid
via `build_nonuniform_to_uniform_remapper`.

### Results

| Label | Steps | Interface points | KE range | vc range |
|---|---|---|---|---|
| baseline | 18 | 568 | $[1.50\times10^{-4},\;6.58\times10^{-2}]$ | $[-2.41\times10^{-2},\;6.23\times10^{-2}]$ |
| phi_primary | 18 | 576 | $[7.20\times10^{-5},\;7.91\times10^{-1}]$ | $[-9.38\times10^{-2},\;3.52\times10^{-1}]$ |

### Key findings

1. **Grid remap pipeline validated:** bilinear interpolation from non-uniform to
   uniform grid produces visually correct contours.
2. **phi_primary produces more interface points (576 vs 568):** slightly sharper
   interface from the first step, consistent with exp13_91.
3. **phi_primary shows higher early KE growth:** $\sim 12\times$ higher KE at
   $t=7.5\times10^{-4}$, likely due to sharper interface definition activating
   stronger capillary dynamics.

---

## Open Problem: Rising Bubble Full $T=1.2$

The `exp13_02_rising_bubble_alpha2_iim.yaml` config ($T_\text{final}=1.2$)
collapses before $t < 10^{-3}$. KE grows to $\sim 10^{7}$ and rise velocity
reaches $|v_c| \sim 1263$. This instability is not resolved by sharpness tuning
or phi-primary transport — it is a fundamental non-uniform grid + capillary coupling
issue documented in [[WIKI-E-022]] and [[WIKI-X-012]].

The quickshot configs ($T_\text{final}=7.5\times10^{-4}$, 18 steps) capture
pre-instability dynamics and are used for method comparison.

---

## Cross-References

- [[WIKI-T-036]] — Phi-primary transport theory (mass conservation analysis)
- [[WIKI-L-018]] — Library modules (grid_remap, reconstruction used here)
- [[WIKI-E-022]] — Ch13 readiness (context and open problems)
- [[WIKI-E-024]] — Sharpness sweep (complementary eps study)
