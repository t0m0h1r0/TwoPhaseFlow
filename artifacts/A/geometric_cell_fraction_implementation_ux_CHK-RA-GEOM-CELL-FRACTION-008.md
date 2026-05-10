# CHK-RA-GEOM-CELL-FRACTION-008

## Purpose

User request:

> Consider the implementation method and UX/YAML.

This note converts the discretization theory into an implementation design and
a YAML contract.  It is still pre-implementation: the goal is to prevent the
code from smuggling the old diffuse-phase assumptions back into a geometric
cell-fraction route.

## 1. Design Principle

The implementation must expose one physical contract:

```text
q_C = |C| theta_C is the hard material phase volume.
Gamma(phi) is the sharp capillary geometry.
Q_h(phi)=q ties them.
```

Everything else is implementation machinery.  The UX must therefore avoid
presenting users with unrelated toggles such as "volume correction",
"capillary smoothing", or "projection relaxation".  Those are not physical
choices.  The only acceptable user-facing choices are:

```text
state space,
transport geometry,
compatibility projection contract,
capillary virtual-work route,
diagnostic/fail-close thresholds.
```

## 2. Existing Code Anchors

The current code already has useful anchors:

```text
src/twophase/simulation/conservative_transport.py
  common-flux momentum transport using a recorded phase ledger.

src/twophase/levelset/transport_ledger.py
  stage-native phase and volume flux ledger.

src/twophase/coupling/closed_interface_geometry.py
  fixed-stratum sharp area/surface-gradient diagnostics.

src/twophase/coupling/closed_interface_riesz.py
  closed-interface capillary reaction route.

src/twophase/simulation/config_*.py
  existing YAML parser split for interface, numerics, output, and run.

src/twophase/simulation/checkpoint.py
  continuation checkpoint path that must be extended with q/stratum/stage data.
```

The wrong implementation is also easy to name:

```text
do not reinterpret existing psi arrays as q without changing units,
do not use normalized theta residuals for nonuniform physical constraints,
do not let capillary read a different interface than Q_h,
do not make geometric fractions a plotting-only diagnostic.
```

## 3. Proposed Module Layout

Use a new geometry state layer rather than overloading level-set internals:

```text
src/twophase/geometry/
  cell_complex.py
    MetricCellComplex, incidence B, cell/face measures, periodic quotient.

  phase_state.py
    GeometricPhaseState(q, theta view, phi, stratum, compatibility diagnostics).

  p1_cut_geometry.py
    Q_h(phi), A_h(phi), S_h(phi), fixed-stratum case tables, physical cut data.

  p1_cut_jacobian.py
    J_q=dQ_h/dphi and dS_h/dphi row assembly on the active stratum.

  swept_flux.py
    bounded geometric swept-volume flux Phi_l and certificates.

  compatibility_projection.py
    hard Q_h(phi)=q projection, KKT/Schur operators, line search, fail-close.

  bundle_capillary.py
    L_B(w), r_sigma(w), M_f Riesz interface to pressure/capillary stack.

  diagnostics.py
    q-volume drift, compatibility residual, stratum margin, Delta S_Pi.
```

Compatibility shims should live near the consuming layer, not inside the
geometry core:

```text
src/twophase/simulation/geometric_phase_runtime.py
  converts YAML/runtime solver state into GeometricPhaseState.

src/twophase/simulation/geometric_transport_ledger.py
  ledger variant in q-units while preserving common-flux semantics.

src/twophase/simulation/visualization/geometric_phase_fields.py
  theta/phi/Gamma overlays for plots.
```

This keeps `levelset/` as the CLS/gauge machinery and prevents the material
carrier from being hidden in a diffuse-profile package.

## 4. Data Model

### Primary state

```text
GeometricPhaseState:
  q:        cell liquid volumes, shape (Nx,Ny), units physical area/volume
  phi:      nodal continuous gauge, shape (Nx+1,Ny+1) modulo periodic quotient
  stratum:  fixed-stratum case/sign data for Gamma(phi)
  ledger:   compatibility residuals, projection work, margins
```

`theta` is computed:

```text
theta = q / cell_volume
```

and should not be stored as an independent mutable source of truth except in
checkpoint payloads where it is explicitly marked as a derived view for human
inspection.

### Geometry cache

The geometry cache is backend-native:

```text
mixed_cell_indices
case_code
edge_crossing_lambda
segment_endpoints
cell_liquid_volume Q_h
cell_surface_contribution
J_q row values and node columns
dS_h row/covector contributions
sign margins
```

For GPU suitability, the cache is struct-of-arrays.  Avoid Python lists of
per-cell objects on the production path.

### Transport ledger

The ledger must evolve from "psi phase flux" to typed phase units:

```text
phase_kind: "diffuse_psi" | "geometric_q"
phase_state_before
phase_state_after_transport
phase_fluxes
face_volume_fluxes
units: "fraction_flux" | "volume_flux"
clip_bounds: must remain None for geometric_q production
mass_correction_applied: must remain False
```

For `geometric_q`, `phase_fluxes` are physical liquid-volume fluxes per time.
Consumers derive mass flux by:

```text
Phi_m = rho_g Phi_V + (rho_l-rho_g) Phi_l.
```

## 5. GPU-First Implementation Route

The reference code may use clear CPU routines for manufactured tests, but the
production design must be vectorizable from the start.

### Geometry kernel

For P1/Q1 marching-squares geometry:

```text
1. load four nodal phi values per cell,
2. compute case_code,
3. compute edge crossing lambdas in vector form,
4. compute Q_h, S_h, J_q, dS_h for each case with masked vector formulas,
5. scatter J_q/dS_h contributions to nodal arrays or sparse row tables.
```

GPU representation:

```text
xp arrays for all cell-local quantities,
integer case tables on device,
preallocated row/column/value arrays for mixed cells,
no host transfer except diagnostics or fail-close messages.
```

`xp.add.at` or a backend abstraction for scatter-add is acceptable for early
implementation.  If it becomes the bottleneck, replace it with sorted COO
segment reductions.  The mathematical API should not change.

### Schur projection

Do not form dense matrices.  Provide operators:

```text
apply_Jq(delta_phi)        -> mixed-cell q residual
apply_JqT(lambda_cells)    -> nodal covector
apply_Weta_inv(rhs)        -> nodal correction solve/preconditioner
apply_Sq(lambda) = J_q W_eta^{-1} J_q^T lambda
```

Initial production candidate:

```text
matrix-free CG on S_q,
Jacobi/row-norm preconditioner first,
optional screened-Laplacian W_eta inverse as a nested matrix-free solve.
```

Fail-close conditions are part of the solver:

```text
rank/conditioning estimate bad,
line search hits sign/case boundary,
||Q_h(phi)-q||_physical too large,
Delta S_Pi exceeds configured diagnostic gate,
q bound 0<=q<=|C| violated.
```

### Bounded flux

The transport kernel should initially support the cases needed for 2D ch14:

```text
2D tensor-product grid,
periodic or wall boundaries,
P1 trace geometry,
face-normal swept area under explicit stage velocity.
```

The transport update is accepted only when the swept-volume certificate proves
boundedness.  If the certificate cannot be proven, fail close; do not clip.

## 6. Integration Strategy

### Stage 0: schema and fail-closed parse gate

Add config fields and canonicalization, but reject activation until the first
geometry gates pass.  Negative-control tests should prove inconsistent YAML is
rejected.

### Stage 1: geometry library

Implement `Q_h`, `S_h`, `J_q`, and `dS_h` on fixed strata.  Tests:

```text
uniform/nonuniform cell area exactness,
finite-difference derivative of Q_h and S_h,
periodic seam counted once,
wall cell geometry counted in physical coordinates.
```

### Stage 2: compatibility projection

Implement fixed-stratum hard projection:

```text
Q_h(phi)=q,
Schur solve,
trust-region line search,
sign-margin gates,
Delta S_Pi ledger.
```

Tests:

```text
constant-shift manufactured target,
smooth perturbation target,
nonuniform q-weighting target,
infeasible/sign-changing target fail-close.
```

### Stage 3: geometric transport and common-flux ledger

Implement bounded swept-volume `Phi_l` and typed ledger.  Tests:

```text
closed-domain global q conservation,
local boundedness without clipping,
same Phi_l used by density and momentum,
restart with pre-step state reproduces zero-start short run.
```

### Stage 4: capillary bundle virtual work

Connect `J_q`, `T_q`, `dS_h`, and `M_f`:

```text
L_B(w) constrained lift,
r_sigma(w)=-sigma dS_h[L_B(w)],
a_sigma=M_f^{-1}r_sigma.
```

Tests:

```text
static Young-Laplace range residual,
nonconstant-curvature nonzero drive,
pressure/capillary Hodge adjoint identity,
closed-interface component volume reaction.
```

### Stage 5: ch14 experimental activation

Only after Stages 1--4 pass should benchmark YAMLs activate the route.  Until
then, the YAML can be present under `status: experimental_fail_closed`.

## 7. UX/YAML Design

### Goals

YAML should state physical contracts, not algorithmic folklore.

Good UX:

```text
I want the interface state space to be geometric cell fraction.
I want hard local volume compatibility.
I want capillary from bundle virtual work.
I want failure rather than hidden correction.
```

Bad UX:

```text
turn on q-ish mass correction,
clip fractions,
smooth curvature more,
relax volume preservation until it runs.
```

### Proposed front-door YAML

Add a new state-space block under `interface`:

```yaml
interface:
  state_space:
    kind: geometric_cell_fraction
    conserved_variable: q
    normalized_view: theta
    gauge:
      variable: phi
      trace: p1_levelset
    compatibility:
      constraint: hard_cell_volume
      units: physical_volume
      projection:
        method: fixed_stratum_schur
        metric: screened_gauge_hodge
        fail_close: true
        trust_region: sign_margin
        residual_tolerance: 1.0e-11
        condition_gate: diagnostic
      ledger:
        record_delta_surface: true
        record_residuals: true
```

For legacy/current runs, the default remains:

```yaml
interface:
  state_space:
    kind: diffuse_cls
```

If the block is absent, parse as `diffuse_cls` to preserve existing YAMLs.

### Numerics block

The numerical stack must then opt into compatible operators:

```yaml
numerics:
  interface:
    transport:
      variable: q
      spatial: geometric_swept_volume
      time_integrator: tvd_rk3
      boundedness: certified
      fail_close: true
  momentum:
    form: conservative_common_flux
    terms:
      surface_tension:
        formulation: pressure_jump
        source: bundle_virtual_work
        closed_interface:
          endpoint: geometric_cell_fraction
          residual_contract:
            metric: pressure_adjoint
            constraints: [cell_volume]
            fail_close: true
  projection:
    poisson:
      operator:
        pressure_force_contract: variational_adjoint
        scalar_operator_pairing: variational_operator
        capillary_reaction_projection: pressure_component_hodge
```

The parser must reject:

```text
state_space.kind=geometric_cell_fraction with transport.variable=psi,
transport.variable=q with momentum.form!=conservative_common_flux,
bundle_virtual_work with endpoint!=geometric_cell_fraction,
geometric_cell_fraction with reinitialization.algorithm=ridge_eikonal,
fail_close=false,
boundedness other than certified,
capillary from curvature_jump on incompatible psi.
```

### Reinitialization UX

Do not overload `interface.reinitialization.algorithm` with this feature.
Compatibility projection is not reinitialization; it does not change the
material carrier.  The geometric route should use:

```yaml
interface:
  reinitialization:
    algorithm: none
  state_space:
    ...
```

or, if the parser requires an explicit name during transition:

```yaml
interface:
  reinitialization:
    algorithm: compatibility_projection
```

but only as a compatibility alias that maps to
`interface.state_space.compatibility.projection`.  It must not run the old
Ridge-Eikonal volume bracket.

### Output/diagnostics UX

Add diagnostics that expose the contract directly:

```yaml
diagnostics:
  - q_volume_conservation
  - compatibility_residual_q
  - stratum_margin
  - projection_surface_work
  - young_laplace_hodge_residual
  - common_flux_phase_momentum_certificate

output:
  fields:
    - theta
    - q
    - phi
    - pressure
    - velocity
    - capillary_hodge_residual
```

For plots:

```yaml
output:
  figures:
    - type: snapshot_series
      fields: [theta, pressure, velocity]
      interface: gamma
      scales:
        color: shared
        vector: shared
```

This matches the recent chapter-14 visualization direction: shared axes and
shared vector/color scales across time series.

### Checkpoint UX

Checkpoint settings should declare continuation intent:

```yaml
output:
  checkpoints:
    interval: 0.01
    continuation_state: pre_step_full
    include:
      - q
      - phi
      - stratum
      - transport_stage_ledger
      - compatibility_projection_ledger
      - pressure_history
      - momentum_state
```

`pre_step_full` is the only restartable checkpoint class for this route.
Post-step/plot checkpoints remain analysis artifacts.

## 8. Parser and Dataclass Changes

Minimal new config models:

```text
InterfaceStateSpaceCfg:
  kind: diffuse_cls | geometric_cell_fraction
  conserved_variable: psi | q
  gauge_variable: phi
  trace: p1_levelset
  compatibility: CompatibilityProjectionCfg

CompatibilityProjectionCfg:
  constraint: hard_cell_volume
  units: physical_volume
  method: fixed_stratum_schur
  metric: screened_gauge_hodge | nodal_hodge
  fail_close: true
  trust_region: sign_margin
  residual_tolerance
  condition_gate: diagnostic | fail_close
```

`RunCfg` should not absorb all these fields.  They belong either in a new
`InterfaceCfg` dataclass or in a `GeometryStateCfg` attached to
`ExperimentConfig`.  `RunCfg` is already overloaded with numerical operator
choices; adding material-state ownership there would make the UX harder to
reason about.

Recommended structural change:

```text
ExperimentConfig
  grid
  physics
  interface: InterfaceCfg
  run
  numerics-derived run fields
  output
```

For backward compatibility, `parse_raw` can keep reading the existing
top-level `interface` block and construct `InterfaceCfg` while preserving
`GridCfg` width parsing.

## 9. Validation Plan

Before any benchmark run:

```text
T1 config negative controls:
   reject inconsistent geometric YAML combinations.

T2 geometry manufactured tests:
   Q_h, S_h, J_q, dS_h exact/finite-difference checks.

T3 projection probes:
   small residual converges, large stratum-crossing fails close.

T4 transport algebra:
   q conservation and boundedness in periodic/wall domains.

T5 common-flux:
   density/momentum use identical Phi_l and reject q-only projections.

T6 capillary Hodge:
   static pressure-exact state gives zero projected drive;
   non-pressure-exact geometry gives nonzero drive.

T7 restart:
   pre-step full checkpoint continuation matches zero-start short run.
```

Only after those pass should ch14 YAMLs be switched from `diffuse_cls` to
`geometric_cell_fraction`.

## 10. Risks and Countermeasures

### R1. YAML becomes a bag of numerical knobs

Countermeasure: provide a profile-like front door
`interface.state_space.kind=geometric_cell_fraction`; reject hidden relaxation
options.  Expose tolerances as certificates, not stabilization.

### R2. Existing code keeps using `psi` paths silently

Countermeasure: typed phase state and ledger.  `phase_kind` must be checked by
all consumers.  Mixed `diffuse_psi` and `geometric_q` paths fail at parse or
runtime contract boundaries.

### R3. Nonuniform grid bug reappears through normalized residuals

Countermeasure: use `q` and `J_q` in all hard constraints.  `theta` is only a
view and plot field.

### R4. GPU path becomes an afterthought

Countermeasure: design the public kernels around backend arrays, struct-of-
arrays geometry cache, matrix-free operators, and sparse row tables.  CPU
reference implementations are tests, not production paths.

### R5. Compatibility projection creates hidden capillary work

Countermeasure: record `Delta S_Pi` and fail/diagnose when projection work is
large.  Physical capillary work must come only from bundle virtual work.

## 11. Established Implementation Direction

The implementation should proceed as:

```text
1. Add InterfaceStateSpaceCfg and parse gates.
2. Add geometry/ metric cell-complex package with Q_h/S_h/J_q/dS_h.
3. Add GeometricPhaseState and typed q transport ledger.
4. Add fixed-stratum compatibility projection in q-units.
5. Add bounded swept-volume flux and common-flux remap integration.
6. Add bundle virtual-work capillary route.
7. Extend checkpoint/output/diagnostics for q/phi/stratum/projection ledger.
8. Activate ch14 YAMLs only after manufactured gates pass.
```

[SOLID-X] Design/artifact only.  No solver source was changed, no tested code
was deleted, and no tactical stabilization, fallback, benchmark branch,
case-specific correction, clipping, or hidden damping route was introduced.
