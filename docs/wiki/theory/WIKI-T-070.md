---
id: WIKI-T-070
title: "Rising-Bubble Early Blowup on Static α=2 FCCD Stack: Buoyancy-Driven Projection-Closure Failure"
status: PROPOSED
date: 2026-04-24
links:
  - "[[WIKI-T-003]]: Variable-density projection baseline"
  - "[[WIKI-T-004]]: Balanced-force consistency principle"
  - "[[WIKI-T-063]]: FCCD face-flux PPE"
  - "[[WIKI-T-066]]: Body-force discretization in variable-density NS"
  - "[[WIKI-T-068]]: FCCD face-flux projector"
  - "[[WIKI-E-031]]: ch13 rising-bubble hypothesis verdicts"
compiled_by: ResearchArchitect
---

# Rising-Bubble Early Blowup on Static α=2 FCCD Stack: Buoyancy-Driven Projection-Closure Failure

## Claim

For the static-`α=2`, wall-bounded ch13 rising-bubble stack, the dominant
instability mechanism is not mass loss, not pure surface-tension error, and
not reinitialization drift. The dominant mechanism is a **projection-closure
failure** driven by buoyancy in a variable-density setting.

## Preconditions

The diagnosis applies to the following stack:

- psi-direct interface transport on a static interface-fitted non-uniform grid
- FCCD pressure projection with phase-separated coefficient and jump decomposition
- `pressure_jump` surface tension
- UCCD6 convection
- wall boundary conditions
- strong density contrast (`ρ_l/ρ_g ≈ 833`)
- nonzero gravity

## Discrete requirement

The variable-density corrector should enforce

$$
D_f\left(u_f^\* + \Delta t\,f_f/\rho_f - \Delta t\,M_f^{-1}G_f p\right)=0
$$

in the **same face space** that defines the PPE operator.

This is the relevant discrete closure, because the FCCD PPE and the FCCD face
projector are both face-flux objects.

## Where the current path breaks

The current runtime performs a face-stable projection, but the canonical solver
state remains nodal:

1. predictor and correction are assembled from nodal velocity fields
2. FCCD projection constructs corrected face fluxes
3. those face fluxes are reconstructed back to nodal velocity
4. the next predictor step again starts from the nodal field

Thus the face state solved by the PPE is not preserved as the authoritative
post-corrector state.

## Why buoyancy matters

Gravity is the repeated excitation mechanism. In the observed path:

- `g=0` stays stable in short-horizon probes
- `σ=0` still blows up
- `reinit_every=0` makes the run worse

So buoyancy is the necessary trigger, while surface tension, reinitialization,
and non-uniformity modulate amplification.

## Negative evidence

Two nearby countermeasures were tested and both failed:

### A. Preserve projected face state

Keeping corrected face fluxes inside the step and skipping the default
post-corrector wall zeroing does not remove the blowup.

Interpretation: boundary overwrite after the corrector is not the dominant
cause.

### B. Projection-consistent buoyancy injection

Moving buoyancy from the nodal predictor branch into the explicit force channel
used by the PPE RHS and the face corrector makes the run worse.

Interpretation: the problem is deeper than force placement alone.

## Consequence

The next viable design is a true face/staggered canonical state:

- keep the corrected face flux as the post-corrector source of truth
- use face divergence as the incompressibility gate
- demote nodal velocity to a derived field for advection support and diagnostics

Without that shift, local PoCs are likely to keep falsifying nearby hypotheses
without curing the instability.
