---
ref_id: WIKI-T-074
title: Well-Balanced Buoyancy Predictor Theory: Pressure-Robust, Interface-Band, Stage-Split Closure
category: theory
status: active
last_updated: 2026-04-25
---

# WIKI-T-074 — Well-Balanced Buoyancy Predictor Theory

## Core Claim

The ch13 rising-bubble failure is best interpreted as a failure of **predictor
closure**, not of level-set transport alone and not of a generic “gravity
stiffness” mechanism.

The admissible cure is:

> a stage-split, pressure-robust, well-balanced buoyancy predictor in which the
> vertical buoyancy mismatch is repaired during predictor assembly on the full
> two-axis dilated interface band, and the residual horizontal coupling is
> repaired mainly in the state seen by `V(u_pred)`.

## Why This Is the Right Mathematical Class

This conclusion combines five theory threads:

1. **Variable-density projection consistency**  
   pressure correction must close on the same discrete support as the corrected
   state.

2. **Pressure robustness / gradient robustness**  
   gradient-compatible body-force content should not contaminate the velocity
   update.

3. **Mass-momentum consistency at large density ratio**  
   the interface-defined material state and the predictor momentum state must be
   assembled consistently.

4. **Balanced-force / well-balanced source treatment**  
   gravity, pressure, and capillary forces must be paired within the same
   discrete family if quiescent equilibria are to be preserved.

5. **Multidimensional local equilibrium**  
   the successful repair is not edge-only, corner-only, x-only, y-only, or a
   simple weighted blend. It lives on the full local 3×3 interface
   neighbourhood.

## Minimal Discrete Form

\[
\mathbf{u}_{B}^{\dagger}
=
T_y^{I_1}\!\left(\mathbf{u}^n + \Delta t\,\mathbf{b}(\psi^n)\right),
\]

\[
\mathbf{u}_{\mathrm{pred}}^{(0)}
=
\mathcal{A}\!\left(
\mathbf{u}^n,\,
\mathbf{C}^n,\,
\mathbf{V}(\mathbf{u}^n),\,
\mathbf{u}_{B}^{\dagger}
\right),
\]

\[
\mathbf{u}_{\mathrm{pred}}^{(1)}
=
S_x^{I_1}\!\left(\mathbf{u}_{\mathrm{pred}}^{(0)}\right),
\]

followed by the usual CN/Picard viscous correction using
`V(u_pred^(1))`.

Interpretation:

- `T_y^{I₁}` = vertical buoyancy repair during predictor assembly
- `S_x^{I₁}` = horizontal/cross-component repair before `V(u_pred)`

## Literature Basis

- Almgren et al. (1998): variable-density adaptive projection  
- Brown–Cortez–Minion (2001): staggered-grid projection consistency  
- Guermond–Salgado (2009): pressure-Poisson splitting for variable density  
- Dodd–Ferrante (2014): pressure-correction for two-fluid flows  
- Rudman (1998), Raessi–Pitsch (2012): mass-momentum consistency at high density ratio  
- François et al. (2006), Patel–Natarajan (2017): balanced-force / well-balanced multiphase discretization  
- Linke et al. (2019), Akbas et al. (2020): pressure robustness / gradient robustness

## What This Excludes

Not admissible as final cures:

- buoyancy-only implicitness without assembly redesign,
- shallow hydrostatic or reduced-pressure patches,
- face-density-only buoyancy re-evaluation,
- late witness additions,
- pure strict-interface masks,
- scalar relaxation tuning.

## Cross-links

- theory derivation: `SP-U_buoyancy_predictor_well_balanced_foundation.md`
- predictor theory: `WIKI-T-072`
- stage-split redesign spec: `WIKI-X-036`
- experiment verdicts: `WIKI-E-031`
