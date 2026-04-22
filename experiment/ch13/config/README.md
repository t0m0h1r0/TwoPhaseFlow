# ch13 Experiment YAML Design

The ch13 YAML schema is organized by *what the setting means*, not by where the
current Python implementation stores it.

## Top-Level Sections

- `grid`: computational mesh size, physical domain, and boundary type.
- `interface`: the full lifecycle of the phase interface.
- `physics`: material properties and physical constants.
- `run`: wall-clock experiment controls such as final time and diagnostics.
- `numerics`: physical-time operators and elliptic constraint solvers.
- `output`: result directory, snapshots, and figure recipes.

## Interface Lifecycle

`interface` groups settings that must be reasoned about together:

- `geometry.fitting`: whether the mesh follows the interface and how often it is rebuilt.
- `geometry.width`: how the CLS thickness is measured (`nominal`, `local`, `xi_cells`).
- `tracking`: which interface variable is transported in physical time (`psi` or `phi`).
- `reinitialization`: geometry restoration algorithm in pseudo-time; this is not physical time integration.

This follows WIKI-X-027: interface transport and reinitialization use different
time axes and should not be placed as sibling `run` knobs.

## Numerical Classification

`numerics` is split by mathematical role:

- `physical_time`: operators that advance the state in physical time `t`.
- `elliptic`: constraint solves with no physical-time derivative.

`physical_time` currently contains:

- `interface_advection`: CLS/level-set advection in physical time.
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

## PPE Solver Semantics

`pressure_projection.poisson.solver.kind` selects the solver class:

- `iterative`: requires an iteration method, currently `gmres`, plus tolerance,
  iteration limit, restart, preconditioner, PCR stage cap, and `c_tau`.
- `direct`: sparse FVM direct solve; it intentionally does not accept iterative
  options such as `method` or `preconditioner`.

Kronecker LU is intentionally absent from ch13 YAML. It remains a restricted
component/reference path, not an integration-experiment default.
