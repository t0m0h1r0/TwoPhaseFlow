# ch13 Experiment YAML Design

The ch13 YAML schema is organized by *what the setting means*, not by where the
current Python implementation stores it.

## Top-Level Sections

- `grid`: computational mesh size, physical domain, boundary type, and mesh distribution.
- `interface`: the full lifecycle of the phase interface.
- `physics`: material properties and physical constants.
- `run`: wall-clock experiment controls such as final time and diagnostics.
- `numerics`: physical-time operators and elliptic constraint solvers.
- `output`: result directory, snapshots, and figure recipes.

## Interface Lifecycle

`interface` groups settings that must be reasoned about together:

- `thickness`: how the CLS thickness is measured (`nominal`, `local`, `xi_cells`).
- `reinitialization`: geometry restoration algorithm in pseudo-time; this is not physical time integration.

The physical-time tracking choice lives under
`numerics.physical_time.interface_advection.tracking`, because it controls the
advection strategy rather than the interface state itself.

Tracking redistance frequency is intentionally separate from reinitialization
frequency:

- `interface_advection.tracking.redistance.schedule.every_steps`: phi-primary
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

`numerics` is split by mathematical role:

- `physical_time`: operators that advance the state in physical time `t`.
- `elliptic`: constraint solves with no physical-time derivative.

`physical_time` currently contains:

- `interface_advection`: CLS/level-set advection in physical time, including
  whether `psi`, `phi`, or neither is the primary transported field.
- `momentum.form`: current equation form. `primitive_velocity` is implemented;
  WIKI-X-028 motivates a future `conservative_momentum` form.
- `momentum.convection`: nonlinear momentum transport scheme.
- `momentum.viscosity`: viscous spatial operator and explicit/CN time treatment.
- `momentum.capillary_force`: surface-tension model, time treatment, curvature
  path, and balanced-force gradient consistency.

`elliptic.pressure_projection` contains projection semantics and the PPE solve.
The PPE is split into `poisson.discretization` and `poisson.solver` so that
the matrix/operator and the linear solver are not confused.

This follows WIKI-X-026 and WIKI-X-028: advection, viscosity, surface tension,
and pressure have different stiffness and conservation roles, so their choices
must be independently visible.

## Current ch13 Scheme Policy

The current ch13 production/probe YAMLs follow the latest wiki design guide
within the schemes implemented today:

- `interface_advection.spatial: weno5` with `tracking.primary: psi` follows
  WIKI-T-065 / WIKI-X-031: ψ is the conservative transported state; φ is
  geometry and should not be the primary physical-time transport variable.
- `momentum.viscosity.time: crank_nicolson` follows WIKI-X-026 / WIKI-X-030:
  viscous terms are stiffness-relevant and should use the CN path when
  available.
- `pressure_projection.mode: consistent_iim` follows WIKI-X-020 / WIKI-X-032:
  the sharp-interface path should be explicit in the config; the implementation
  can still reject/fallback unsafe IIM candidates internally.
- `poisson.solver.kind: iterative` with `gmres + line_pcr` follows WIKI-T-060 /
  WIKI-T-063 / WIKI-L-026 for GPU-scale FVM projection. Direct sparse FVM solve
  is kept as a debugging option, not the ch13 default.
- `momentum.convection.spatial: fccd_flux` remains the conservative implemented
  default. The `_uccd6` YAML is an explicit UCCD6 probe; WIKI-X-028's
  conservative-momentum UCCD6 form is still a future implementation target.

## PPE Solver Semantics

`pressure_projection.poisson.solver.kind` selects the solver class:

- `iterative`: requires an iteration method, currently `gmres`, plus tolerance,
  iteration limit, restart, preconditioner, PCR stage cap, and `c_tau`.
- `direct`: sparse FVM direct solve; it intentionally does not accept iterative
  options such as `method` or `preconditioner`.

Kronecker LU is intentionally absent from ch13 YAML. It remains a restricted
component/reference path, not an integration-experiment default.
