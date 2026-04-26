---
ref_id: WIKI-L-035
title: "Implementation Roadmap: Projection-Native Capillary Coupling"
domain: code
status: ACTIVE
superseded_by: null
tags: [capillary, surface_tension, projection, balanced_force, gpu, ch13]
compiled_by: Codex
compiled_at: "2026-04-26"
depends_on:
  - "[[WIKI-T-077]]"
  - "[[WIKI-T-076]]"
source_memo: "docs/memo/short_paper/SP-AA_capillary_energy_variational_geometry.md"
---

# Projection-Native Capillary Coupling

## Implementation goal

Replace the current dual capillary path with a named, testable coupling
strategy. Production should use:

```text
surface_tension.formulation = projection_native_jump
```

where capillarity is represented by a pressure jump datum consumed by the same
face projection operator as the PPE/corrector. Explicit CSF forcing is disabled
in this mode.

For phase-separated PPE, this datum is not `sigma*kappa*(1-psi)`. It is a
phase-labelled jump field `J_sep` whose interface trace satisfies:

```text
J_g|_Gamma - J_l|_Gamma = sigma kappa_Gamma.
```

## Current hazard

The current ch13 path computes:

```text
f_sigma = kappa grad(psi) / We
rhs += div(f_sigma/rho)
u^{n+1} += dt f_sigma/rho
pressure_eff = pressure + sigma kappa (1 - psi)
```

This is a dual representation of capillarity. It is useful as a regression
baseline but should be renamed:

```text
legacy_csf_jump
```

The smooth jump shape is also a mixture-style object. With
`coefficient: phase_separated`, cross-phase faces are cut, so
`grad(1-psi)` inside the smeared band becomes an intra-phase source instead of
a pure pressure trace jump.

## New package layout

```text
src/twophase/capillary/
  __init__.py
  state.py
  geometry.py
  curvature.py
  coupling.py
  diagnostics.py
```

### `state.py`

```text
CapillaryGeometryState:
  psi
  phi_geo
  delta_gamma
  n_face
  kappa
  J_sep
  area_h

CapillaryCoupling:
  rhs_force_components
  rhs_source
  pressure_flux_components
  corrector_force_components
  diagnostic_pressure_jump
  diagnostic_force_components
  diagnostics
```

### `curvature.py`

Define an interface:

```text
CapillaryCurvatureOperator.compute(geometry_state) -> kappa
```

Initial implementations:

- `PsiDirectHFELegacy`: existing production path, retained for regression;
- `SDFDirectCurvature`: curvature from shared `phi_geo`;
- `FaceVariationalCurvature`: future production target after energy tests.

### `coupling.py`

Define:

```text
CapillaryCouplingStrategy.assemble(geometry_state, rho, dt) -> CapillaryCoupling
```

Implement:

- `ProjectionNativeJump`: jump only, explicit force zero;
- `ExplicitBalancedCSF`: force only, jump disabled;
- `LegacyCSFJump`: current dual path.

`ProjectionNativeJump` must assemble `J_sep` and then convert it to a
phase-trace flux before calling the PPE. The PPE helper must not apply:

```text
pressure_eff = pressure + J_sep
```

nor reconstruct `J_sep` internally as `sigma*kappa*(1-psi)`.

Important verification result: applying a discontinuous nodal `J_sep` through
the current FCCD core operator does **not** pass the phase-separated null test.
The compact `face_gradient` sees the jump before `A_f^sep` cuts cross-phase
faces. Therefore implementation must not simply set
`pressure_eff = pressure + J_sep` and then use the ordinary FCCD pressure
gradient everywhere.

Instead split the correction:

```text
flux_p = A_f^sep G_f q + jump_flux_sep(J_sep)
```

with a dedicated phase-trace jump operator satisfying:

```text
jump_flux_sep(J_sep) = 0
```

for a constant-curvature static bubble.

The detailed operator contract is tracked in [[WIKI-L-036]].

The PPE RHS and corrector must use the same jump flux:

```text
L_sep q = D_f u_f^*/dt - D_f jump_flux_sep(J_sep)
u_f^{n+1} = u_f^* - dt(A_f^sep G_f q + jump_flux_sep(J_sep))
```

## NS pipeline integration

Replace direct use of `state.f_x/state.f_y` for capillarity with coupling
fields:

```text
capillary = capillary_strategy.assemble(geometry_state, state.rho, state.dt)

rhs = predictor_rhs + capillary.rhs_source
q = ppe_solver.solve(rhs, rho)
u_new = project(..., q, capillary.pressure_flux_components)
```

For `ProjectionNativeJump`:

```text
rhs_force_components        = zero arrays
rhs_source                  = -D_f jump_flux_sep(J_sep)
pressure_flux_components    = jump_flux_sep(J_sep)
corrector_force_components  = zero arrays
diagnostic_pressure_jump    = J_sep
```

Existing non-capillary body forces, including balanced buoyancy residuals,
remain outside this capillary coupling object.

## YAML migration

Recommended:

```yaml
numerics:
  momentum:
    terms:
      surface_tension:
        formulation: projection_native_jump
        geometry_source: ridge_eikonal_sdf
        curvature: sdf_direct
        jump_shape: phase_trace
        energy_audit: true
```

Backward compatibility:

```text
formulation: pressure_jump       -> legacy_csf_jump
curvature: psi_direct_hfe        -> PsiDirectHFELegacy
jump_shape: sigma_kappa_1mpsi    -> legacy smooth jump
```

Warn in debug mode when using `legacy_csf_jump`.

## GPU requirements

- All state arrays live on `backend.xp`.
- Geometry products are explicitly passed through `CapillaryGeometryState`;
  they are not hidden caches.
- Diagnostics reduce on device and synchronise only at configured output
  points.
- Prefer CuPy vector operations first; introduce custom kernels only after
  profiling.

## Test ladder

1. Unit: `ProjectionNativeJump` returns zero explicit force.
2. Unit: `LegacyCSFJump` reproduces current `f_sigma` and jump context.
3. Unit: phase-trace jump operator gives `L_sep J_sep = 0` for constant
   curvature.
4. Unit: current raw FCCD path remains available only as `legacy_csf_jump`.
5. Static bubble: lower `R_BF` than legacy.
6. Perturbed circle: non-growing `E_k + sigma A_h`.
7. Capillary wave: theoretical decay and symmetric force intersections.
8. Rising bubble: T=0.5 gate, then T=8 gate.

## SOLID audit

- [SOLID-S] Geometry, curvature, coupling, diagnostics, and pipeline
  orchestration are separate responsibilities.
- [SOLID-D] The NS pipeline depends on capillary interfaces, not concrete
  curvature classes.
- [SOLID-C2] Existing tested `psi_direct_hfe` logic remains available through
  `LegacyCSFJump` / `PsiDirectHFELegacy`.
