---
ref_id: WIKI-L-036
title: "Phase-Trace Jump Flux Operator for Phase-Separated PPE"
domain: code
status: ACTIVE
superseded_by: null
tags: [capillary, phase_separated_ppe, jump_flux, projection, gpu]
compiled_by: Codex
compiled_at: "2026-04-26"
depends_on:
  - "[[WIKI-T-076]]"
  - "[[WIKI-T-077]]"
  - "[[WIKI-L-035]]"
source_memo: "docs/memo/short_paper/SP-AA_capillary_energy_variational_geometry.md"
---

# Phase-Trace Jump Flux Operator

## Purpose

`jump_flux_sep(J_sep)` converts a phase-labelled capillary pressure jump into a
face flux compatible with the phase-separated PPE:

```text
L_sep = D_f A_f^sep G_f.
```

It must not differentiate the discontinuous composite jump field with ordinary
FCCD stencils. The operator exists precisely because raw FCCD sees across the
phase jump before `A_f^sep` cuts cross-phase faces.

## Algebraic contract

Given:

```text
r = D_f u_f^*/dt,
F_J = jump_flux_sep(J_sep),
L_sep q = r - D_f F_J,
u_f^{n+1} = u_f^* - dt(A_f^sep G_f q + F_J),
```

then:

```text
D_f u_f^{n+1} = 0
```

up to PPE solve tolerance.

## Required invariants

1. **Cut-face support**

```text
F_J(e)=0 for cross-phase faces.
```

2. **Young--Laplace nullity**

```text
J_l = const, J_g = const
=> F_J = 0.
```

This is the static constant-curvature bubble test.

3. **Gauge invariance**

```text
J_m -> J_m + C_m
```

must not change `F_J`.

4. **Same-flux closure**

The exact same `F_J` array must be used in:

- PPE RHS source `-D_f F_J`;
- velocity corrector pressure-like flux `-dt F_J`;
- diagnostics.

## Minimal implementation

Use a phase-restricted graph gradient:

```text
F_J,e = A_f^sep(e) * (J_m(j) - J_m(i)) / d_ij,
        e=(i,j), i,j∈V_m,
F_J,e = 0,
        otherwise.
```

This is intentionally local. It is lower order than FCCD, but it preserves the
phase-separated null space exactly. That is more important than formal compact
order for the first production trial.

## Proposed API

```text
PhaseTraceJumpFluxOperator:
  assemble(geometry_state, rho, coeff_face) -> PhaseTraceJumpFlux

PhaseTraceJumpFlux:
  face_flux_components  # F_J, face arrays
  rhs_source            # -D_f F_J, nodal array
  diagnostic_jump       # J_sep, nodal/phase-labelled plot field
  diagnostics           # norms, null-test values, support counts
```

`rhs_source` is a node field, not a force component. `face_flux_components` is
pressure-like and is subtracted in the corrector.

## GPU implementation sketch

For each axis:

```text
phase_lo = phase[0:N]
phase_hi = phase[1:N+1]
same = phase_lo == phase_hi

grad_J = (J[1:N+1] - J[0:N]) / dx_face
F_J = where(same, coeff_face * grad_J, 0)
```

Then compute `rhs_source = -D_f F_J` using the same face divergence routine as
the projection path. All arrays stay on `backend.xp`.

Do not call `fccd.face_gradient(J_sep)` for this operator.

## Integration point

In the pressure stage:

```text
rhs = predictor_rhs + noncapillary_rhs + capillary.rhs_source
q = ppe_solver.solve(rhs, rho)
```

In the face corrector:

```text
pressure_faces = A_f^sep G_f q
projected_faces = predictor_faces - dt * pressure_faces
projected_faces = projected_faces - dt * capillary.face_flux_components
projected_faces = projected_faces + dt * noncapillary_force_faces
```

The plotting pressure may be:

```text
p_plot = q + diagnostic_jump.
```

But `p_plot` must not be passed to the ordinary pressure-gradient operator.

## Tests

1. `J_sep` phase constants produce zero `F_J` and zero `rhs_source`.
2. Smooth legacy `sigma*kappa*(1-psi)` produces nonzero graph source.
3. Gauge shift `J_m -> J_m + C_m` leaves `F_J` unchanged.
4. PPE/corrector closure gives `D_f u^{n+1}=0` in a manufactured predictor
   field.
5. GPU and CPU norms match within tolerance.

## Future high-order path

A phase-restricted compact jump flux may replace the local graph gradient only
if it preserves all invariants above. Stencils must be solved per connected
phase component or truncated one-sided near the interface; they must never
couple `V_l` and `V_g`.
