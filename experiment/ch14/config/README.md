# ch14 Benchmark YAML Design

The §14 benchmark set is the canonical surface for the two-phase NS production
stack. Three YAML files are checked in:

- `ch14_capillary_water_air_alpha2_n128.yaml` — capillary-wave benchmark.
- `ch14_rising_bubble_water_air_alpha2_n128x256.yaml` — rising-bubble benchmark.
- `ch14_rayleigh_taylor_water_mercury_n128x512.yaml` — Rayleigh–Taylor instability
  benchmark (water/mercury, Atwood ≈ 0.862, gravity-driven).

Run them through the unified runner (`experiment/run.py`):

- `python experiment/run.py --config ch14_capillary_water_air_alpha2_n128`
- `python experiment/run.py --config ch14_rising_bubble_water_air_alpha2_n128x256`
- `python experiment/run.py --config ch14_rayleigh_taylor_water_mercury_n128x512`
- Add `--plot-only` to regenerate figures from a prior `data.npz`.

All configs emit periodic snapshots with `psi`, `velocity`, and `pressure`
fields. The runner stores these in `data.npz` under `fields/psi`,
`fields/velocity`, and `fields/pressure` (plus compatibility fields
`fields/u`, `fields/v`, and `fields/p`).

The schema is organized by *what the setting means*, not by where the current
Python implementation stores it.

## Top-Level Sections

- `grid`: computational mesh size, physical domain, boundary type, and mesh distribution.
- `interface`: the full lifecycle of the phase interface.
- `physics`: material properties and physical constants.
- `run`: wall-clock experiment controls such as final time and diagnostics.
- `numerics`: time integrators, equation terms, projection semantics, and linear solvers.
- `output`: result directory, snapshots, and figure recipes.

## Capillary-Wave Initial Field

The capillary-wave experiment is configured through `initial_condition` only;
do not add wrapper scripts for new wave inputs. Use the `capillary_wave` shape
alias:

```yaml
initial_condition:
  type: capillary_wave
  axis: y
  mean: 0.5
  amplitude: 0.05
  mode: 2
  length: 1.0
  phase: 0.0
  interior_phase: liquid
```

This represents `y = mean + amplitude*cos(2π*mode*x/length + phase)`.
The Rayleigh–Taylor YAML uses the same shape alias with `interior_phase: liquid`
(lower phase = liquid) and a `physics.phases.gas` slot relabeled as the heavy
fluid (mercury); the `capillary_wave` handler key dispatches identically.

## Interface Lifecycle

`interface` groups settings that must be reasoned about together:

- `thickness`: how the CLS thickness is measured (`nominal`, `local`, `xi_cells`).
- `geometry.curvature`: interface-geometry reconstruction used to obtain κ.
  `psi_direct_hfe` lives here because HFE is a steep-interface geometry
  treatment, not a momentum-force switch.
- `reinitialization`: geometry restoration algorithm in pseudo-time; this is not
  physical time integration.

`numerics.interface.transport` holds both the spatial scheme and the
physical-time integrator together:

```yaml
numerics:
  interface:
    transport:
      variable: psi
      spatial: fccd
      time_integrator: tvd_rk3
```

`numerics.interface.tracking` is only needed when the primary tracking variable
differs from the transport variable (phi-primary experiments). When
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
- `alpha`: grid concentration strength; `alpha: 2.0` is the standard ch14
  non-uniform setup.
- `schedule`: grid rebuild schedule (`static`, `every_step`, or `every_N`).

The distribution is located under `grid` because it changes the mesh. It may
use interface information as an input, but it is not itself interface physics.

## Numerical Classification

`numerics` is organised by equation role and physical term. The big split is:
interface transport, momentum terms, and projection/PPE.

- `time.algorithm`: overall time-integration algorithm family. `fractional_step`
  is the paper term for the projection predictor-corrector. This is the only
  entry in `numerics.time`; all per-equation choices live in their own blocks.
- `interface.transport`: transported variable, spatial scheme, and physical-time
  integrator co-located in one block.
- `interface.tracking`: tracking/redistance policy, only needed for phi-primary
  experiments. Omit when `transport.variable: psi`.
- `momentum.terms`: spatial/time choices for physical momentum terms. Pressure
  and surface tension are written as `pressure` and `surface_tension`, not as
  hidden derivative knobs. `pressure.gradient` and `surface_tension.gradient`
  name the gradient operator (∇p and ∇H(ψ)); `convection.spatial` names the
  transport operator — deliberately different keys since the operators are
  semantically different.
- `projection`: PPE solve configuration. `poisson.operator.discretization`
  selects the pressure operator family; `poisson.operator.coefficient` selects
  how material phases enter the PPE coefficient.

`surface_tension.formulation` is not a phase selector.
`physics.surface_tension` is the material constant σ;
`momentum.terms.surface_tension.formulation` selects the numerical formulation
for the σ κ ∇ψ term. Use `pressure_jump` for the production §14 pressure-jump
balanced-force path.

`momentum.form: primitive_velocity` is omitted: there is exactly one
implemented form and a paper reader gains nothing from seeing a constant.

Gravity is omitted when `physics.gravity: 0.0`. There is no separate
`gravity.enabled` flag; physical presence is determined by the physics section.

This follows WIKI-X-026 and WIKI-X-028: advection, viscosity, surface tension,
and pressure have different stiffness and conservation roles, so their choices
must be independently visible.

## ch14 Production Numerical Stack

All three ch14 YAMLs share the production stack:

- `interface.transport.spatial: fccd` — FCCD is the conservative interface
  transport operator (WIKI-T-065 / WIKI-X-031: ψ is the conservative transported
  state; φ is geometry and should not be the primary physical-time transport
  variable). `tracking:` is omitted because `transport.variable: psi` already
  determines the tracking variable. The flux-locus form is the term default.
- `interface.transport.time_integrator: tvd_rk3` — co-located with the spatial
  scheme in the same `transport:` block.
- `momentum.terms.convection.spatial: uccd6` + `time_integrator: imex_bdf2` —
  WIKI-T-062 positions UCCD6 as the order-preserving upwind CCD remedy for
  transport/Gibbs control.
- `momentum.terms.pressure.gradient: fccd` and
  `momentum.terms.surface_tension.formulation: pressure_jump` — surface tension
  enters the PPE as a pressure jump rather than as a CSF body force.
- `momentum.terms.viscosity.spatial: ccd` + `time_integrator: implicit_bdf2` —
  CN-family path for stiffness-relevant viscous terms (WIKI-X-026 / WIKI-X-030).
- `projection.poisson.operator.discretization: fccd`,
  `coefficient: phase_separated`,
  `interface_coupling: jump_decomposition` — the FCCD pressure operator
  with phase-separated coefficient and explicit jump decomposition at the interface.
- `projection.poisson.solver.kind: defect_correction` (jacobi-preconditioned
  GMRES base solver) — keeps the residual-correction shell visible.

Cadence differences across YAMLs:
- Capillary-wave: `reinitialization.every_steps: 20` (slow dynamics).
- Rising-bubble & RT: `every_steps: 4` (faster geometry change).

## PPE Solver Semantics

`projection.poisson.solver.kind` selects the solver class:

- `iterative`: requires `method` (currently `gmres`), `tolerance`,
  `max_iterations`, `restart`, and `preconditioner`.
  `preconditioner: jacobi` is the ch14 production default (GPU-compatible).
  `preconditioner: line_pcr` requires CPU-side batched PCR and must not be
  used on GPU runs.
- `direct`: sparse FVM direct solve; intentionally rejects all iterative options.
- `defect_correction`: outer residual correction. Requires `corrections` and
  `base_solver`. `base_solver` keys are rejected for non-DC solvers.

Defect-correction example:

```yaml
projection:
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

`projection.poisson.operator.coefficient: phase_separated` is the two-phase
declaration for the PPE: rho is assembled from `physics.phases` and psi.

Kronecker LU is intentionally absent from ch14 YAML. It remains a restricted
component/reference path, not an integration-experiment default.

## Two-Phase Slot Convention

`physics.phases` uses fixed slot names `liquid` and `gas` regardless of the
actual fluids. The Rayleigh–Taylor YAML relabels the `gas` slot with mercury's
material constants while keeping the schema key. Document the physical fluid
in the YAML header comment.
