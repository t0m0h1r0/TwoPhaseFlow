# ch13 Experiment YAML Design

The ch13 YAML schema is organized by *what the setting means*, not by where the
current Python implementation stores it.

## Top-Level Sections

- `grid`: computational mesh size, physical domain, and boundary type.
- `interface`: the full lifecycle of the phase interface.
- `physics`: material properties and physical constants.
- `run`: wall-clock experiment controls such as final time and diagnostics.
- `numerics`: discretization, time treatment, and solver choices per equation term.
- `output`: result directory, snapshots, and figure recipes.

## Interface Lifecycle

`interface` groups settings that must be reasoned about together:

- `geometry.fitting`: whether the mesh follows the interface and how often it is rebuilt.
- `geometry.width`: how the CLS thickness is measured (`nominal`, `local`, `xi_cells`).
- `tracking`: which interface variable is transported in physical time (`psi` or `phi`).
- `reinitialization`: geometry restoration in pseudo-time; this is not physical time integration.

This follows WIKI-X-027: interface transport and reinitialization use different
time axes and should not be placed as sibling `run` knobs.

## Numerical Terms

`numerics.terms` is the operator table. Each term says how it is discretized and
how it is advanced:

- `interface_transport`: CLS/level-set advection in physical time.
- `momentum_advection`: primitive-velocity momentum convection for the current pipeline.
- `viscosity`: spatial operator and explicit/CN time treatment.
- `surface_tension`: force model, curvature path, and gradient consistency.
- `pressure_projection`: projection mode plus PPE solver type.

This follows WIKI-X-026 and WIKI-X-028: advection, viscosity, surface tension,
and pressure have different stiffness and conservation roles, so their choices
must be independently visible.

## PPE Solver Semantics

`pressure_projection.solver.kind` selects the solver class:

- `iterative`: requires an iteration method, currently `gmres`, plus tolerance,
  iteration limit, restart, preconditioner, PCR stage cap, and `c_tau`.
- `direct`: sparse FVM direct solve; it intentionally does not accept iterative
  options such as `method` or `preconditioner`.

Kronecker LU is intentionally absent from ch13 YAML. It remains a restricted
component/reference path, not an integration-experiment default.
