# CHK-RA-CH14-VAR-039 - PhaseRegion Force Adapter Consumer Design

Date: 2026-05-17

Scope: design the zero-step consumer boundary for
`PhaseRegionForceAdmissionReport`.  This checkpoint is design-only.  It does
not connect capillary force to pressure/velocity projection, nonlinear
optimization, micro-stepping, or T/8.

## Why This Gate Exists

`CHK-RA-CH14-VAR-038` made the candidate report fail-closed, but it is still
possible for future runtime code to accidentally read the candidate's
`surface_acceleration` as if it were an accepted force.

The consumer boundary must therefore be a **blocked read gate**:

```text
PhaseRegionForceAdmission + PhaseRegionForceAdmissionReport
  -> PhaseRegionForceAdapterDecision
       report accepted as diagnostic
       force payload withheld
       force_admissible = false
```

The consumer may prove that the diagnostic object is well formed.  It may not
make the face cochain available to a solver step until the later
pressure/velocity work gate is proven.

## State Ownership

The consumer reads only the zero-step candidate identity:

```text
Omega_g owner map
runtime psi gauge
face mass metric M_f
Riesz face cochain s_f
diagnostic report
```

It does not own:

```text
velocity state
pressure unknown
PPE RHS
velocity correction
time-step update
```

This keeps the current design from sliding back into the old split:

```text
q is saved, phi is rebuilt, force is read elsewhere, velocity is projected
```

## A3 Boundary

| Equation / invariant | Discretization | Consumer result |
|---|---|---|
| `q_g = |C|-q_l` | explicit owner-map complement | require `complement_used` visible |
| `psi = H(-phi)` | nodal runtime chart gauge | require report/candidate shape agreement |
| `M_f` | current face metric from grid/boundary epoch | require face shape metadata |
| `s_f=-M_f^{-1}T_h^*dE_h` | diagnostic Riesz cochain | readable only as diagnostic |
| `dE[T(u)] + <s,u>_M = 0` | fixed-stratum work checks | require diagnostics valid |
| no pressure/velocity theorem yet | missing work gate | withhold force payload |

## Proposed Code Shape

```text
PhaseRegionForceAdapterDecision
  valid: bool
  reason: str
  force_admissible: bool
  report: PhaseRegionForceAdmissionReport
  candidate_metric_keys: tuple[str, ...]
  withheld_force_reason: str
  force_components: None
  metrics: dict[str, float]
```

Helper:

```text
build_phase_region_force_adapter_decision(
    admission: PhaseRegionForceAdmission,
    report: PhaseRegionForceAdmissionReport,
    required_metric_keys: tuple[str, ...],
) -> PhaseRegionForceAdapterDecision
```

Required behavior:

```text
report.valid must be true
report.force_admissible must be false
admission.force_admissible must be false
report/runtime_steps must remain zero
candidate face shapes must match report face shapes
required metrics must exist
force_components is always None
withheld_force_reason = "pressure_velocity_work_gate_missing"
```

The helper may return `valid=true` only for a diagnostic read decision.  It
must still return `force_admissible=false`.

## Boundary and Nonuniform Policy

The consumer must not recompute geometry from uniform `h`.  It reads the
report's `bc_type`, `grid_alpha`, `min_dx`, `max_dx`, and face shapes.

For a future pressure/velocity work gate, the consumer must additionally prove
that the pressure projection uses the same:

```text
FCCD divergence operator
face measure / density metric
boundary type
face component shapes
metric epoch
```

Until that proof exists, the consumer must withhold force arrays even when the
diagnostic report is valid.

## Vectorization Layout

The consumer should preserve array-first layout:

```text
face_component_shapes: tuple of shapes
metric keys: tuple of strings
metrics: flat scalar dict
force_components: None
```

No per-cell object graph, nonlinear optimizer, dense pressure solve, or hidden
CPU fallback belongs in this boundary.

## Tests for the Next Code Gate

The next implementable unit should test:

```text
valid report -> valid diagnostic decision, force still withheld
invalid report -> invalid decision
admission/report face-shape mismatch -> invalid decision
missing required metric -> invalid decision
force_components is always None
force_admissible remains false
```

The runtime dry-run may use the decision only as a report guard.  It must not
feed `surface_acceleration` into pressure, velocity, PPE RHS, or a time step.

## Exit Criteria Before Micro-Step

Before any micro-step or T/8 probe, a separate pressure/velocity work gate must
show:

```text
capillary work in M_f
+ pressure projection work
+ velocity correction work
close in the same discrete metric and boundary space
```

This artifact does not authorize that gate; it only prevents premature force
consumption.

## Validation

```text
git diff --check = PASS
docs/wiki WIKI count = 432
docs/wiki/code WIKI-L count = 65
targeted CHK/wiki/design scan = PASS
```

[SOLID-X] design-only; no code, runtime route, pressure/velocity coupling,
micro-step, or T/8.
