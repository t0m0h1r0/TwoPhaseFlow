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

`numerics.interface.transport` holds both the spatial scheme and the
physical-time integrator together:

```yaml
numerics:
  interface:
    transport:
      variable: psi
      spatial: fccd_flux
      time_integrator: tvd_rk3
```

`numerics.interface.tracking` is only needed when the primary tracking variable
differs from the transport variable (phi-primary experiments).  When
`transport.variable: psi`, the `tracking:` block adds no information and should
be omitted.

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

`numerics` is organised by equation role and physical term.  The big split is:
interface transport, momentum terms, and projection/PPE.

- `time.algorithm`: overall time-integration algorithm family.  `fractional_step`
  is the paper term for the projection predictor-corrector.  This is the only
  entry in `numerics.time`; all per-equation choices live in their own blocks.
- `interface.transport`: transported variable, spatial scheme, and physical-time
  integrator co-located in one block.
- `interface.tracking`: tracking/redistance policy, only needed for phi-primary
  experiments.  Omit when `transport.variable: psi`.
- `momentum.terms`: spatial/time choices for physical momentum terms.  Pressure
  and surface tension are written as `pressure` and `surface_tension`, not as
  hidden derivative knobs.  `pressure.gradient` and `surface_tension.gradient`
  name the gradient operator (∇p and ∇H(ψ)); `convection.spatial` names the
  transport operator — deliberately different keys since the operators are
  semantically different.
- `projection`: projection semantics and the PPE solve.  `poisson.solver`
  selects the linear algebra.  The `poisson.operator` block (FVM discretization,
  variable-density coefficient) is optional; both values have exactly one
  valid choice and default automatically.

`surface_tension.model` is not a duplicate physical input.
`physics.surface_tension` is the material constant σ;
`momentum.terms.surface_tension.model` selects the numerical formulation for
the σ κ ∇ψ term.

`momentum.form: primitive_velocity` is omitted: there is exactly one
implemented form and a paper reader gains nothing from seeing a constant.

Gravity is omitted when `physics.gravity: 0.0`.  There is no separate
`gravity.enabled` flag; physical presence is determined by the physics section.

This follows WIKI-X-026 and WIKI-X-028: advection, viscosity, surface tension,
and pressure have different stiffness and conservation roles, so their choices
must be independently visible.

## Current ch13 Scheme Policy

The current ch13 production/probe YAMLs follow the latest wiki design guide
within the schemes implemented today:

- `interface.transport.spatial: fccd_flux` follows the core CCD-family policy:
  FCCD/UCCD/DCCD are introduced so production ch13 experiments do not fall back
  to WENO. This preserves WIKI-T-065 / WIKI-X-031's field separation: ψ is the
  conservative transported state; φ is geometry and should not be the primary
  physical-time transport variable.  `tracking:` is omitted because
  `transport.variable: psi` already determines the tracking variable.
- `interface.transport.time_integrator: tvd_rk3` is co-located with the spatial
  scheme in the same `transport:` block, reflecting that spatial and temporal
  discretizations of the same equation belong together.
- `momentum.terms.convection.time_integrator: ab2` matches the implemented
  momentum predictor history; startup falls back to Euler only for the first
  step when no previous convection state exists.
- `momentum.terms.pressure.gradient` and `momentum.terms.surface_tension.gradient`
  name the gradient operators for ∇p and σκ∇ψ explicitly.  `gradient:` is used
  (not `spatial:`) because these are gradient reconstructions, not transport
  operators like `convection.spatial`.
- `momentum.terms.viscosity.time_integrator: crank_nicolson` follows WIKI-X-026 / WIKI-X-030:
  viscous terms are stiffness-relevant and should use the CN path when
  available.
- `projection.mode: consistent_iim` follows WIKI-X-020 / WIKI-X-032:
  the sharp-interface path should be explicit in the config; the implementation
  can still reject/fallback unsafe IIM candidates internally.
- `projection.poisson.solver.kind: iterative` with `gmres + jacobi` follows WIKI-T-060 /
  WIKI-T-063 / WIKI-L-026 for GPU-scale FVM projection. Jacobi preconditioner
  is required for GPU execution; `line_pcr` requires CPU-side batched PCR and
  must not be used in production ch13 runs.  Direct sparse FVM solve is kept as
  a debugging option only.
- `momentum.terms.convection.spatial: fccd_flux` remains the conservative implemented
  default. The `_uccd6` YAML is an explicit UCCD6 probe; WIKI-X-028's
  conservative-momentum UCCD6 form is still a future implementation target.

## PPE Solver Semantics

`projection.poisson.solver.kind` selects the solver class:

- `iterative`: requires `method` (currently `gmres`), `tolerance`,
  `max_iterations`, `restart`, and `preconditioner`.
  `pcr_stages` / `c_tau` are **only** valid when `preconditioner: line_pcr`;
  they are rejected at parse time for any other preconditioner.
  `preconditioner: jacobi` is the ch13 production default (GPU-compatible).
  `preconditioner: line_pcr` requires CPU-side batched PCR and must not be
  used on GPU runs.
- `direct`: sparse FVM direct solve; intentionally rejects all iterative options.
- `defect_correction`: outer residual correction.  Requires `corrections` and
  `base_solver`.  `base_solver` keys are rejected for non-DC solvers.

Defect-correction example:

```yaml
projection:
  mode: consistent_iim
  poisson:
    solver:
      kind: defect_correction
      corrections:          # outer DC loop
        max_iterations: 3
        tolerance: 1.0e-8
        relaxation: 1.0     # ω in p_new = p_old + ω·δp
      base_solver:          # inner approximate solve
        kind: iterative
        method: gmres
        tolerance: 1.0e-8
        max_iterations: 500
        restart: 80
        preconditioner: jacobi
```

The `projection.poisson.operator` block (`discretization: fvm`,
`coefficient: variable_density`) is optional; both values are the only
available choices and default automatically.

Kronecker LU is intentionally absent from ch13 YAML. It remains a restricted
component/reference path, not an integration-experiment default.
