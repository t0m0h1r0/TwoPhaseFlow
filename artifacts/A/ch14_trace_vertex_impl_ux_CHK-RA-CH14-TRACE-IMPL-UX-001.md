# CHK-RA-CH14-TRACE-IMPL-UX-001

## Scope

User request: study implementation method and UX before coding.

This checkpoint translates the trace-vertex VJP theory into concrete code
seams, test slices, and YAML semantics.  It intentionally does not implement
the solver change.

## Existing Seams

The relevant existing code already provides three useful anchors:

```text
src/twophase/coupling/closed_interface_stratum.py
src/twophase/coupling/closed_interface_geometry.py
src/twophase/coupling/closed_interface_riesz.py
```

The first two are reusable.  The last one is now a conservative-transport
diagnostic: it proves the Riesz identity for
`T_c(u)=-D_f(psi_f u_f)`, but it is not the final sharp-trace law.

The pressure/corrector seam already supports external face cochains:

```text
div_op.pressure_fluxes(..., capillary_jump_components=face_components)
```

This is the right seam for `s_K`; the new law should not be encoded as a fake
scalar curvature field or as a new `curvature_method`.

The interface stage also already records reinitialization projection fields.
The new law needs one additional state-level endpoint:

```text
psi_transport_endpoint = psi after physical transport and before reinit
```

When no reinit is triggered, this equals the current `state.psi`.  When reinit
is triggered, it is `last_reinit_projection["psi_before"]`.

## Code Architecture

### 1. Trace Graph

Add a shape-free trace graph layer, preferably in a new module:

```text
src/twophase/coupling/closed_interface_trace.py
```

Public objects:

```text
TraceVertex2D
TraceSegment2D
TraceComponent2D
TraceGraph2D
build_trace_graph_2d(...)
```

Requirements:

```text
edge crossings are keyed by global grid-edge id, not per-cell duplicates;
segments are oriented consistently with the existing shoelace sign;
threshold touches fail closed;
ambiguous marching-squares cells fail closed in the first production theorem;
components are recorded explicitly for one or more closed loops.
```

The current private helpers in `closed_interface_geometry.py` already compute
crossing vertices and shoelace derivatives.  The implementation should expose
that geometry as a graph instead of recomputing unrelated structures.

### 2. Vertex Geometry Differentials

Extend or add:

```text
trace_surface_vertex_covectors_2d(graph, sigma)
trace_component_area_vertex_covectors_2d(graph)
```

The surface covector for segment `a -> b` is:

```text
g_a += -sigma t,
g_b +=  sigma t,
t = (z_b - z_a)/|z_b-z_a|.
```

The area covector for component vertex `k` is:

```text
g_k += 0.5 R_-90 (z_{k+1}-z_{k-1})
```

with the sign matched to the implementation's oriented-area convention.

Tests:

```text
move trace vertices directly and finite-difference S_h(z) and V_h(z);
check rigid translation gives delta S_h ~= 0 and delta V_h ~= 0;
check topology and component orientation are stable on the fixed stratum.
```

### 3. Trace Velocity Map

Add:

```text
src/twophase/coupling/closed_interface_trace_velocity.py
```

Public objects:

```text
TraceVelocityMap
ReconstructedNodalP1TraceVelocityMap
trace_vertex_velocities_from_faces(...)
pullback_trace_vertex_covectors_to_faces(...)
```

First concrete map:

```text
reconstructed_nodal_p1:
  face DOFs -> nodal vector velocity -> P1 edge interpolation -> trace vertices.
```

This uses the same linear reconstruction idea as
`reconstruct_nodes_from_faces`, but the VJP must use the exact transpose of
that reconstruction.  Do not handwave this step.  The required test is:

```text
sum_z g_z . (C_K u_f)_z == sum_f (C_K^T g)_f u_f
```

for random face velocities and random vertex covectors, including periodic
and non-periodic boundary choices supported by the solver.

If this candidate fails the rigid-motion, tangential, or conservation gates,
the next candidates are `direct_face_p1` or a mimetic/Whitney trace map.  The
fallback is never damping, smoothing, curvature caps, or range deletion.

### 4. Trace Riesz Cochain

Add a new module instead of mutating the old diagnostic in place:

```text
src/twophase/coupling/closed_interface_trace_riesz.py
```

Public object:

```text
ClosedInterfaceTraceRieszCochain
closed_interface_trace_riesz_cochain(...)
```

The object should contain:

```text
trace_graph
surface_vertex_covectors
volume_vertex_covectors_by_component
surface_force_covector_faces     = -C_K^T d_z(sigma S_h)
volume_force_covector_faces      =  C_K^T d_z V_m
surface_acceleration_faces       = M_f^{-1} surface_force_covector_faces
volume_reaction_acceleration_faces = M_f^{-1} volume_force_covector_faces
face_weight_components
work/residual diagnostics
```

The old `closed_interface_riesz.py` should remain as negative/diagnostic
knowledge until the new trace path passes all gates; later it can be renamed
or its docstring can state "conservative transport diagnostic" explicitly.

### 5. Augmented Hodge Projector

The one-component helper in `interface_projection_diagnostics.py` is not
general enough for the theorem.  Add a projection helper that accepts multiple
component-reaction columns:

```text
weighted_augmented_hodge_projection(
    surface_components=s_K,
    reaction_columns=[B_1, ..., B_M],
    div_op=D_f,
    face_weight_components=M_f,
)
```

It returns:

```text
corrected_capillary_components = s_K - B mu
range_components               = Pi_R(corrected_capillary_components)
hodge_residual_components      = corrected_capillary_components - Pi_R(...)
normal_equation_residuals
orthogonality_residuals
rank diagnostics
```

This is the code form of:

```text
H_X s = H_R(s - B mu_*),  X=[A_fG_f B].
```

The first implementation can use the existing dense diagnostic Hodge matrix
for theorem tests.  Production can later replace only the linear algebra
implementation with a Schur form, preserving the same residual contract.

### 6. Runtime Wiring

Add a capillary-source selector to the solver runtime:

```text
capillary_force_source: curvature_jump | closed_interface_riesz
closed_interface_options: dict-like typed settings
capillary_reaction_projection: pressure_component_hodge
```

For `closed_interface_riesz`, the pressure stage must not ask the scalar jump
context to invent curvature.  Instead:

```text
1. choose psi_transport_endpoint;
2. build s_K and B_K from the trace graph and C_K;
3. apply pressure/component reaction projection to obtain corrected_capillary_components;
4. add D_f(corrected_capillary_components) to the PPE RHS;
5. pass the same corrected_capillary_components to
   div_op.pressure_fluxes(..., capillary_jump_components=...);
6. store full pressure-face history exactly as the current affine-jump path does.
```

The corrector then applies:

```text
u_f^{n+1} = u_f^* - dt A_fG_f p + dt corrected_capillary_components
```

with the existing code sign convention encoded by
`pressure_fluxes(..., capillary_jump_components=...)`.  The sign must be
locked by a power test:

```text
released-from-rest KE coefficient > 0 for a noncritical trace;
component-constrained discrete critical trace gives no Hodge acceleration.
```

## Test Slices

Implement in this order:

```text
1. Trace graph and vertex geometry
   tests: topology, direct vertex FD, orientation, rigid translation.

2. Trace velocity map and VJP
   tests: C_K dot-product identity, boundary variants, zero-normal/tangential gate.

3. Trace Riesz cochain
   tests: d_zS_h[C_K u] + <s_K,u>_M = 0 and
          d_zV_m[C_K u] - <B_m,u>_M = 0.

4. Augmented Hodge projector
   tests: M_f orthogonality, D_f residual, multi-component rank diagnostics,
          sampled-circle convergence recorded as trend only.

5. Runtime YAML parser
   tests: accepted strict config, legacy config unchanged, invalid mixed keys rejected.

6. Runtime source integration
   tests: one-step noncritical release, static/discrete-critical silence,
          pressure-face history sign lock.

7. ch14 validation
   tests: N=32,T=1 static/oscillating with pressure, velocity vector, psi snapshots;
          reinit-separated geometry ledger.
```

## YAML UX

Existing configurations keep their meaning by default:

```yaml
capillary_force:
  formulation: pressure_jump
  source: curvature_jump
  curvature: face_implicit
poisson:
  operator:
    capillary_range_projection: component_hodge_augmented
```

The new physical law is explicit:

```yaml
capillary_force:
  formulation: pressure_jump
  source: closed_interface_riesz
  closed_interface:
    trace_space: p1_marching_squares
    topology: fail_closed
    ambiguous_cells: fail
    surface_energy: sharp_length
    component_volume: oriented_area
    trace_velocity:
      map: reconstructed_nodal_p1
      endpoint: before_reinit
    diagnostics:
      gates: strict
poisson:
  operator:
    capillary_reaction_projection: pressure_component_hodge
```

Semantics:

```text
source
  chooses the raw capillary cochain construction.

closed_interface
  chooses the sharp trace geometry and admissible trace velocity map.

capillary_reaction_projection
  removes pressure and component reactions only; it does not delete the force.

capillary_range_projection
  remains legacy scalar-jump vocabulary and is rejected for closed_interface_riesz.
```

Fail-closed rules for `source: closed_interface_riesz`:

```text
requires formulation: pressure_jump;
requires poisson coefficient: phase_separated;
requires poisson interface_coupling: affine_jump;
requires face-native/canonical face state for the first runtime path;
rejects curvature, curvature_cap, smoothing, damping, Rayleigh scaling;
rejects capillary_range_projection and boolean aliases;
rejects benchmark-name branches;
requires capillary_reaction_projection: pressure_component_hodge;
requires diagnostics.gates: strict for production runs.
```

The UX names theorem objects.  It should not ask users to choose "circle" or
"ellipse", and it should not expose knobs that tune the answer to a benchmark.

## Verdict

Implementation should proceed through the trace graph, trace velocity VJP, and
Riesz cochain first.  Runtime wiring comes only after the face-space work and
Hodge gates pass.

The YAML should make the mathematical contract visible and reject mixed legacy
settings.  The central user-facing distinction is:

```text
curvature_jump           = legacy scalar jump source;
closed_interface_riesz   = surface-energy virtual-work source;
capillary_range_projection = legacy scalar-jump projection vocabulary;
capillary_reaction_projection = theorem-grade pressure/component reaction policy.
```

## Validation

Docs/design checkpoint only.

[SOLID-X] implementation/UX design only; no production source/config/result
change, no tested implementation deleted, no FD/WENO/PPE fallback, damping/CFL
workaround, curvature cap, smoothing, benchmark-name branch, blanket
`c -> Pi_R c`, or QP-as-physics path introduced.
