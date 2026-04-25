---
ref_id: WIKI-L-034
title: "ch13 Rising Bubble Closure: Balanced Buoyancy + Ridge-Eikonal FMM"
domain: code
status: ACTIVE
superseded_by: null
tags: [ch13, rising_bubble, buoyancy, fccd, projection, ridge_eikonal, fmm, time_integration]
compiled_by: Codex
compiled_at: "2026-04-25"
---

# ch13 Rising Bubble Closure: Balanced Buoyancy + Ridge-Eikonal FMM

## Decision

The production ch13 rising-bubble run uses the following clean configuration:

```yaml
numerics:
  momentum:
    predictor:
      assembly: balanced_buoyancy
    terms:
      convection:
        spatial: uccd6
        time_integrator: ab2
      viscosity:
        spatial: ccd
        time_integrator: crank_nicolson
        cn_mode: richardson
  projection:
    face_flux_projection: true
    canonical_face_state: true
    face_native_predictor_state: true
```

The old value
`buoyancy_faceresidual_stagesplit_transversefullband` remains a legacy alias,
but it is no longer the preferred YAML vocabulary.

## Theory pillar 1: pressure-robust buoyancy

For vertical gravity with potential `Phi_g = -g y`,

```text
rho' g = -grad(rho' Phi_g) + Phi_g grad(rho').
```

The gradient part is pressure-like. It must be represented in pressure space,
not advanced as a free explicit velocity source. The implemented
`balanced_buoyancy` predictor therefore advances only the non-hydrostatic
residual. Discretely, the residual acceleration is assembled as

```text
a_f^res = face(f_b / rho) + (1/rho)_f G_f(rho' Phi_g).
```

This is a pressure-robust / well-balanced source treatment: gradient forces
should not create solenoidal velocity.

## Theory pillar 2: face-state closure

The phase-separated projection uses the face operator chain

```text
D_f A_f G_f p.
```

Therefore the predictor state entering the PPE RHS must also be the
projection-native face state `u*_f`. The canonical face-state changes are not a
cache trick. They define the discrete state variable required for the proof:
the `D_f u*_f` used by the PPE and the `A_f G_f p` used by the corrector must
act on the same face geometry and phase cuts.

## Theory pillar 3: time integration

The accepted time update is term-aware:

- AB2 for smooth explicit momentum convection;
- Crank--Nicolson for viscous/parabolic response;
- Richardson/Picard refinement for the CN predictor state;
- projection as a constraint solve;
- SSP/TVD-RK3 retained only for bounded interface transport.

The important change is that the full variable-density momentum update is not
treated as one explicit TVD-RK3 RHS. The pressure/buoyancy balance and the
projection constraint determine the correct split.

## Theory pillar 4: Ridge--Eikonal requirement

Ridge--Eikonal is required because the capillary and pressure-jump terms depend
on a signed-distance reconstruction satisfying

```text
|grad(phi)| = 1
```

on the non-uniform wall grid. A fixed-sweep GPU pseudo-time Eikonal kernel is
not production-equivalent unless it proves residual convergence and boundary
consistency. In ch13 it delayed the blow-up but did not pass the final-time
run; non-uniform FMM did.

Acceptable future GPU work:

1. implement GPU FMM with the same accepted-set non-uniform update, or
2. implement residual-converged GPU fast sweeping with explicit wall-grid proof.

## Imported items

| Item | Production meaning |
|---|---|
| `balanced_buoyancy` | user-facing predictor mode for pressure-robust buoyancy |
| face residual acceleration | same-locus residual source built with PPE face operators |
| canonical face state | projected face velocity carried as primary state |
| face-native predictor state | `u*_f` constructed before PPE RHS assembly |
| CN predictor callbacks | source split applied inside the viscous predictor stage |
| `cn_mode: richardson` | short YAML alias for internal `richardson_picard` |
| non-uniform FMM redistancing | paper-faithful `|grad(phi)|=1` metric closure |

## Validation

Remote validation on 2026-04-25:

```text
make test
  559 passed, 3 skipped, 2 xfailed

make run EXP=experiment/ch13/run.py ARGS="ch13_rising_bubble_water_air_alpha2_n128x256"
  reached t=0.5000, step=140
  final KE=9.494e-04
  final kappa_max=3.528e+03
  final ppe_rhs=6.719e+02
  final bf_res=2.786e+02
```

Field outputs exist for `psi`, velocity, and pressure through `t=0.500`.

## Paper link

Use [SP-Z](../../memo/short_paper/SP-Z_rising_bubble_buoyancy_fmm_closure.md)
as the long-form source for the paper section. The paper should present this
as a single closure theorem: pressure-like buoyancy, projection-native face
state, term-aware time integration, and FMM redistancing are mutually required
for the ch13 water--air rising-bubble benchmark.

