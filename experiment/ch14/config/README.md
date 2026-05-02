# ch14 Benchmark YAML Design

The §14 benchmark set is the canonical surface for the two-phase NS production
stack. Four production YAML files are checked in:

- `ch14_capillary.yaml` — capillary-wave benchmark.
- `ch14_static_droplet_periodic.yaml` — periodic static-droplet GPU benchmark.
- `ch14_rising_bubble.yaml` — rising-bubble benchmark.
- `ch14_rayleigh_taylor.yaml` — Rayleigh–Taylor instability benchmark.

The capillary-wave route intentionally has a single checked-in YAML:
`ch14_capillary.yaml`.  Short, bounded, or GPU profiling variants should be
created as untracked local run copies or reproduced through command-line
overrides, not checked in as additional capillary YAMLs.
Run them through the unified runner (`experiment/run.py`):

- `python experiment/run.py --config ch14_capillary`
- `python experiment/run.py --config ch14_static_droplet_periodic`
- `python experiment/run.py --config ch14_rising_bubble`
- `python experiment/run.py --config ch14_rayleigh_taylor`
- Add `--plot-only` to regenerate figures from a prior `data.npz`.

The four production configs emit periodic snapshots with `psi`, `velocity`,
and `pressure` fields. The runner stores these in `data.npz` under `fields/psi`,
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
  On nonuniform grids, `local`/`xi_cells` is allowed only with
  `surface_tension.formulation: pressure_jump` or `none`; CSF uses `nominal`.
- `geometry.curvature`: interface-geometry reconstruction used to obtain κ.
  `psi_direct_filtered` is the direct-ψ curvature route with an
  interface-limited smoothing filter; it is not Hermite field extension.
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

`grid.distribution` owns mesh non-uniformity, while `grid.domain.boundary`
is the only place that declares whether each axis has physical walls or is
periodic.  The canonical form is axis-local and monitor-based:

- `axes.<axis>.type`: `uniform` or `nonuniform`.
- `axes.<axis>.monitors.interface`: interface-centred grid density.
- `axes.<axis>.monitors.wall`: wall-centred grid density, valid only on axes
  declared as wall-bounded in `grid.domain.boundary`.
- `axes.<axis>.dx_min_floor`: optional cell-width floor for that nonuniform
  axis.
- Legacy compact form remains accepted for interface-only grids:
  top-level `type/method/alpha` plus `axes: [x]`, `[y]`, `[x, y]`, or omitted.
  It cannot express wall refinement.
- `schedule`: non-negative grid rebuild interval. The paper-standard
  interface-following route is `1`, meaning rebuild every physical step from
  the current tracked interface. `static`/`0` remains available for explicit
  fixed-grid comparisons.

Uniform axes may not declare monitors. Nonuniform axes must declare at least
one monitor. Periodic axes may use interface monitors but cannot use wall
monitors because no physical wall exists in that direction.

Canonical capillary-wave form:

```yaml
grid:
  domain:
    boundary:
      x: periodic
      y:
        lower: wall
        upper: wall
  distribution:
    schedule: 1
    axes:
      x:
        type: uniform
      y:
        type: nonuniform
        monitors:
          interface:
            alpha: 2.0
          wall:
            alpha: 1.3
            eps_g_cells: 4
            apply_to: [lower, upper]
```

The capillary-wave YAML keeps `x` uniform and periodic, while `y` is
nonuniform because it contains both the interface-normal resolution and the
upper/lower wall resolution. It does not use a fake interface-fitting axis with
`alpha: 1.0`.

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

The dynamic ch14 YAMLs share the production stack:

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
  enters the PPE as an interface stress condition rather than as a CSF body force.
- `momentum.terms.viscosity.spatial: ccd` + `time_integrator: implicit_bdf2` —
  BDF2 Helmholtz path for stiffness-relevant viscous terms. The nested
  `solver.kind` selects `defect_correction` (default production path) or
  `gmres` (explicit comparison path). DC-specific settings live under
  `solver.corrections`.

Viscous BDF2 solver selection:

```yaml
viscosity:
  spatial: ccd
  time_integrator: implicit_bdf2
  solver:
    kind: defect_correction   # or gmres
    tolerance: 1.0e-8
    max_iterations: 80
    restart: 40
    corrections:
      max_iterations: 3
      relaxation: 0.8
      low_operator: component  # or scalar; scalar uses c=(d+1)/d isotropic low solve
```
- `projection.poisson.operator.discretization: fccd`,
  `coefficient: phase_separated`,
  `interface_coupling: affine_jump` — the FCCD pressure operator
  with a jump-aware affine face gradient, avoiding regular-pressure
  decomposition of `j_gl(1-ψ)`. On nonuniform grids this same key means the
  face jump is built from the local physical face distance `H_f` and shared by
  the PPE RHS and face-flux corrector; no separate nonuniform PPE solver key is
  required. Regridded Mode 2 runs must rebuild this face cache from the current
  grid instead of interpolating it from the previous step.
- `projection.poisson.solver.kind: defect_correction` with
  `base_solver.discretization: fd` / `base_solver.kind: direct` — evaluates
  the residual with the FCCD high-order operator and solves each correction
  with the low-order FD `L_L` operator. The FD matrix factor is reused within
  one outer DC solve, matching the paper's grid-defect method without
  re-entering the legacy FVM direct sparse solve for every correction RHS.

Cadence differences across YAMLs:
- Capillary-wave: `reinitialization.every_steps: 20` (slow dynamics).
- Static droplet: `tracking.enabled: false`, `convection.time_integrator: ab2`,
  and `viscosity.time_integrator: forward_euler`; this frozen-interface
  reference route avoids BDF2/PPE coefficient rebuilds while preserving the
  pressure-jump projection stack.
- Rising-bubble & RT: `every_steps: 4` (faster geometry change).

## PPE Solver Semantics

`projection.poisson.solver.kind` selects the solver class:

- `iterative`: requires `method` (currently `gmres`), `tolerance`,
  `max_iterations`, `restart`, and `preconditioner`.
  `preconditioner: line_pcr` is the ch14 low-order FD correction default;
  `jacobi` is available only as a cheaper, slower fallback preconditioner.
- `direct`: sparse FVM direct solve; intentionally rejects all iterative options.
- `defect_correction`: outer residual correction. Requires `corrections` and
  `base_solver`. `base_solver` keys are rejected for non-DC solvers. For FCCD
  production runs, `base_solver.discretization` must select a lower-order
  operator (`fd`); using the same FCCD operator or the legacy `fvm_direct`
  sparse solve as the base solver is rejected because it bypasses the intended
  paper contract or reintroduces the slow FVM Step 2 path.

Defect-correction example:

```yaml
projection:
  poisson:
    solver:
      kind: defect_correction
      corrections:          # outer DC loop
        max_iterations: 3
        tolerance: 1.0e-8
        relaxation: 0.7     # ω < 0.833 for FCCD/FD DC stability margin
      base_solver:          # inner approximate solve
        discretization: fd
        kind: direct
```

For research sweeps, the same low-order ``L_L`` slot can be made iterative
without changing the high-order FCCD residual operator:

```yaml
      base_solver:
        discretization: fd
        kind: iterative
        method: cg
        preconditioner: jacobi
```

CG solves the control-volume-weighted SPD form ``-W L_L p = -W rhs`` and does
not silently fall back to direct solves.  The production ch14 YAMLs keep
`fd/direct` because factor reuse is the current measured fast path.

`projection.poisson.operator.coefficient: phase_separated` is the two-phase
declaration for the PPE: rho is assembled from `physics.phases` and psi.

Kronecker LU is intentionally absent from ch14 YAML. It remains a restricted
component/reference path, not an integration-experiment default.

## Two-Phase Slot Convention

`physics.phases` uses fixed slot names `liquid` and `gas` regardless of the
actual fluids. The Rayleigh–Taylor YAML relabels the `gas` slot with mercury's
material constants while keeping the schema key. Document the physical fluid
in the YAML header comment.
