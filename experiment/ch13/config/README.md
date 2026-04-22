# ch13 Experiment YAML Design

The ch13 YAML schema is organized by *what the setting means*, not by where the
current Python implementation stores it.

## Top-Level Sections

- `grid`: computational mesh size, physical domain, boundary type, and mesh distribution.
- `interface`: the full lifecycle of the phase interface.
- `physics`: material properties and physical constants.
- `run`: wall-clock experiment controls such as final time and diagnostics.
- `numerics`: time integrators, equation terms, projection semantics, and linear solvers.
- `output`: result directory, snapshots, and figure recipes.

## Interface Lifecycle

`interface` groups settings that must be reasoned about together:

- `thickness`: how the CLS thickness is measured (`nominal`, `local`, `xi_cells`).
- `geometry.curvature`: interface-geometry reconstruction used to obtain κ.
  `psi_direct_hfe` lives here because HFE is a steep-interface geometry
  treatment, not a momentum-force switch.
- `reinitialization`: geometry restoration algorithm in pseudo-time; this is not physical time integration.

The physical-time tracking choice lives under `numerics.interface.tracking`,
because it controls the interface transport strategy rather than the interface
state itself.

Tracking redistance frequency is intentionally separate from reinitialization
frequency:

- `numerics.interface.tracking.redistance.schedule.every_steps`: phi-primary
  tracking cleanup while transporting the interface in physical time.
- `interface.reinitialization.schedule.every_steps`: full CLS profile restoration
  in pseudo-time after advection.

This follows WIKI-X-027: interface advection and reinitialization use different
time axes and should not be placed as sibling `run` knobs or mixed in one
`interface` bucket.

## Grid Distribution

`grid.distribution` owns mesh non-uniformity:

- `type: uniform`: no interface-fitted concentration, `alpha` is ignored.
- `type: interface_fitted`: concentrate cells around the interface.
- `method: gaussian_levelset`: Gaussian density derived from the level-set field.
- `alpha`: grid concentration strength; `alpha: 2.0` is the standard ch13 non-uniform setup.
- `schedule`: grid rebuild schedule (`static`, `every_step`, or `every_N`).

The distribution is located under `grid` because it changes the mesh. It may use
interface information as an input, but it is not itself interface physics.

## Numerical Classification

`numerics` is organised by equation role, not by individual force names.  The
big split is: interface transport, momentum operators, and projection/PPE.

- `time`: physical-time orchestration.  ch13 interface transport uses
  `tvd_rk3`; the momentum update is the existing projection
  predictor-corrector with CN viscosity.
- `interface.transport`: transported variable, spatial scheme, and physical-time
  integrator for the interface equation.
- `interface.tracking`: tracking/redistance policy.  This is separate from
  `interface.reinitialization`, which is pseudo-time geometry restoration.
- `momentum.form`: current equation form. `primitive_velocity` is implemented;
  WIKI-X-028 motivates a future `conservative_momentum` form.
- `momentum.operators`: spatial/time choices for implemented momentum
  operators.  `balanced_force` is the coupled pressure/surface-tension operator;
  it is not expressed as two independent knobs because using different schemes
  is precisely the unstable case.
- `projection`: projection semantics and the PPE solve.  The PPE is split into
  `poisson.operator` and `poisson.solver` so that discretisation and linear
  algebra are not confused.

`surface_tension_model` is not a duplicate physical input.  `physics.surface_tension`
is the material constant σ; `momentum.operators.balanced_force.surface_tension_model`
selects the numerical formulation for the σ κ ∇ψ half of the balanced pair.

Gravity is omitted when `physics.gravity: 0.0`.  There is no separate
`gravity.enabled` flag; physical presence is determined by the physics section.

This follows WIKI-X-026 and WIKI-X-028: advection, viscosity, surface tension,
and pressure have different stiffness and conservation roles, so their choices
must be independently visible.

## Current ch13 Scheme Policy

The current ch13 production/probe YAMLs follow the latest wiki design guide
within the schemes implemented today:

- `interface.transport.spatial: fccd_flux` with `interface.tracking.primary: psi` follows
  the core CCD-family policy: FCCD/UCCD/DCCD are introduced so production ch13
  experiments do not fall back to WENO. This preserves WIKI-T-065 / WIKI-X-031's
  field separation: ψ is the conservative transported state; φ is geometry and
  should not be the primary physical-time transport variable.
- `time.interface_transport: tvd_rk3` reflects the actual FCCD/DCCD advection
  implementation; older `forward_euler` wording was misleading.
- `momentum.operators.balanced_force.spatial: fccd_flux` applies the same
  CCD-family face operator to pressure correction and surface tension force.
  There is no `balanced_with` field because the coupling is the operator itself.
- `momentum.operators.viscosity.time_integrator: crank_nicolson` follows WIKI-X-026 / WIKI-X-030:
  viscous terms are stiffness-relevant and should use the CN path when
  available.
- `projection.mode: consistent_iim` follows WIKI-X-020 / WIKI-X-032:
  the sharp-interface path should be explicit in the config; the implementation
  can still reject/fallback unsafe IIM candidates internally.
- `projection.poisson.solver.kind: iterative` with `gmres + jacobi` follows WIKI-T-060 /
  WIKI-T-063 / WIKI-L-026 for GPU-scale FVM projection. For N=128 ch13 runs,
  diagonal Jacobi keeps the same PPE residual class as the truncated line-PCR
  probe while avoiding the costly per-iteration batched tridiagonal solves.
  Direct sparse FVM solve is kept as a debugging option, not the ch13 default.
- `momentum.operators.convection.spatial: fccd_flux` remains the conservative implemented
  default. The `_uccd6` YAML is an explicit UCCD6 probe; WIKI-X-028's
  conservative-momentum UCCD6 form is still a future implementation target.

## PPE Solver Semantics

`projection.poisson.solver.kind` selects the solver class:

- `iterative`: requires an iteration method, currently `gmres`, plus tolerance,
  iteration limit, restart, and preconditioner. `pcr_stages` / `c_tau` are
  meaningful only when `preconditioner: line_pcr`.
- `direct`: sparse FVM direct solve; it intentionally does not accept iterative
  options such as `method` or `preconditioner`.
- `defect_correction`: outer residual correction.  It must specify
  `corrections` and an explicit `base_solver`; `base_solver` is rejected for
  non-DC solvers so meaningless YAML fails fast instead of being ignored.

Kronecker LU is intentionally absent from ch13 YAML. It remains a restricted
component/reference path, not an integration-experiment default.
