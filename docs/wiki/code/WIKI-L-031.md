---
id: WIKI-L-031
title: "FCCDSolver Face-Jet Primitive and Upwind Taylor-HFE State"
status: IMPLEMENTED
date: 2026-04-23
links:
  - "[[WIKI-T-069]]: FCCD face jet theory"
  - "[[WIKI-L-024]]: FCCD library module"
compiled_by: ResearchArchitect
---

# FCCDSolver Face-Jet Primitive and Upwind Taylor-HFE State

## Code surface

`src/twophase/ccd/fccd.py` now exposes:

- `FCCDFaceJet(value, gradient, curvature)`
- `FCCDSolver.face_second_derivative(field, axis, q=None)`
- `FCCDSolver.face_jet(field, axis, q=None)`
- `FCCDSolver.upwind_face_value(field, advective_velocity_face, axis, nodal_gradient=None, q=None)`

## A3 mapping

| Theory symbol | Code |
|---|---|
| $u_f$ | `FCCDFaceJet.value` |
| $u'_f$ | `FCCDFaceJet.gradient` |
| $u''_f$ | `FCCDFaceJet.curvature` |
| $q=S_{\rm CCD}u$ | `q` from `CCDSolver.differentiate` |
| $u^{up}_{f}$ | `upwind_face_value(...)` |

## GPU rule

All new array operations use `backend.xp` and fused kernels. No `.get()`,
`.item()`, or `float(device_array)` is introduced in the hot path.

## Verification

Focused tests live in `src/twophase/tests/test_fccd.py`:

- face-jet fields match existing `face_value` / `face_gradient` primitives.
- face second derivative converges on smooth periodic fields.
- upwind Taylor-HFE reconstruction converges at third order for both velocity
  signs.
