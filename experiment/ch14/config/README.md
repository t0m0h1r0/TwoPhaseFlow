# ch14 Benchmark YAML Design

The §14 benchmark set is the canonical surface for the two-phase NS production
stack. Five production YAML files are checked in:

- `ch14_capillary.yaml` — capillary-wave benchmark.
- `ch14_static_droplet.yaml` — periodic static-droplet GPU benchmark.
- `ch14_oscillating_droplet.yaml` — oscillating-droplet benchmark.
- `ch14_rising_bubble.yaml` — rising-bubble benchmark.
- `ch14_rayleigh_taylor.yaml` — Rayleigh–Taylor instability benchmark.

Each experiment type intentionally has exactly one checked-in YAML. Short,
bounded, diagnostic, resolution, one-period, and GPU-profiling variants should
be created as untracked local run copies, command-line overrides, or in-memory
diagnostic configs. They must not be checked in as additional ch14 YAMLs.
Run them through the unified runner (`experiment/run.py`):

- `python experiment/run.py --config ch14_capillary`
- `python experiment/run.py --config ch14_static_droplet`
- `python experiment/run.py --config ch14_oscillating_droplet`
- `python experiment/run.py --config ch14_rising_bubble`
- `python experiment/run.py --config ch14_rayleigh_taylor`
- Add `--plot-only` to regenerate figures from a prior `data.npz`.

Each normal run writes a restart checkpoint to
`experiment/ch14/results/<config>/checkpoint_final.npz`. Resume is never
implicit: pass `--resume-from <path>` explicitly, usually after increasing
`run.T_final` in the same YAML. The checkpoint manifest ignores restart-safe
output-only paths (`output.*`, `run.snap_times`, `run.snap_interval`,
`run.print_every`, and `run.debug_diagnostics`) but refuses restart if any
physics/numerics/grid/interface/diagnostic parameter or any execution code under
`src/twophase/`, `experiment/runner/`, or `experiment/run.py` changed. For long runs,
`--checkpoint-every-steps N` refreshes the same checkpoint atomically every `N`
completed steps, and `--no-checkpoint-final` disables the final write when a
read-only dry run is needed. Numerical state is stored as NumPy `.npy` binary
members inside the `.npz`, preserving array dtype bytes losslessly; JSON is used
only for non-numerical metadata such as the manifest and debug key names.

The five production configs share the chapter-14 execution contract introduced
for the rising-bubble route: conservative common-flux momentum transport,
`predictor.assembly: none`, projected-face preservation, pressure-coordinate
BDF2 history, and an explicit fail-closed boundary-Hodge state-space contract.
All five YAMLs select the active-geometry capillary decomposition scheme with
`interface.state_space: active_geometry_capillary`.  The parser validates that
scheme against the fixed short-paper active-geometry contract internally:
transported `q`, normalized `theta`, P1 gauge `phi`, active-cached
compatibility, required GPU storage, no implicit dense runtime fallback,
`geometric_swept_volume` transport, and
`bundle_virtual_work` pressure-jump coupling with
`pressure_component_hodge` reaction.

`ch14_capillary.yaml` and `ch14_oscillating_droplet.yaml` are SI water-air
cases at about 20 C.  The capillary wave uses a 20 mm x 20 mm tank with
mode 2, so the wavelength is 10 mm; the oscillating droplet uses the same
20 mm square tank with a 10 mm-class ellipse (`a=5.5 mm`, `b=4.5 mm`).
Their final times and snapshot times are no longer inherited from the old
unit-box scale.  The capillary-wave theory reference uses the rigid-wall
two-layer finite-depth dispersion relation because the 10 mm interface sits
midway between the upper and lower walls of the 20 mm tank; the paper-facing
snapshot window then follows the signed mode-2 production response over one
observed cycle.  The oscillating-droplet window follows the Rayleigh-Lamb
water-air period.  All five Chapter 14 YAMLs use active-geometry `q` as the
interface carrier; the `interface.reinitialization` block therefore selects
`compatibility_projection` every step.  This is not diffuse-CLS redistance:
it is the hard active-geometry constraint solve that restores `Q_h(phi)=q`
after swept-volume `q` transport and before bundle capillarity evaluates
surface-energy work.

The five production configs emit periodic snapshots with `psi`, `velocity`,
and pressure-family figures. The runner stores raw fields in `data.npz` under
`fields/psi`, `fields/velocity`, and `fields/pressure` (plus compatibility
fields `fields/u`, `fields/v`, and `fields/p`), and stores the affine face
pressure cochain under `fields/pressure_accel_faces/<axis>`.

For affine pressure-jump runs, `fields/pressure` is the stored scalar
representative associated with the face pressure cochain.  The sharp-interface
pressure is single-valued only inside each phase and has a jump on the
interface.  Production pressure figures should therefore use `snapshot_series`
field `pressure_hodge` when the saved face cochain is same-phase integrable,
which reconstructs a phase-wise Hodge representative from that cochain.  This
is fail-closed: if old data do not contain that cochain, plotting must stop and
the data must be regenerated.  The same fail-closed rule applies when the
same-phase exact-gradient residual is not small: then the saved face cochain is
not a scalar pressure field on the current phase graph, and the plot must be
treated as a cochain diagnostic rather than as physical pressure.
`pressure_hodge` therefore rejects residuals above `max_relative_residual`
(default `1e-2`) instead of forcing a misleading scalar image.  Runs whose
stored affine cochain is not guaranteed integrable, such as the current
rising-bubble pressure output, should plot the stored scalar `pressure` field
instead of forcing a Hodge representative.
Do not mask the fitted interface band as "undefined"; that hides the pressure
representative instead of testing the discrete pressure-work contract.

The schema is organized by *what the setting means*, not by where the current
Python implementation stores it.

## YAML Ownership Philosophy

The YAML is the experiment contract.  The user should explicitly choose the
scientific and numerical degrees of freedom:

- Scheme selection: `interface.state_space`, interface transport, momentum
  term discretizations, gravity formulation, PPE operator/solver, and
  `projection.active_geometry.solver.scheme`.
- Parameter selection: grid resolution/distribution, material constants, CFL
  multiplier, final time, tolerances, iteration limits, relaxation factors, and
  fallback triggers.
- Initial and boundary state: `initial_condition`, `initial_velocity`, and
  `boundary_condition`.
- Output and diagnostics: result directory, snapshots, figures, checkpoints,
  and diagnostic names.

Code should not hide those choices behind a broad preset.  The parser may only
validate combinations, normalize local aliases, and derive internal runtime
contracts that are not meaningful experiment knobs: for example the
q/theta/phi handoff fields, active-cache implementation markers, GPU-required
runtime guard, dense-reference test boundary, and derived geometry ledgers.

When a block affects the mathematical scheme or a convergence parameter, keep
it visible in YAML.  When a value is merely a consequence of an explicit scheme
choice, let the parser derive it and fail closed if the surrounding YAML
contradicts the paper contract.

## Top-Level Sections

- `grid`: computational mesh size, physical domain, boundary type, and mesh distribution.
- `experiment`: runner metadata such as handler type.
- `interface`: the full lifecycle of the phase interface.
- `physics`: material properties and physical constants.
- `run`: wall-clock experiment controls such as final time and diagnostics.
- `numerics`: time integrators, equation terms, projection semantics, and linear solvers.
- `output`: result directory, snapshots, and figure recipes.

## Handler Metadata and Initial Field

Checked-in ch14 YAMLs separate experiment dispatch from field geometry:
`experiment.type` selects the runner handler, while `initial_condition.objects`
describes the conservative level-set field.  Do not add wrapper scripts for new
wave inputs.  Use the `capillary_wave` shape alias inside `objects`:

```yaml
experiment:
  type: capillary_wave

initial_condition:
  background_phase: gas
  objects:
    - type: capillary_wave
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
fluid (mercury); `experiment.type: capillary_wave` dispatches identically.

## Object Collections and Velocity Perturbations

Use `initial_condition.objects` for experiment-facing object placement.  The
older `shapes` key remains accepted for low-level primitives, but checked-in
benchmark YAMLs should prefer the domain wording for both single and multiple
field regions:

```yaml
initial_condition:
  background_phase: gas
  objects:
    - type: circle
      center: [0.35, 0.30]
      radius: 0.08
      interior_phase: liquid
    - type: ellipse
      center: [0.65, 0.30]
      semi_axes: [0.12, 0.06]
      interior_phase: liquid
    - type: layer
      axis: y
      bounds: [0.60, 0.72]
      interior_phase: liquid
```

Supported object primitives currently include `circle`, `ellipse`, `layer`,
`rectangle`, `half_space`, `capillary_wave`, `perturbed_circle`, and
`zalesak_disk`.  `bubble` remains a convenience alias for a gas-filled circle,
but it is not the object model itself.  Set `interior_phase` explicitly whenever
the default liquid interior is not intended.

Initial velocity supports superposition through `base` and `perturbations`.
Each child is a normal velocity primitive, so adding new perturbation families
does not require a separate parser path:

```yaml
initial_velocity:
  base:
    type: uniform
    velocity: [0.0, 0.0]
  perturbations:
    - type: sinusoidal_perturbation
      component: y
      axis: x
      amplitude: 0.01
      mode: 1
      length: 1.0
      phase: 0.0
```

This defines `v' = 0.01 sin(2π x / length + phase)` and leaves the horizontal
component unchanged except for the base field.

## Interface Lifecycle

`interface` groups settings that must be reasoned about together:

- `thickness`: how the CLS thickness is measured (`nominal`, `local`, `xi_cells`).
  On nonuniform grids, `local`/`xi_cells` is allowed only with
  `surface_tension.formulation: pressure_jump` or `none`; CSF uses `nominal`.
- `geometry.curvature`: interface-geometry reconstruction used to obtain κ.
  ch14 production YAMLs use `face_implicit`, the scalar face-native
  Young-Laplace pressure-jump geometry.  The P2 ALE discrete-gradient
  face-cochain route is not a validated production pressure-jump path until
  its pressure-jump range projection passes the static-droplet Hodge gate.
- `reinitialization`: geometry restoration algorithm in pseudo-time; this is not
  physical time integration.

`numerics.interface.transport` holds both the spatial scheme and the
physical-time integrator together:

```yaml
numerics:
  interface:
    transport:
      variable: q
      spatial: geometric_swept_volume
      time_integrator: tvd_rk3
      boundedness: certified
      fail_close: true
    tracking:
      primary: q
```

For active-geometry Chapter 14 YAMLs, `tracking.primary: q` follows from the selected
scheme contract.

Tracking redistance frequency is intentionally separate from reinitialization
frequency:

- `numerics.interface.tracking.redistance.schedule.every_steps`: phi-primary
  tracking cleanup while transporting the interface in physical time.
- `interface.reinitialization.schedule.every_steps`: full CLS profile restoration
  in pseudo-time after advection.
  Conservative common-flux reinitialization must be represented in the same
  `q,m,p` bundle as transport.  The current dynamic capillary-wave and
  oscillating-droplet configs use every-step restoration; checked-in configs may
  still set this to `0` for benchmark-specific reasons such as
  static-equilibrium gates or transport-only dynamic gates.

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
  interface-following route is `1`, meaning the fitted grid is rebuilt every
  physical step from the current conservative common-flux state.

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

The capillary-wave YAML keeps `x` periodic and interface-fitted, while `y` is
also nonuniform because it contains both the interface-normal resolution and the
upper/lower wall resolution.

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
- `interface.tracking`: tracking/redistance policy.  Chapter 14
  active-geometry capillary YAMLs declare `primary: q` so the q/theta/phi
  state-space contract is visible.
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

The stack is intentionally written out in YAML.  Do not replace it with a
single broad `numerical_stack` key: that would remove the user's responsibility
for scheme selection and convergence parameter selection.  The code-side role
is to reject contradictory combinations, not to choose the experiment for the
user.

- `interface.state_space: active_geometry_capillary` — the user-facing
  active-geometry capillary decomposition selection.
  Internal projection details such as `active_cached`, GPU storage, dense
  reference policy, and support budgets are derived and validated by the parser
  rather than exposed as experiment knobs.
- `interface.transport.variable: q` and
  `interface.transport.spatial: geometric_swept_volume` — active geometry owns the
  material phase as physical cell volume, while `theta` and `phi` are derived
  views constrained by the explicit state-space contract.
- `interface.transport.time_integrator: tvd_rk3` — co-located with the spatial
  scheme in the same `transport:` block.
- `interface.geometry.curvature.method: face_implicit` — scalar face-native
  Young-Laplace diagnostic geometry on fitted grids.
- `interface.reinitialization.algorithm: compatibility_projection` with
  `schedule.every_steps: 1` — the active-geometry q/theta/phi compatibility
  projection is applied every step.  This is not Ridge--Eikonal diffuse
  redistance and must not be replaced by a hidden profile-restoration fallback.
- `momentum.terms.convection.spatial: uccd6` + `time_integrator: imex_bdf2` —
  WIKI-T-062 positions UCCD6 as the order-preserving upwind CCD remedy for
  transport/Gibbs control.
- `momentum.terms.pressure.gradient: fccd` and
  `momentum.terms.surface_tension.formulation: pressure_jump` — surface tension
  enters the PPE as an interface stress condition rather than as a CSF body force.
- `momentum.terms.surface_tension.source: bundle_virtual_work` exposes
  `closed_interface.endpoint: geometric_cell_fraction` and
  `residual_contract: {metric: pressure_adjoint, constraints: [cell_volume],
  fail_close: true}`. These keys state the active-geometry theorem contract: the
  surface-energy covector, cell-volume reaction, PPE source, and face corrector
  all use the geometric q endpoint and the same pressure-adjoint face metric.
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
      max_iterations: 12
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
  `corrections.max_iterations` is a user-owned cap, not a success criterion;
  convergence is accepted only through the residual tolerance, and
  `corrections.fail_close: true` keeps non-convergence visible.
- `projection.active_geometry.solver` selects the active q/phi compatibility
  projection solver policy.  This is separate from `interface.state_space`:
  the state-space key selects active geometry, while this block selects how the
  active projection is solved and stopped.  Production YAMLs currently use
  `scheme: pcg`; `dc` and `dc_then_pcg` are explicit research settings.

Experiment-specific YAMLs may change geometry, boundary conditions, initial
fields, gravity, output cadence, and final time. They should not change the
canonical ch14 numerical stack above without recording a new paper-backed
experiment type.

## Active Geometry Solver Semantics

`projection.active_geometry.solver.scheme` selects one of three explicit
policies:

- `pcg`: PCG/Newton only; no DC fallback.
- `dc`: residual-monotone defect correction only; no PCG fallback.
- `dc_then_pcg`: start with residual-monotone DC and fall back to PCG only on
  listed triggers.

PCG-only example:

```yaml
projection:
  active_geometry:
    solver:
      scheme: pcg
      convergence:
        norm: linf
        absolute_tolerance: 1.0e-11
        relative_tolerance: 0.0
        max_iterations: 8
      pcg:
        tolerance: 1.0e-12
        max_iterations: 256
        roundoff_floor: 1.0e-14
```

DC-only example:

```yaml
projection:
  active_geometry:
    solver:
      scheme: dc
      convergence:
        norm: linf
        absolute_tolerance: 1.0e-11
        relative_tolerance: 0.0
        max_iterations: 8
      dc:
        tolerance: 1.0e-11
        max_iterations: 8
        relaxation: 1.0
```

DC with explicit PCG fallback:

```yaml
projection:
  active_geometry:
    solver:
      scheme: dc_then_pcg
      convergence:
        norm: linf
        absolute_tolerance: 1.0e-11
        relative_tolerance: 0.0
        max_iterations: 8
      dc:
        tolerance: 1.0e-11
        max_iterations: 4
        relaxation: 0.75
      pcg:
        tolerance: 1.0e-12
        max_iterations: 256
        roundoff_floor: 1.0e-14
      fallback:
        triggers: [not_converged, residual_floor_exceeded]
```

Fallback is never implicit: declaring `scheme: dc` with a `fallback:` block is
rejected; declaring `scheme: pcg` with DC settings is rejected.  `roundoff_floor`
must be no larger than the PCG tolerance.

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
        max_iterations: 12
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
