---
ref_id: WIKI-E-031
title: "ch13 Static α=2 Rising-Bubble Diagnosis: Hypothesis Matrix and Verdicts"
domain: experiment
status: OPEN
superseded_by: null
sources:
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_debug/data.npz
    git_hash: f91e314
    description: baseline debug run with full step diagnostics
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_faceproj_debug/data.npz
    git_hash: 4b0c245
    description: explicit face-flux projection debug comparison
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_facepreserve_debug/data.npz
    git_hash: f91e314
    description: PoC A — preserve projected faces
  - path: experiment/ch13/results/ch13_rising_bubble_water_air_alpha2_n128x256_buoyancyproj_debug/data.npz
    git_hash: f91e314
    description: PoC B — projection-consistent buoyancy injection
depends_on:
  - "[[WIKI-T-063]]: FCCD face-flux PPE"
  - "[[WIKI-T-066]]: body-force discretization in variable-density NS"
  - "[[WIKI-T-068]]: FCCD face-flux projector"
  - "[[WIKI-T-070]]: projection-closure diagnosis"
tags: [ch13, rising_bubble, alpha_2, wall_bc, blowup, projection_closure, buoyancy]
compiled_by: ResearchArchitect
compiled_at: "2026-04-24"
---

# ch13 Static α=2 Rising-Bubble Diagnosis: Hypothesis Matrix and Verdicts

## Baseline observation

The baseline debug case blows up at `step=6`, `t=0.0148`.

What fails first is not mass conservation but the projection chain:

- `volume_conservation ~ 7e-08`
- `ppe_rhs_max: 1.33e+01 → 9.06e+09`
- `bf_residual_max: 2.36e+00 → 1.98e+11`
- `div_u_max: 2.48e-03 → 6.54e+05`

## Hypothesis matrix

| Hypothesis | Verdict | Evidence |
|---|---|---|
| Surface tension is the primary cause | Rejected | `sigma=0` still blows up |
| Gravity is the required trigger | Supported | `g=0` stays stable in short-horizon probe |
| Reinitialization causes the instability | Rejected | disabling reinit makes the run worse |
| Non-uniform `α=2` grid is the only cause | Rejected | `alpha=1` delays but does not remove blowup |
| Face-flux projection is absent | Rejected | FCCD path already enables it; forcing it off worsens the run |
| Wall zeroing after the corrector is the dominant cause | Weakened | face-preserve PoC does not improve stability |
| Buoyancy placement alone is the dominant cause | Rejected | projection-consistent buoyancy PoC is worse |
| Nodal/face source-of-truth mismatch is the dominant cause | Most plausible | all tests align with this interpretation |

## PoC verdicts

### PoC A — preserve projected faces

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_facepreserve_debug.yaml`

Result:

- blowup remains at `step=6`, `t=0.0147`
- `div_u_max` worsens to `2.31e+06`

Verdict:

Preserving projected faces inside the step is not enough if the wider runtime
still treats nodal velocity as the canonical state.

### PoC B — projection-consistent buoyancy

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_buoyancyproj_debug.yaml`

Result:

- blowup moves earlier to `step=6`, `t=0.0118`
- `ppe_rhs_max` worsens to `3.31e+12`
- `bf_residual_max` worsens to `4.28e+13`

Verdict:

Changing the buoyancy injection path without changing the canonical projection
state aggravates the instability.

## Experimental takeaway

The experimental campaign rules out several nearby explanations and leaves one
dominant reading:

> The face-stable object solved by the FCCD PPE is not preserved as the solver's
> canonical post-corrector state, and buoyancy repeatedly excites that closure
> gap.

This result raises the priority of a face/staggered canonical-state design for
the next implementation round.
