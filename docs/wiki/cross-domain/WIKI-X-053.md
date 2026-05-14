---
ref_id: WIKI-X-053
title: "Ch14 Capillary Zero-Base RCA: Boundary-Constrained Face State"
domain: cross-domain
status: ACTIVE
tags: [ch14, capillary_wave, ao_fast, rca, boundary_hodge, face_state, no_slip, moving_grid, phase_separated_ppe, hfe]
sources:
  - path: docs/wiki/theory/WIKI-T-173.md
    description: "Literature survey establishing the operator-consistency route"
  - path: docs/wiki/theory/WIKI-T-168.md
    description: "Constrained face-state space reformulation"
  - path: docs/wiki/theory/WIKI-T-172.md
    description: "Moving-grid face-cochain and pressure-history contract"
  - path: experiment/ch14/config/ch14_capillary.yaml
    description: "Current capillary-wave YAML"
  - path: src/twophase/simulation/config_run_builder_sections.py
    description: "Parser contract tying constrained_face to no-slip face state"
depends_on:
  - "[[WIKI-X-051]]"
  - "[[WIKI-X-052]]"
  - "[[WIKI-T-168]]"
  - "[[WIKI-T-172]]"
  - "[[WIKI-T-173]]"
consumers:
  - domain: code
    usage: "Use before touching capillary AO-Fast face-state, boundary, or projection code"
  - domain: experiment
    usage: "Use before rerunning long ch14 capillary-wave experiments"
compiled_by: ResearchArchitect
compiled_at: 2026-05-14
---

# Ch14 Capillary Zero-Base RCA: Boundary-Constrained Face State

## Knowledge Card

The latest zero-base review reframed the late capillary-wave failure as a
boundary-compatible face-complex problem.  The important contradiction is:

```text
YAML declares:       boundary_hodge.state_space = constrained_face
runtime published:   nodal velocity after no-slip wall clamping
stored face state:   only wall-normal faces constrained unless explicitly told otherwise
```

This mixes two velocity spaces.  The nodal field and the face cochain are then
not two representatives of the same state, so the next predictor, pressure
history, grid rebuild, and capillary jump operate on a mixed boundary complex.

Do not forget the governing route: Chapter 14 capillary troubleshooting keeps
**phase-separated PPE + HFE** as the base architecture.  HFE is not an optional
post-processor to discard when the run is unstable; it is the smooth one-sided
pressure/history coordinate that prevents FCCD/DC stencils from consuming a raw
Young--Laplace jump.  Any boundary, DC, GPU, or YAML change must preserve this
split-PPE/HFE contract before it is considered a valid remedy.

When a boundary face space is introduced, the HFE/affine jump contribution must
remain part of the same pressure equation, not a separate forcing shortcut.  The
restricted split equation is formally

```text
D_h P_B A_f G_h p = rhs + D_h P_B A_f B_HFE(j).
```

Thus both the left-hand operator and the HFE affine RHS must apply the same
admissible-space projection `P_B`.  Applying `P_B` only to `A_f G_h p` while
leaving `A_f B_HFE(j)` in the full face space is a mixed-complex bug.  However,
`P_B` must be the theory-selected metric wall retraction/quotient operator; raw
boundary-face zeroing is not a complete production pressure operator because it
can change the pressure nullspace and RHS range.

## Hypothesis Matrix

| Hypothesis | Theoretical test | Evidence / verdict |
|---|---|---|
| Physical capillary instability | Surface energy should exchange with kinetic energy; a face-Hodge spike without compatibility failure is not physical wave growth. | Rejected as primary. |
| `q`/`phi` graph incompatibility | Check `compat_linf` and graph retraction. | Earlier fixed; current diagnostics keep `compat_linf=0`. |
| DC iteration count too low | DC must be convergence-gated, not count-gated. | Rejected as root; fail-close convergence remains required. |
| Replacing the route by GMRES, monolithic FD, or non-HFE pressure handling | The target paper route is phase-separated PPE + HFE + high-order DC; changing the solver family can hide the defect instead of explaining it. | Rejected as a shortcut. Use such runs only as diagnostics, never as the production fix. |
| Pressure history stores wrong object | History must be smooth coordinate without AO reaction. | Important but already addressed; not the observed late face spike. |
| Projected face cochain lost at rebuild | Face interpolation and Hodge projection do not commute. | Identified earlier and partially fixed by projected-face transport. |
| Momentum remap correction uses wrong metric | Least-change momentum correction should be kinetic-metric, `delta m=rho lambda`. | Supported and fixed in grid rebuild. |
| Initial/rebuild face state must seed projection-native Hodge | If no projected faces exist, nodal remap alone seeds the wrong complex. | Supported and fixed by seeding `reproject_faces` from `div_op.face_fluxes`. |
| Boundary face state is inconsistent with no-slip nodal state | If only normal faces are zeroed, reconstructed/transported face state and no-slip nodal state differ on wall tangential DOFs. | Supported by code audit; parser/YAML now require no-slip face state for `constrained_face`. |
| HFE affine RHS is outside the restricted boundary face equation | Check whether `D_h P_B A_f G_h p` and `D_h P_B A_f B_HFE(j)` use the same admissible `P_B`. | Supported as a necessary condition. A direct-face projection test catches the mismatch, but production still requires the metric retraction/quotient and matching RHS range compatibility, not raw boundary-face zeroing. |
| Full restricted PPE `D_h P_w G_A` is still missing | Literature and WIKI-T-168 select it as the final production operator. | Not fully implemented; current fix closes the essential face-state contract and keeps this as the next larger step. |

## Implemented Countermeasure

For any configuration declaring

```yaml
numerics:
  projection:
    boundary_hodge:
      state_space: constrained_face
```

the parser now requires:

```yaml
face_no_slip_boundary_state: true
```

If omitted, the parser derives `true` from `state_space: constrained_face`.
If explicitly disabled, it fails closed.  Chapter 14 YAMLs now spell the flag
out for readability.

This means the face-native predictor state, PPE RHS face state, AO capillary
jump cochain, pressure-reaction cochain, and stored projected face state use
the same no-slip boundary space as the nodal velocity publication.

## Remaining Open Front

The larger theorem-selected route remains the production restricted pressure
operator:

```text
f_new = P_w f_dag - dt P_w G_A p,
D_h f_new = 0,
K_w p = D_h P_w f_dag / dt,
K_w = D_h P_w G_A.
```

The current change is not a substitute for `D_h P_w G_A`; it removes a proven
mixed-boundary-state contradiction so the remaining diagnostics can target the
true restricted-PPE gap instead of a simpler publication-state mismatch.

## Negative Knowledge

Do not fix this failure by:

- changing capillary amplitude, CFL, damping, or smoothing;
- replacing phase-separated PPE + HFE/DC by a different production route just
  to make the run advance;
- using micro-offsets;
- disabling nonuniform grids or grid rebuilds;
- publishing no-slip nodal velocity while carrying a no-penetration-only face
  state;
- enabling a post-pressure wall projection as a silent production fallback;
- ignoring wall-trace diagnostics because `div_u` alone is small.
