---
ref_id: WIKI-E-032
title: "ch13 Projection-Closure Trial Synthesis: Failed Hypotheses, Accepted Cause, Clean-Main Validation"
domain: experiment
status: RESOLVED
superseded_by: null
tags: [ch13, rising_bubble, diagnosis, projection_closure, fccd, phase_separated]
compiled_by: Codex
compiled_at: "2026-04-25"
---

# ch13 Projection-Closure Trial Synthesis

## Accepted cause

The accepted cause of the early ch13 rising-bubble blowup is a discrete
projection mismatch:

- PPE solved `D_f[(1/rho)_f^sep G_f(p)]`,
- corrector applied `D_f[(1/rho)_f^mix G_f(p)]`,
- wall-grid divergence rows were not guaranteed to match the matrix-free PPE
  rows.

The resulting residual was concentrated at cross-phase faces. It was excited by
gravity/buoyancy and amplified by the water-air density ratio.

## Trial ladder

| Trial family | Outcome | Lesson |
|---|---|---|
| `sigma=0` / surface-tension ablations | Did not identify surface tension as sole cause | Capillarity can amplify but was not the algebraic defect. |
| `g=0` / buoyancy ablations | Stable over short probe | Buoyancy is the trigger that excites the projection defect. |
| Reinitialization changes | Not sufficient | Interface quality matters, but the pressure projection still mismatched. |
| Face-preserve / face-canonical state carry | Not sufficient | Carrying faces does not help if the pressure correction uses the wrong `A_f`. |
| Projection-consistent buoyancy injection | Worsened in some probes | Moving buoyancy without closing PPE/corrector operators changes forcing, not the projection identity. |
| q-jump / reduced pressure | Useful after closure, not primary | Jump consistency is secondary to the `D_f A_f G_f` closure. |
| Phase-separated coefficient closure | Passed | Same `A_f`, `G_f`, `D_f`, and wall rows remove the early blowup. |

## Clean-main validation

Clean merge:

```text
8682cf5 Align FCCD projection with phase-separated PPE
977c834 Merge ch13 FCCD projection closure
```

Validation:

```text
make test ...
378 passed, 18 skipped, 2 xfailed
```

ch13 probe:

```text
make run EXP=experiment/ch13/run.py \
  ARGS='ch13_rising_bubble_water_air_alpha2_n128x256_faceproj_debug'
```

Final diagnostic at `T=0.05`:

```text
KE      = 1.283e-04
ppe_rhs = 8.564e+01
bf_res  = 4.407e+03
div_u   = 4.642e-01
```

This is not yet a final physical benchmark verdict. It is the clean-main
verification that the early explosive projection failure is removed without
importing the large experimental predictor-assembly branch.

## Why the successful trial worked

The successful trial was the first one that restored the exact discrete
projection identity:

```text
P_h = I - G_h L_h^{-1} D_h,
L_h = D_f A_f G_f.
```

All earlier repairs changed a source term, state carrier, or stage ordering
while leaving `A_f^PPE != A_f^corr` on interface faces.

## Related

- `docs/memo/short_paper/SP-X_projection_closure_trial_synthesis.md`
- `docs/wiki/theory/WIKI-T-076.md`
- `docs/wiki/code/WIKI-L-033.md`
- `docs/wiki/experiment/WIKI-E-031.md`
