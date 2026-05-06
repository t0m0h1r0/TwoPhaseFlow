# CHK-RA-CH14-IMPL-METHOD-001: implementation method for variational capillarity

Date: 2026-05-07
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`
Scope: decide how to implement the rigorous capillary-force contract without
turning it into a curvature tune, benchmark branch, or projection workaround.
This is a design/documentation slice; no solver code is changed here.

## Current Code Integration Map

The existing pressure-jump path has three important seams:

```text
src/twophase/coupling/interface_stress_closure.py
  build pressure-jump/interface context and evaluate signed face jump gradients.

src/twophase/simulation/divergence_ops.py
  pressure_fluxes(..., capillary_jump_components=...)
  applies face capillary cochains by subtracting them from pressure fluxes.

src/twophase/simulation/ns_step_services.py
  solve_ns_pressure_stage(...)
  chooses capillary_range_projection mode and stores pressure/capillary faces.

src/twophase/simulation/interface_projection_diagnostics.py
  constructs range projection, one-component augmented projection, weights,
  and diagnostics for face cochains.

src/twophase/coupling/transport_variational_capillary.py
  already contains nodal surface-energy gradients and a transport-adjoint
  face work map for the level-set transport equation.
```

The new implementation should not be squeezed into "curvature" semantics.
It should produce a raw face cochain `s` and component columns `B`, then hand
those to a same-metric augmented Hodge projector.

## Naming And Configuration

Do not add a benchmark-specific option.  The clean public contract is a new
capillary source/model selector under the existing capillary force section:

```yaml
numerics:
  physical_time:
    momentum:
      capillary_force:
        formulation: pressure_jump
        source: closed_interface_riesz
```

`curvature` remains a legacy scalar-jump source.  `source` selects how the
capillary face cochain is constructed.  Proposed values:

```text
curvature_jump          existing scalar curvature pressure jump
closed_interface_riesz  fixed-stratum virtual-work cochain
```

`capillary_range_projection` is a reaction/projection option and should not
also select the force law.  Once `closed_interface_riesz` is active, the only
accepted production projection is the weighted augmented projection with
component columns from the same geometry.  The legacy
`component_hodge_augmented` remains a fallback/negative-control mode for the
old scalar cochain, not the final physics.

If a minimal first slice needs less config churn, an internal runtime flag can
route the diagnostic path, but the final YAML contract should use `source`,
not a fake `curvature=closed_interface_riesz`.

## New Objects

### `ClosedInterfaceStratum`

Suggested module:

```text
src/twophase/coupling/closed_interface_stratum.py
```

Responsibilities:

```text
input: grid, psi, phase_threshold
output: stratum hash, cut masks, crossing coordinates, local edge coordinates,
        segment pairing/orientation, component labels when available.
```

Initial implementation:

```text
1. Reuse the existing marching-squares local crossing logic as a starting
   point, because it already computes crossing locations and derivatives.
2. Add explicit stratum hashing: cut edge mask, crossing count, ambiguous-cell
   pairing rule, and component label summary.
3. For ambiguous four-crossing cells, use one deterministic decider and include
   its decision in the hash; derivative probes fail closed if the decision
   changes.
4. Do not smooth/cap to avoid stratum changes.  Report invalid derivative.
```

The first diagnostic version may assemble per-cell segments without global
component ordering for `S_h`.  Component volumes need connected labels before
production.

### `TraceGeometryFunctional`

Suggested module:

```text
src/twophase/coupling/closed_interface_geometry.py
```

Responsibilities:

```text
S_h(q)          sharp trace length
dS_h/dpsi      nodal covector on the fixed stratum
V_m,h(q)        component areas
dV_m,h/dpsi    component volume covectors
geometry residuals against centered finite differences
```

Reuse possible:

```text
marching_squares_surface_energy_gradient_2d
p2_trace_surface_energy_2d
p2_trace_surface_energy_gradient_2d
```

but do not accept them as production by name.  They become reusable kernels
only after stratum hashing, volume covectors, and finite-difference residuals
are attached to the same `ClosedInterfaceStratum`.

First implementation slice:

```text
S_h and dS_h/dpsi for P1 segments,
single global liquid volume covector dV/dpsi,
finite-difference derivative tests on frozen stratum.
```

Production slice:

```text
multi-component V_m,h and B columns,
component-rank diagnostics,
arbitrary closed components.
```

### `TransportLinearization`

Suggested module:

```text
src/twophase/coupling/interface_transport_vjp.py
```

Responsibilities:

```text
T_K^T g for the actual pre-reinit transport endpoint.
```

The existing helper

```text
_negative_face_divergence_adjoint(...)
transport_variational_pressure_jump_gradient(...)
```

already maps a nodal covector through the level-set transport equation
`psi_t=-D_f(psi_f u_f)`.  The new path should factor that map into a reusable
VJP that returns a face covector, not a pressure-jump curvature surrogate.

Diagnostic scaffold:

```text
1. analytic VJP using the same `-D_f(psi_f u_f)` operator as existing code,
2. dot-product test against finite-difference `Phi_K(q, eps w, dt)`,
3. fail closed if the stratum hash changes under +/- eps.
```

Do not use a geometry-only velocity interpolation that differs from the actual
transport equation; that would violate the power identity even if `S_h` is
exact.

### `CapillaryRieszCochain`

Suggested module:

```text
src/twophase/coupling/capillary_riesz_cochain.py
```

Responsibilities:

```text
build raw face cochain s,
build component columns B,
report Riesz work residuals,
return face components in the same convention accepted by
divergence_ops.pressure_fluxes(..., capillary_jump_components=...).
```

Important sign task:

```text
pressure_fluxes computes face = coeff * grad(p) - capillary_jump_components.
capillary_jump_range_projection currently recovers c by evaluating zero
pressure flux and negating it.
```

Therefore the new provider must include a sign-lock unit test:

```text
dE_h[T_K a_cap] < 0
```

on a release-from-rest noncritical perturbation.  Passing projection residuals
alone is insufficient.

### `AugmentedCapillaryHodgeProjector`

Suggested module:

```text
src/twophase/simulation/capillary_hodge_projector.py
```

or a split of the current `interface_projection_diagnostics.py`.

Responsibilities:

```text
input: raw face cochain s_components, component columns B_components,
       div_op, ppe_solver, rho, pressure_flux_kwargs, M_f weights.
output: reaction projection Pi_X s, quotient h, corrected cochain for
        production sign convention, projection diagnostics.
```

Do not keep this as a one-component beta formula.  Generalize from:

```text
beta = <h_c,h_b>_M / <h_b,h_b>_M
```

to the small dense normal equation:

```text
H_B^T M_f H_B mu = H_B^T M_f h_s,
H_B = (I-Pi_R)B,
h_s = (I-Pi_R)s.
```

This uses existing PPE range projection as a black box for `Pi_R`, then solves
only the component Schur complement in dense CPU/GPU arrays.  The vector result
is unique even if coefficients are rank deficient; use a pseudoinverse or
rank-revealing solve and report rank.

## Implementation Slices

### Slice 1: Geometry Diagnostic, No Production Force

Files:

```text
src/twophase/coupling/closed_interface_stratum.py
src/twophase/coupling/closed_interface_geometry.py
src/twophase/tests/test_closed_interface_geometry.py
```

Acceptance:

```text
stratum hash stable under small perturbations,
S_h finite-difference residual converges,
V_h finite-difference residual converges,
ambiguous/topology-changing probes fail closed,
CPU tests pass.
```

This slice does not touch `ns_step_services`.

### Slice 2: Transport VJP Diagnostic

Files:

```text
src/twophase/coupling/interface_transport_vjp.py
src/twophase/tests/test_interface_transport_vjp.py
```

Acceptance:

```text
(T^T g)^T w == g^T(T w) within tolerance,
uses the same face transport operator as the solver,
stratum-changing finite differences fail closed,
no reinit leg is included.
```

### Slice 3: Riesz Cochain Diagnostic

Files:

```text
src/twophase/coupling/capillary_riesz_cochain.py
src/twophase/tests/test_capillary_riesz_cochain.py
```

Acceptance:

```text
s^T M_f w + dE_h[T w] ~= 0,
b_m^T M_f w - dV_m,h[T w] ~= 0,
face arrays match div_op pressure-flux shapes,
sign-lock diagnostic reports expected direction but does not alter solver.
```

### Slice 4: General Augmented Projection

Files:

```text
src/twophase/simulation/capillary_hodge_projector.py
src/twophase/tests/test_capillary_hodge_projector.py
```

Acceptance:

```text
old one-component test remains a special case,
multiple B columns handled with rank diagnostics,
X^T M_f h residual is small,
range_projected force deletion is not used for production.
```

### Slice 5: Explicit Experimental Runtime Mode

Files:

```text
src/twophase/simulation/config_constants.py
src/twophase/simulation/config_models.py
src/twophase/simulation/config_run_layout_sections.py
src/twophase/simulation/config_run_operator_sections.py
src/twophase/simulation/ns_runtime_config.py
src/twophase/simulation/ns_step_services.py
src/twophase/tests/test_config_io_fccd.py
src/twophase/tests/test_ns_pipeline_fccd.py
```

Acceptance:

```text
new `capillary_force.source=closed_interface_riesz` parses fail-closed,
requires pressure_jump + affine_jump + face_flux_projection,
requires augmented Hodge projection,
stores diagnostics without changing legacy default,
one-step static/dynamic probes run.
```

The mode should be explicit at first.  Do not make it `auto` until the full
static/dynamic/reinit validation ladder passes.

### Slice 6: Ch14 Validation And Visuals

Files:

```text
experiment/ch14/config/_tmp_* or promoted config after proof
experiment/ch14/results/*
artifacts/A/*
```

Remote-first commands:

```text
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make cycle EXP=<config>
SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test PYTEST_ARGS='<targets>'
```

Acceptance:

```text
N=32,T=1 static: KE and quotient Hodge residual near zero,
N=32,T=1 oscillating no-reinit: nonzero drive and improved Rayleigh Hessian,
N=32,T=10 oscillating: phase judged with q^n->q_T and q_T->q^{n+1} split,
2D snapshots, velocity vectors, pressure fields regenerated,
no damping/CFL/cap/smoothing fallback introduced.
```

## Key Design Decisions

### Use Existing Transport Kernels Carefully

The existing `transport_variational_capillary.py` is useful, but only as a
kernel source.  The previous P2/transport route failed production gates because
it did not close the full same-metric `s,B,X` diagram.  The implementation
must therefore extract reusable VJP/gradient pieces and wrap them with:

```text
fixed stratum hash,
volume covectors,
M_f Riesz residuals,
augmented projection,
sign-lock,
reinit ledger.
```

### Keep Diagnostics And Production Separable

Diagnostic finite differences may be slow and CPU-oriented if they are not in
the production step.  Production arrays must follow the existing `backend.xp`
path and avoid benchmark-specific branches.  Any host transfer in the solver
hot path must be justified as diagnostic-only or moved out before acceptance.

### Treat Component Projection As A Schur Complement

Do not hand-code special cases beyond tests.  The one-component formula is:

```text
mu = <h_s,h_b>_M / <h_b,h_b>_M.
```

The implementation should use the multi-column formula from the start:

```text
mu = (H_B^TM_fH_B)^+ H_B^TM_fh_s.
```

This makes the single-component path a regression test, not the architecture.

### Add Sign-Lock Before Ch14 Runs

Because `pressure_fluxes` subtracts `capillary_jump_components`, the sign can
look correct in diagnostics while being reversed in the corrector.  Before any
T=1/T=10 judgement, add a unit/integration sign test that checks energy power
for a synthetic noncritical trace.

## Rejected Implementation Shortcuts

Do not implement:

```text
closed_interface_riesz as a curvature_method alias only,
Rayleigh frequency scalar rescaling,
component beta tuning,
static/oscillating config branches,
circle/ellipse classifiers,
range projection as production force replacement,
reinit projection as capillary work,
curvature cap/smoothing/damping/CFL workarounds,
PPE fallback to hide the cochain residual.
```

## Recommended Next Code Commit

The first actual code commit should implement only Slice 1:

```text
ClosedInterfaceStratum + TraceGeometryFunctional + finite-difference tests.
```

It is the smallest code change that directly tests the selected theory and
does not risk changing production physics.  If Slice 1 fails, the error is in
geometry/stratum logic.  If it passes, Slice 2 can test transport adjointness
without entangling PPE, pressure signs, or ch14 validation.

[SOLID-X] Implementation-method artifact only; no production source/config/result
change, no tested implementation deleted, no FD/WENO/PPE fallback, damping,
CFL workaround, curvature cap, smoothing, blanket `c -> Pi_R c`,
benchmark-name branch, or QP-as-physics path introduced.
