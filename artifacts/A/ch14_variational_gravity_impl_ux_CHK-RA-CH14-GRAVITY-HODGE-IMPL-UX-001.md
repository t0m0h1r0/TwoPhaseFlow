# CHK-RA-CH14-GRAVITY-HODGE-IMPL-UX-001: implementation and YAML plan

## Scope

User request: consider how to implement the variational gravity Hodge
formulation, including UX/YAML.

This is a design artifact.  It does not implement code.  The target theorem is
SP-AK / WIKI-T-165:

```text
Phi_g(m) = y^T(g m)
r_g(q)  = -T_m(q)^T d Phi_g/dm
a_g(q)  = M_f(q)^{-1} r_g(q).
```

The old nodal route

```text
buoy_v = -(rho-rho_ref)/rho * g
```

is not the production definition for the SI water-air rising bubble unless it
is proven equal to this face covector in the active metric.

## Existing Code Reading

The current route has these relevant pieces:

```text
src/twophase/simulation/ns_pipeline.py
  _advance_conservative_common_flux_stage()
  _materialise_step_fields()
  _predict_velocity_stage()
  _solve_pressure_stage()
  _correct_velocity_stage()

src/twophase/simulation/ns_step_services.py
  build_pressure_robust_buoyancy_residual_accel_faces()
  compute_ns_predictor_stage()
  solve_ns_pressure_stage()
  correct_ns_velocity_stage()

src/twophase/simulation/conservative_transport.py
  ConservativeCommonFluxTransport

src/twophase/coupling/transport_variational_capillary.py
  _negative_face_divergence_adjoint()
```

The common-flux stage already transports `psi`, density, and momentum with one
ledger.  The pressure and capillary paths already have a pressure-adjoint face
metric.  The missing layer is a first-class gravity force covector.

The current gravity placement is still split between:

```text
1. predictor body acceleration through buoy_v;
2. optional balanced-buoyancy residual face assembly;
3. force faces in the corrector for non-gravity forces.
```

The failed verification showed that toggling the pressure-history form,
`balanced_buoyancy`, or `projection_consistent_buoyancy` does not change the
root behavior.  Therefore the implementation should not patch those toggles.

## Implementation Principle

Implement gravity as a force covector service:

```text
GravityPotentialCovector
  inputs:
    q or psi at the force stage
    rho_l, rho_g
    grid coordinates
    g
    production transport-adjoint operator
    active face-mass metric M_f
  outputs:
    gravity_covector_faces r_g
    gravity_accel_faces    a_g = M_f^{-1} r_g
    diagnostics:
      adjoint_residual
      hydrostatic_scale
      face_weighted_l2
      energy_work_estimate
```

The service must be GPU-first:

```text
all array work uses backend.xp
no host loops in production
only scalar diagnostics cross host/device boundaries
```

## New Modules

### 1. transport adjoint utility

Create:

```text
src/twophase/simulation/transport_adjoint.py
```

Move or wrap the existing FCCD adjoint logic now private in
`transport_variational_capillary.py`:

```text
negative_face_divergence_adjoint(xp, fccd, nodal_covector, axis)
```

The function must continue to satisfy:

```text
<eta, -D_f F> = <(-D_f)^T eta, F>
```

for periodic, wall, and mixed boundary axes on uniform and nonuniform grids.
Capillary code can then import the shared utility.  This prevents gravity and
capillary from silently using different transport adjoints.

### 2. gravity covector service

Create:

```text
src/twophase/simulation/gravity_covector.py
```

Suggested public API:

```python
@dataclass
class GravityCovectorResult:
    covector_faces: list[Any]
    acceleration_faces: list[Any]
    face_weight_components: list[Any]
    adjoint_residual_linf: Any
    face_weighted_l2: Any

def build_variational_gravity_covector(
    *,
    xp,
    grid,
    fccd,
    div_op,
    psi,
    rho,
    rho_l: float,
    rho_g: float,
    g_acc: float,
    face_weight_components,
    coordinate_fields,
) -> GravityCovectorResult:
    ...
```

The algebra is:

```text
ell_g = g y
adj_axis = (-D_axis)^T ell_g
m_face_axis = rho_g face(1) + (rho_l-rho_g) face(psi)
r_g_axis = -m_face_axis * adj_axis
a_g_axis = r_g_axis / M_f_axis
```

The sign should be locked by tests, not by convention memory:

```text
<r_g,w> + <g y,T_m w> = 0
```

and by the single-phase hydrostatic null gate.

### 3. generalized face force diagnostics

Do not reuse capillary-only naming for gravity diagnostics.  Add either:

```text
src/twophase/simulation/force_hodge_diagnostics.py
```

or extend the existing diagnostics with neutral names:

```text
force_face_weighted_l2
gravity_adjoint_residual_linf
gravity_face_linf
gravity_hodge_weighted_l2
gravity_projection_energy_delta
```

Production must not depend on a dense Hodge solve.  Dense diagnostics are
acceptable in tests and plot-only analysis, but not in the force path.

## Pipeline Integration

### Stage placement

Use the already existing step ordering:

```text
transport q,m,p
materialise rho,mu
surface/capillary force
gravity covector force
viscous/convection predictor
pressure solve
corrector
publish conservative state
```

The gravity covector is built after `state.rho` and the current transported
`state.psi` are known, before the predictor and PPE.

### State fields

Extend `NSStepState` with:

```text
gravity_covector_face_components
gravity_accel_face_components
gravity_face_weight_components
gravity_force_diagnostics
```

These are step-local.  No persistent checkpoint state is required for the
first implementation because gravity is recomputed from saved `q`, grid,
material parameters, and face metric.  Restart invariance still must be tested.

### Predictor rule

When `gravity.formulation=variational_potential`:

```text
buoy_v = 0
do not call build_pressure_robust_buoyancy_residual_accel_faces()
require face_native_predictor_state
require projected/canonical face velocity state
```

The face predictor receives the explicit gravity impulse:

```text
predictor_face =
    carried_face
  + face_delta_from_viscous_convection
  + dt_force * gravity_accel_face
  - dt_pressure_history * pressure_history_face_delta
```

For IMEX-BDF2, use the same force factor as the BDF2 explicit term:

```text
dt_force = 2/3 dt
```

For startup/backward-Euler:

```text
dt_force = dt
```

Then reconstruct `u_star,v_star` from `predictor_face_components`.  This avoids
a nodal gravity interpolation deciding the face flux.  The first implementation
may operator-split viscosity and gravity in this order.  That choice must be
recorded in the energy ledger.

### PPE and corrector rule

Gravity must not be added again as `force_faces` in the corrector.  Its
divergence enters the PPE through the predictor faces:

```text
rhs = D_f(u_star_face) / dt + capillary/affine terms
```

The corrector then applies pressure:

```text
u_face^{n+1} = u_star_face - dt_projection * pressure_face + non_gravity_force_faces
```

where `non_gravity_force_faces` remains available for the existing capillary
path until capillary is also fully unified as a force-covector stage.  The key
rule is no double counting:

```text
gravity is either in predictor_face or in corrector force_faces, never both.
```

For the proposed route it is in `predictor_face`.

### Conservative state publication

After projection, `_publish_conservative_state()` should keep the existing
behavior:

```text
p = rho * u
```

with `rho = state.conservative_density`.  No extra gravity state is published.
The gravity energy diagnostic is part of the step ledger, not part of the
state.

## Config Model Changes

Add to `RunCfg`:

```python
gravity_formulation: str = "body_acceleration"
gravity_transport_adjoint: str = "legacy"
gravity_metric: str = "legacy"
gravity_hodge_gate: str = "off"
gravity_work_gate: str = "off"
```

Supported values:

```text
gravity_formulation:
  none
  body_acceleration          # backward-compatible legacy
  variational_potential      # SP-AK route

gravity_transport_adjoint:
  legacy
  common_flux

gravity_metric:
  legacy
  transported_face_mass

gravity_hodge_gate / gravity_work_gate:
  off
  diagnostic
  fail_close
```

Do not overload `projection_consistent_buoyancy`; keep it as legacy.

## YAML UX

Canonical rising-bubble YAML should become explicit:

```yaml
numerics:
  momentum:
    form: conservative_common_flux
    predictor:
      assembly: none
    terms:
      gravity:
        formulation: variational_potential
        transport_adjoint: common_flux
        metric: transported_face_mass
        hodge_gate: fail_close
        work_gate: diagnostic
      convection:
        spatial: uccd6
        time_integrator: imex_bdf2
      pressure:
        gradient: fccd
      viscosity:
        spatial: ccd
        time_integrator: implicit_bdf2
      surface_tension:
        formulation: pressure_jump
        source: closed_interface_riesz
```

The UX intentionally puts gravity under `momentum.terms.gravity`, not under
`projection`, because gravity is a physical energy covector.  The projection
only supplies the Hodge reaction.

For backward-compatible configs, omitting the block preserves legacy behavior:

```yaml
terms:
  gravity: { formulation: body_acceleration }
```

For `g_acc=0`, the parser may normalize to:

```text
gravity_formulation = none
```

but only when no explicit gravity block is provided.

## Validation and Fail-Close Rules

When `formulation=variational_potential`, parser/runtime must require:

```text
momentum.form = conservative_common_flux
projection.face_flux_projection = true
projection.canonical_face_state = true
projection.face_native_predictor_state = true
poisson.operator.pressure_force_contract = variational_adjoint
poisson.operator.scalar_operator_pairing = variational_operator
gravity.transport_adjoint = common_flux
gravity.metric = transported_face_mass
```

Until conservative remap of `q,m,p` is available, also require:

```text
reinitialization.schedule.every_steps = 0
grid.distribution.schedule = 0
```

or fail-close at runtime if a reinit/remap trigger occurs.

If any requirement is missing, raise a configuration error.  Do not silently
fall back to `body_acceleration`.

## Test Plan

### Config tests

Add assertions to `test_config_io_fccd.py`:

```text
ch14_rising_bubble uses variational_potential
legacy default remains body_acceleration
variational_potential rejects primitive_velocity
variational_potential rejects non-face-native projection
variational_potential rejects balanced_buoyancy predictor assembly
```

### Operator tests

Add `test_variational_gravity_covector.py`:

```text
G1 random-adjoint:
  <r_g,w> + <g y,T_m w> ~= 0
  for uniform, nonuniform, wall, periodic, periodic_wall

G2 single-phase hydrostatic:
  constant q gives zero projected velocity from rest

G3 flat two-phase:
  gravity plus admissible pressure/jump reaction has tiny Hodge residual

G4 finite initial bubble:
  Hodge norm is nonzero but bounded by physical scale
```

### Pipeline tests

Add focused tests around `compute_ns_predictor_stage()`:

```text
variational gravity sets buoy_v to zero
gravity impulse is added to predictor_face_components
corrector does not add gravity a second time
IMEX-BDF2 uses dt_force = 2/3 dt
restart recomputes identical gravity faces
```

### Smoke experiments

Run in increasing cost:

```text
1. one-step hydrostatic column
2. rising bubble N=32x64 to T=0.021
3. rising bubble N=32x64 to T=0.03 with checkpoints
4. rising bubble N=32x64 to T=0.1 if T=0.03 crosses old failure band cleanly
```

Acceptance for the first proof is not merely "no blow-up":

```text
projection energy delta <= tolerance
gravity adjoint residual <= tolerance
single-phase hydrostatic velocity ~= 0
old t ~= 0.02056 band crossed without ppe/div/face runaway
```

## GPU-First Notes

The implementation should use only vectorized face arrays:

```text
fccd.face_value(psi, axis)
negative_face_divergence_adjoint(...)
face_weight_components
xp.where / xp.asarray / xp.sum
```

Avoid:

```text
Python loops over cells
dense Hodge projection in production
host-side marching or topology loops for gravity
CPU-only diagnostics in the timestep
```

The only loops in production should be over spatial axes.

## Risks and Counterarguments

### R1. Sign convention

Risk: `r_g=-T_m^T gy` sign is easy to invert.

Mitigation: do not trust convention.  Lock sign with both the adjoint identity
and a physical single-bubble first-step direction.

### R2. Wrong mass face metric

Risk: using `rho_face` while pressure projection uses affine-jump or
phase-separated weights breaks Hodge orthogonality.

Mitigation: compute `face_weight_components` from the same active pressure
metric.  If the metric cannot be built, `variational_potential` fails closed.

### R3. Double counting gravity

Risk: adding gravity in predictor and corrector injects work twice.

Mitigation: `NSStepState` has one gravity path.  For variational gravity,
`buoy_v=0` and corrector force faces exclude gravity.

### R4. Viscosity splitting

Risk: adding gravity after the implicit viscous predictor changes the time
factorization.

Mitigation: declare the force substep and use BDF2 explicit force factor
`2/3 dt`.  Validate with energy/projection gates.  A later refinement can pass
face covectors into a monolithic viscous-force solve, but the first production
proof should prioritize metric consistency over a hidden nodal RHS.

### R5. Reinit/remap

Risk: reinit changes `q` and therefore `m`, but gravity force is built from the
wrong mass.

Mitigation: current rising-bubble variational gravity route requires
reinit/remap disabled or conservative q/m/p remap.  Runtime fail-close remains.

### R6. Dense Hodge temptation

Risk: using dense Hodge projection to "fix" gravity force.

Mitigation: Hodge solves are diagnostics and gates.  Production force is the
transport-adjoint covector; pressure projection handles the range component.

## Recommended Commit Sequence

1. Config and UX parsing.
   Add `gravity_*` RunCfg fields, parser validation, YAML update, and config
   tests.  No solver behavior change yet.

2. Transport-adjoint and covector unit layer.
   Add shared adjoint utility and `GravityPotentialCovector`; prove G1 on
   CPU/GPU-capable array paths.

3. Pipeline integration.
   Add step-state gravity faces, disable legacy buoyancy for
   `variational_potential`, add predictor-face impulse, and prevent double
   counting in corrector.

4. Diagnostics and gates.
   Add gravity diagnostics to `StepDiagnostics`, restart invariance test, and
   projection energy gate.

5. Experiments.
   Update `ch14_rising_bubble.yaml`, run N=32x64 short gates, then cross the
   old blow-up time.

This order keeps each commit testable and prevents another expensive
full-experiment rerun before the algebraic gates are in place.
