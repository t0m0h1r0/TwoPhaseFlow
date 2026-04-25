---
ref_id: WIKI-L-032
title: "Phase-Separated FCCD Projection Closure: PPE, Predictor Residual, and Corrector Faces"
domain: code
status: ACTIVE
superseded_by: null
tags: [fccd, ppe, projection, phase_separated, buoyancy, ch13]
compiled_by: Codex
compiled_at: "2026-04-25"
---

# Phase-Separated FCCD Projection Closure

## Core rule

For phase-separated PPE,

`L_sep(p) = D_f[(1/rho)_f^sep G_f(p)]`,

where `(1/rho)_f^sep` is zero on cross-phase faces. The velocity corrector and
the buoyancy residual split must use the same face coefficient. If PPE cuts a
face but projection uses harmonic mixture density on that same face, the solved
pressure is not the pressure used by the corrector.

## Failure mode

Before this closure, FCCD PPE used phase-separated coefficients, but
`FCCDDivergenceOperator.pressure_fluxes()` always used the harmonic mixture
coefficient. Thus the code solved

`L_sep(p) = rhs`

and then corrected with

`D_f[(1/rho)_f^mix G_f(p)]`.

The leftover divergence is

`D_f[((1/rho)_f^mix - (1/rho)_f^sep) G_f(p)]`,

which is concentrated at the density interface and is amplified by the
water-air density ratio.

## Implementation

- `FCCDDivergenceOperator.pressure_fluxes()` now accepts `coefficient_scheme`.
- `coefficient_scheme="phase_separated"` zeros cross-phase pressure fluxes.
- The face-native buoyancy residual uses the same coefficient choice as PPE.
- The velocity corrector passes phase-separated coefficients when FCCD PPE is
  phase-separated.

## ch13 verdict

The old face-residual debug case blew up at `step=4`, `t≈0.0109`.
After coefficient closure, the same case reaches `T=0.05` without blowup:

- no q-jump: final `KE=1.119e-05`, `ppe_rhs=1.174e+02`, `div_u=4.353e-01`
- q-jump PoC: final `KE=1.125e-05`, `ppe_rhs=1.192e+02`, `div_u=4.190e-01`

The root cause is therefore not lack of q-jump alone. The dominant defect was
mixed phase-separated and mixture-density face spaces in PPE/projection.
