# CHK-RA-CH14-VAR-041 - Pressure/Velocity Work-Gate Design

Date: 2026-05-17

Scope: design the next gate required before a PhaseRegion capillary face
cochain can be used by pressure/velocity projection.  This checkpoint is
design-only.  It does not connect the force to runtime projection, perform a
micro-step, or run T/8.

## Current State

The PhaseRegion route has a validated zero-step chain:

```text
PhaseRegionForceAdmission
  -> PhaseRegionForceDiagnostics
  -> PhaseRegionForceAdmissionReport
  -> PhaseRegionForceAdapterDecision
```

The adapter decision is valid only as a diagnostic read.  It explicitly
withholds force:

```text
force_components = None
force_admissible = false
withheld_force_reason = pressure_velocity_work_gate_missing
```

## Key Finding from Runtime Code

`FCCDDivergenceOperator.project_faces(..., force_components=...)` currently
treats `force_components` as **nodal** vector components and calls
`face_fluxes(force_components)` internally.

The PhaseRegion cochain is already a **face** object:

```text
s_f = -M_f^{-1} T_h^* dE_h
```

Therefore this is forbidden:

```text
project_faces(..., force_components=cochain.surface_acceleration)
```

because it would pass a face cochain through a nodal-to-face evaluator and
silently change the discrete space.  The pressure/velocity gate must either
introduce an explicit face-force projection path or prove a nodal
reconstruction with the same work pairing.  The face-force path is the safer
next oracle.

## Required Work Gate

Before `force_admissible` may become true, the following must be proven in one
zero-step oracle:

```text
u_f          = FCCD face velocity from the runtime velocity space
s_f          = PhaseRegion capillary face acceleration
p_f          = pressure_fluxes(p, rho) in the same face space
M_f          = same face mass metric used by the Riesz cochain
D_f          = same FCCD divergence/boundary operator

projection: u_f^+ = u_f - dt p_f + dt s_f
work:       <s_f, u_f>_M and <p_f, u_f>_M are measured in the same M_f
```

The gate is not a physical time step.  It is a compatibility theorem over
spaces, shapes, boundary conditions, and work pairings.

## A3 Contract

| Equation / invariant | Discretization | Required code boundary |
|---|---|---|
| `s_f=-M_f^{-1}T_h^*dE_h` | PhaseRegion face cochain | existing admission candidate |
| `u_f` | `FCCDDivergenceOperator.face_fluxes(vel)` | runtime face velocity |
| `p_f` | `FCCDDivergenceOperator.pressure_fluxes(p,rho,...)` | pressure face reaction |
| `u_f^+=u_f-dt p_f+dt s_f` | face-level projection update | `apply_pressure_projection` or new face-force helper |
| boundary space | direct face boundary operator | same `boundary_face_space` for `p_f` and `s_f` |
| work metric | `face_weight_components=M_f` | same weights in all dot products |
| no hidden conversion | no face cochain through `face_fluxes` | explicit fail-closed test |

## Gate Ladder

### G0: Shape and Boundary Admission

Checks:

```text
shape(s_f[axis]) == shape(u_f[axis]) == shape(p_f[axis])
apply_direct_face_boundary_space(s_f) == s_f
same bc_type
same boundary_face_space
same grid/metric epoch
```

### G1: Pressure Range Orthogonality

Use manufactured pressure fields and verify the pressure reaction lives in the
declared pressure range under the same face metric.  The Hodge part of the
capillary cochain must not be silently converted into pressure range.

### G2: Work Closure

For virtual face velocities already admitted to the fixed stratum:

```text
dE[T_h(u_f)] + <s_f,u_f>_M = 0
```

and for projection-compatible pressure faces:

```text
<p_f,u_f>_M
```

must use the exact same face arrays and weights.  This is a scalar oracle, not
a time step.

### G3: Face-Level Projection Oracle

Only after G0--G2 pass may a zero-step projection oracle call:

```text
apply_pressure_projection(u_faces, p_faces, s_faces, dt)
```

or a new explicitly named helper:

```text
project_faces_with_face_force(...)
```

The existing `project_faces(..., force_components=...)` path must remain
blocked for `s_f` unless a nodal-force reconstruction theorem is separately
proved.

## Tests for Next Code Gate

The next code unit should be diagnostic-only and test:

```text
face cochain cannot be consumed through nodal force_components
candidate face shapes match FCCD face_fluxes shapes
boundary-face-space projection leaves admitted s_f unchanged
manufactured pressure face arrays share the same face metric
work dot products use exactly admission.face_metric.face_weight_components
force_admissible remains false
```

## Nonuniform and Boundary Policy

The gate must use runtime grid coordinates and FCCD caches after grid rebuild.
No uniform `h` shortcut is allowed.  Periodic, wall, and mixed boundary cases
are different face boundary spaces, not different theories.

## Exit Criteria Before Micro-Step

Micro-step remains blocked until:

```text
G0 shape/boundary PASS
G1 pressure range PASS
G2 work closure PASS
G3 face-level projection oracle PASS
force_admissible is still false until a final admission decision is added
```

Only then can a separate gate decide whether to expose a force to a
single-step runtime probe.

## Validation

```text
git diff --check = PASS
docs/wiki WIKI count = 434
docs/wiki/code WIKI-L count = 67
targeted CHK/wiki/design scan = PASS
```

[SOLID-X] design-only; no pressure/velocity coupling, production force route,
micro-step, or T/8.
