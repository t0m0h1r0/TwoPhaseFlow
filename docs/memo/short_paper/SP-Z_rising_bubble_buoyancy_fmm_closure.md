# SP-Z — Rising-Bubble Buoyancy/FMM Closure for ch13

- **Status**: ACTIVE
- **Compiled by**: Codex
- **Compiled at**: 2026-04-25
- **Scope**: `ch13_rising_bubble_water_air_alpha2_n128x256`

## 1. Claim

The `worktree-researcharchitect-src-refactor-plan` rising-bubble result is
reproduced on the clean worktree only when two discrete identities are enforced
simultaneously:

1. the momentum predictor is assembled in the projection-native face state, and
2. Ridge--Eikonal redistancing uses the converged non-uniform FMM signed
   distance, not a finite fixed-sweep approximation.

The stable production setting is therefore:

```yaml
momentum:
  convection:
    time_scheme: ab2
  viscosity:
    scheme: crank_nicolson
    cn_mode: richardson_picard
    predictor_assembly: buoyancy_faceresidual_stagesplit_transversefullband
projection:
  face_flux_projection: true
  canonical_face_state: true
  face_native_predictor_state: true
```

## 2. Buoyancy identity

For vertical gravity with potential `Phi_g = -g y`, the density-fluctuation
force satisfies

```text
rho' g = -grad(rho' Phi_g) + Phi_g grad(rho').
```

The first term is hydrostatic and belongs in pressure space. The second term is
the non-hydrostatic residual that may enter the velocity predictor. The
implemented predictor therefore builds the residual on the same face operator
used by the PPE corrector:

```text
a_f^res = face(f_b / rho) + (1/rho)_f G_f(rho' Phi_g).
```

This is not a cache optimisation. It is the discrete algorithmic state: the
face residual produced during predictor assembly is retained and reused by the
projection/corrector path so that `D_f A_f G_f` remains the same operator chain
throughout the step.

## 3. Time integration choice

TVD-RK3 is not the selected NS momentum integrator for this two-phase
capillary/buoyancy run. The accepted split is:

- explicit convection: AB2,
- viscous contribution: Crank--Nicolson with Richardson/Picard refinement,
- pressure projection: face-canonical variable-density projection,
- buoyancy predictor: residual-only stage split in face space.

This is the minimal tested combination that preserves the hydrostatic part in
pressure space while keeping the predictor consistent with the projection
state.

## 4. Eikonal redistancing requirement

The Ridge--Eikonal method requires the signed-distance reconstruction to solve

```text
|grad(phi)| = 1
```

on the non-uniform wall grid using the accepted-set upwind rule. A fixed number
of pseudo-time/Godunov sweeps is not equivalent unless a residual criterion and
boundary-consistent non-uniform update are proved. In the observed ch13 case,
the approximate device sweep delayed but did not remove blow-up, whereas the
non-uniform FMM path completed the run.

GPU optimisation is still required for the production solver, but the GPU
replacement for this component must be a mathematically equivalent GPU FMM or a
residual-converged non-uniform fast-sweeping method. A faster approximate
redistancing kernel is not admissible for this benchmark because curvature and
balanced force are sensitive to signed-distance error.

## 5. Verification

Validation on 2026-04-25:

```text
make test
  559 passed, 3 skipped, 2 xfailed

make run EXP=experiment/ch13/run.py ARGS="ch13_rising_bubble_water_air_alpha2_n128x256"
  reached t = 0.5000 in 140 steps
  final KE = 9.494e-04
  final kappa_max = 3.528e+03
  final ppe_rhs = 6.719e+02
  final bf_res = 2.786e+02
```

The earlier failing region near `t ≈ 0.38--0.46` is crossed without kinetic
energy blow-up.

