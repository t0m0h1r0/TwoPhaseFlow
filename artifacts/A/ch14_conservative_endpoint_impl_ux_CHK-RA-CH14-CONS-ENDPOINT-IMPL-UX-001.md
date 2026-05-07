# CHK-RA-CH14-CONS-ENDPOINT-IMPL-UX-001

## Question

Design the implementation and YAML UX for the conservative face-psi endpoint
capillary law, with explicit attention to:

1. CCD/FCCD/UCCD6 connectivity,
2. compatibility with the current overall ch14 scheme,
3. GPU-first execution,
4. fail-close diagnostics rather than fallback behavior.

## Current Code Reading

The current YAMLs already use:

```yaml
surface_tension:
  formulation: pressure_jump
  source: closed_interface_riesz
projection:
  face_flux_projection: true
  canonical_face_state: true
  face_native_predictor_state: true
  poisson:
    operator:
      discretization: fccd
      coefficient: phase_separated
      interface_coupling: affine_jump
      capillary_reaction_projection: pressure_component_hodge
```

The parser already fail-closes on the most dangerous combinations:
`closed_interface_riesz` requires `pressure_jump`, rejects `curvature`, rejects
`capillary_range_projection`, and requires
`capillary_reaction_projection: pressure_component_hodge`.

However, `solve_ns_pressure_stage` currently imports and calls
`closed_interface_trace_riesz_cochain` and `trace_component_hodge_projection`
for `capillary_force_source == "closed_interface_riesz"`.  That is no longer
the selected production endpoint.  The selected endpoint is the conservative
face-psi transport VJP:

```text
T_f(q)u_f = -D_f(P_f q u_f).
```

Therefore the implementation task is not a new scalar curvature option.  It is
to replace the trace-vertex production call with the conservative endpoint
cochain and to project reactions using the actual FCCD/affine-jump pressure
range.

## Implementation Architecture

### 1. Coupling Layer: Endpoint-Exact Cochain Builder

Keep the endpoint pullback in `src/twophase/coupling/closed_interface_riesz.py`,
but make the production object explicit:

```text
ConservativeEndpointRieszCochain
  psi_endpoint
  surface_nodal_covector          d_q(sigma S_h)
  volume_nodal_covectors          [d_q V_m,h]
  surface_acceleration            s=-M_f^{-1}T_f^T dE
  volume_reaction_accelerations   B_m=M_f^{-1}T_f^T dV_m
  face_weight_components          diagnostic M_f only
  endpoint_metadata               conservative_psi, before_reinit, fccd
```

The existing `closed_interface_riesz_cochain` already builds the surface
cochain with `_negative_transport_adjoint_force_covector`, which is the right
VJP skeleton.  The production refinement is:

```text
surface_nodal = d_q(sigma S_h)
volume_nodal[m] = d_q V_m,h
surface_force = -T_f^T surface_nodal
volume_force[m] = T_f^T volume_nodal[m]
surface_acceleration = surface_force / M_f
volume_reaction_acceleration[m] = volume_force[m] / M_f
```

The builder must use `state.psi_transport_endpoint`, not post-reinit `state.psi`.
If `psi_transport_endpoint` is absent while source is
`closed_interface_riesz`, the step fails closed because the work endpoint is
undefined.

### 2. Geometry Kernels: GPU-First P1 Functionals

The surface gradient is already available as a vectorized `xp` implementation
through `marching_squares_surface_energy_gradient_2d`.  The volume gradient in
`closed_interface_geometry.liquid_area_gradient_2d` still uses host loops and
`array_to_numpy`; it is acceptable for diagnostic probes, but not for a
GPU-first production step.

Production needs an `xp` vectorized P1 area gradient:

```text
marching_squares_liquid_area_gradient_2d(xp, grid, psi, threshold)
```

It should share the same cell-corner arrays and edge-crossing masks as the
surface-energy kernel.  It must return device arrays when `xp` is CuPy and must
avoid per-cell Python loops and host transfers.  The first implementation may
support one connected component for the production ch14 droplet path, but the
API must be list-shaped for `V_m`; if multiple components are detected before
per-component GPU labels exist, strict mode fails closed.

### 3. Projection Layer: Use the Actual Pressure Range

Do not use dense diagnostic Hodge projection in production.  The dense
`weighted_hodge_decomposition` is useful for small tests, but GPU-first
production must project through the same range as the corrector:

```text
G_A p = div_op.pressure_fluxes(p, rho, zero_jump_pressure_flux_kwargs)
R     = range(G_A)
```

For an arbitrary face cochain `c`, the range projection should solve:

```text
D_f G_A p = D_f c
Pi_R c = G_A p
h_R(c) = c - Pi_R c
```

with the existing PPE solver after temporarily zeroing the interface jump
context.  This mirrors `capillary_jump_range_projection`, but it takes
external face cochains instead of reconstructing a scalar curvature jump from
`pressure_fluxes(0, rho, ...)`.

Required production helper:

```text
project_external_capillary_cochain(
  raw_components,
  component_reaction_components,
  div_op,
  ppe_solver,
  rho,
  pressure_flux_kwargs,
  face_weights
) -> CapillaryReactionProjection
```

Algorithm:

```text
raw_range = Pi_R(raw)
raw_hodge = raw - raw_range

for each B_m:
  B_range[m] = Pi_R(B_m)
  B_hodge[m] = B_m - B_range[m]

Solve beta from:
  (B_i^H, B_j^H)_M beta_j = (raw_hodge, B_i^H)_M

corrected_components = raw_components - sum_m beta_m B_hodge[m]
hodge_components     = raw_hodge     - sum_m beta_m B_hodge[m]
range_components     = corrected_components - hodge_components
```

`corrected_components`, not `hodge_components` alone, must be passed to
`pressure_fluxes(..., capillary_jump_components=corrected_components)`.  This
preserves the pressure representative while leaving the final projected face
acceleration equal to the component-constrained Hodge drive.

### 4. Pressure Stage Wiring

In `src/twophase/simulation/ns_step_services.py`, the
`closed_interface_source` branch should become:

```text
cochain = closed_interface_riesz_cochain(
  xp=xp,
  grid=jump_grid,
  psi=state.psi_transport_endpoint,
  fccd=div_op._fccd,
  sigma=physical_jump_sigma,
  rho=state.rho,
)

projection = project_external_capillary_cochain(
  raw_components=cochain.surface_acceleration,
  component_reaction_components=cochain.volume_reaction_accelerations,
  div_op=div_op,
  ppe_solver=ppe_solver,
  rho=state.rho,
  pressure_flux_kwargs=zero_jump-compatible kwargs,
  face_weights=capillary_face_hodge_weights(...),
)

rhs += div_op.divergence_from_faces(projection.corrected_components)
pressure_flux_eval_kwargs["capillary_jump_components"] = projection.corrected_components
```

The trace-vertex modules remain available as diagnostic/future trace-primary
research code, but the runtime source `closed_interface_riesz` must no longer
call them.

### 5. Corrector Compatibility

The current face-native corrector can remain structurally unchanged if
`state.pressure_correction_face_components` is produced during pressure solve.
The implementation must add a guard:

```text
if capillary_force_source == "closed_interface_riesz"
and face_flux_projection recomputes pressure faces without
state.pressure_correction_face_components:
    fail closed
```

Otherwise the corrector can accidentally recompute pressure faces with
`sigma=0` and without the capillary cochain.  The canonical ch14 settings
already use `face_native_predictor_state` and preserve the stored face
correction; the guard makes this a contract rather than an assumption.

## CCD/FCCD/UCCD6 Compatibility

The implementation is compatible with the current scheme only if these objects
are shared, not duplicated:

```text
P_f   = FCCD face interpolation used in T_f(q)u_f
D_f   = FCCD divergence used by transport, PPE RHS, and Hodge residual
G_A   = div_op.pressure_fluxes(... zero jump ...) used by the corrector
M_f   = face metric/kinetic pairing used only for reaction orthogonality
u_f   = projected face state passed to UCCD6 momentum
CCD   = viscosity acts on the corrected velocity field after projection
```

This favors a simulation-layer projection helper over a coupling-layer dense
Hodge solve.  The coupling layer should not independently define pressure
range by `M_f^{-1}D_f^T` unless that object is proven identical to the actual
`pressure_fluxes` range for the active coefficient, nonuniform grid, and
affine-jump interface coupling.

For UCCD6, the capillary law remains a pressure/corrector face acceleration,
not a convection source.  The sequence is:

```text
transport psi with projected u_f
record psi_transport_endpoint before reinit
materialize rho, mu from current interface state
predict momentum with CCD/UCCD6/viscosity
build conservative endpoint capillary cochain at psi_transport_endpoint
solve PPE with D_f(corrected capillary cochain)
correct face velocity using the same corrected capillary cochain
reconstruct nodes and apply wall hooks
```

This keeps capillarity in the same place as pressure jump physics and avoids
injecting it into UCCD6 convection or CCD viscosity.

## GPU-First Requirements

Production must avoid:

```text
array_to_numpy on step-sized fields,
dense D matrices,
per-face/per-cell Python loops in the hot path,
host least-squares for anything larger than the small component matrix,
CPU-only graph traversal unless diagnostics explicitly request it.
```

Production may use:

```text
xp vectorized marching-squares masks,
FCCD face_value and face_divergence,
existing PPE solver calls for range projection,
device-side weighted dot products,
xp.linalg for the tiny component-reaction normal matrix,
backend.asnumpy only when recording scalar diagnostics.
```

Strict diagnostics can run additional CPU graph checks, but they must be
labelled as diagnostics and must not become the default GPU production path.

## UX Contract

Keep the existing user-facing source name for continuity, but redefine it as
the conservative endpoint law:

```yaml
surface_tension:
  formulation: pressure_jump
  source: closed_interface_riesz
  closed_interface:
    endpoint: conservative_psi
    transport_vjp: fccd_face_psi
    surface_energy: p1_marching_squares_length
    component_volume: p1_liquid_area
    topology: fail_closed
    diagnostics:
      mode: strict
      virtual_work: sampled
      profile_sensitivity: report
projection:
  face_flux_projection: true
  canonical_face_state: true
  face_native_predictor_state: true
  poisson:
    operator:
      discretization: fccd
      coefficient: phase_separated
      interface_coupling: affine_jump
      capillary_reaction_projection: pressure_component_hodge
```

The nested `closed_interface` block may be optional because the defaults are
fully determined by `source: closed_interface_riesz`.  It is valuable as
documentation and for fail-close validation.  The parser should reject:

```text
curvature,
curvature_cap,
smoothing,
damping,
Rayleigh scaling,
benchmark-name source branches,
capillary_range_projection,
boolean projection aliases,
trace_velocity / trace_space fields under the production source,
source alias trace_riesz unless an explicit experimental trace endpoint is added.
```

The source aliases should be tightened:

```text
closed_interface        -> closed_interface_riesz
conservative_riesz      -> closed_interface_riesz
conservative_endpoint   -> closed_interface_riesz
trace_riesz             -> reject for production
```

## Diagnostics UX

The step diagnostics should distinguish endpoint law, projection, and reinit:

```text
capillary_endpoint_type
capillary_endpoint_riesz_residual
capillary_endpoint_volume_riesz_residual
capillary_projection_range_residual
capillary_component_hodge_weighted_l2
capillary_hodge_weighted_l2
capillary_corrector_sign_power
capillary_static_critical_residual_ratio
capillary_profile_sensitivity_l2
reinit_surface_energy_delta
reinit_linf_delta
```

Only scalar diagnostics should be transferred to host each step.  Optional
field outputs may include:

```text
fields/psi_before_transport
fields/psi_after_transport_before_reinit
fields/psi_after_reinit
fields/capillary_corrected_face_x
fields/capillary_corrected_face_y
fields/capillary_hodge_face_x
fields/capillary_hodge_face_y
```

The face fields should be opt-in because they are large on GPU.

## Acceptance Tests

Implementation should add targeted tests in this order:

1. Config parse: `closed_interface_riesz` defaults to
   `endpoint=conservative_psi` and rejects `trace_riesz`, `curvature`,
   `capillary_range_projection`, and missing face-native projection.
2. Conservative VJP work: random face velocities satisfy
   `dE[T_f u] + <s,u>_M` and `dV[T_f u] - <B,u>_M` within tolerance.
3. External projection: a manufactured pressure-range cochain projected through
   `pressure_fluxes` gives zero Hodge component on CPU and GPU.
4. Component reaction: `corrected_components` preserve `D_f raw` and produce
   `B^TM_fh=0`, `D_fh=0`.
5. Corrector sign: release from rest gives positive kinetic work for decreasing
   surface energy.
6. Runtime seam: `solve_ns_pressure_stage` passes the same
   `corrected_components` to PPE RHS and `pressure_fluxes`.
7. GPU smoke: closed-interface source runs without host-loop geometry in the
   hot path and matches CPU diagnostics within tolerance.
8. ch14 N=32 static/oscillating: static uses discrete-critical/convergence
   gates; oscillating produces nonzero capillary motion; reinit endpoint fields
   are split.

## Decision

Implement `closed_interface_riesz` as conservative endpoint Riesz, not
trace-vertex Riesz.  The decisive compatibility rule is:

```text
the cochain builder, Hodge reaction projection, PPE source, pressure flux
corrector, and UCCD6 face state must all share the same FCCD face complex.
```

The trace-vertex route remains research code for a future trace-primary solver.
It should not be the production implementation behind the current YAML source.

[SOLID-X] Design artifact only.  No production solver/config/result behavior is
changed, no tested implementation is deleted, and no FD/WENO/PPE fallback,
damping/CFL workaround, curvature cap, smoothing, benchmark branch, blanket
projection, or QP-as-physics route is introduced.
