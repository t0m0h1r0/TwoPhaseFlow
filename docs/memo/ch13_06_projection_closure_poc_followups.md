# CHK-182: projection-closure PoC follow-ups for ch13 rising bubble

Date: 2026-04-24
Branch: `worktree-researcharchitect-src-refactor-plan`
Execution: remote GPU via `make cycle`

## Goal

Follow up on the ch13 rising-bubble blowup after the theoretical diagnosis:

```text
buoyancy-driven variable-density projection closure failure
```

Two minimal opt-in PoCs were tested without touching the FCCD matrix-free hot
path.

## PoC A — preserve projected face state

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_facepreserve_debug.yaml`

Implementation:

- keep corrected face fluxes as an internal step state
- reconstruct nodal velocity from those faces
- skip post-corrector wall zeroing for the default wall path

Result:

| case | blowup | key diagnostics at blowup |
|---|---|---|
| baseline face projection | `step=6`, `t=0.0148` | `ppe_rhs=9.06e9`, `bf_res=1.98e11`, `div_u=6.54e5` |
| preserve projected faces | `step=6`, `t=0.0147` | `ppe_rhs=9.35e9`, `bf_res=1.40e11`, `div_u=2.31e6` |

Interpretation:

- preserving corrected faces alone does **not** fix the instability
- post-corrector wall zeroing is therefore not the dominant root cause

## PoC B — projection-consistent buoyancy injection

Config:

`experiment/ch13/config/ch13_rising_bubble_water_air_alpha2_n128x256_buoyancyproj_debug.yaml`

Implementation:

- remove buoyancy from the nodal predictor branch
- inject buoyancy through the explicit force field used by the PPE RHS and the
  face-flux corrector

Result:

| case | blowup | key diagnostics at blowup |
|---|---|---|
| baseline face projection | `step=6`, `t=0.0148` | `ppe_rhs=9.06e9`, `bf_res=1.98e11`, `div_u=6.54e5` |
| projection-consistent buoyancy | `step=6`, `t=0.0118` | `ppe_rhs=3.31e12`, `bf_res=4.28e13`, `div_u=9.78e6` |

Interpretation:

- routing buoyancy through the current explicit force path makes the run worse
- the dominant defect is not just "where buoyancy enters", but the deeper
  closure mismatch between nodal momentum state and face-flux pressure
  projection

## Conclusion

The two smallest countermeasures both fail:

1. preserving the corrected face state
2. making buoyancy enter through the same explicit force channel as surface tension

This strengthens the original diagnosis: the next viable fix is a stricter
staggered/face-state design where the projection variable remains canonical
after the corrector, instead of being converted back into nodal velocity as the
authoritative state.
