# CHK-RA-CH14-VAR-017 - PhaseRegion InterfaceAtlas implementation design

Date: 2026-05-17

Scope: theory-to-implementation design only.  No code, runtime route, force
coupling, T/8 run, tolerance weakening, smoothing, damping, CFL retuning,
rebuild skipping, FD/WENO/PPE fallback, or hidden CPU fallback is introduced by
this checkpoint.

## 1. Design target

The previous reset fixed the physical owner as a finite-dimensional phase
region:

```text
Omega_g(t) = gas phase region
Gamma(t) = boundary Omega_g(t)
q_i(t) = |Omega_g(t) cap cell_i| / |cell_i|
E[Omega_g] = sigma Per(Omega_g)
```

The implementation must therefore own a discrete region object, not a bare
cell-volume field and not a pretty level-set array:

```text
R_h = PhaseRegionBatch(components, charts, constraints, metric_epoch)
q_phys = Q_h(R_h)
r = q_T - q_phys
E_h = sigma sum_c perimeter(component_c)
```

Here `q_T` is the transported finite-volume measure, `q_phys` is the cell
measure induced by the admitted region, and `r` is a diagnostic residual.  The
residual must not be silently converted into curvature, pressure, velocity, or
force.

## 2. Failure knowledge inherited

| Evidence | Inherited lesson | Implementation consequence |
|---|---|---|
| Baseline capillary-wave oracle PASS in WIKI-E-064 | Smooth graph-chart geometry has a valid low-mode variational signal. | Preserve graph chart as a restricted component kernel. |
| Screened graph-q runtime FAIL in WIKI-E-064 and CHK-RA-CH14-OSC-EIGHTH-032 | Exact transported `q` can contain modes outside smooth interface geometry. | Runtime admission must report `r`; all-cell q exactness is not a force gate. |
| Graph rebuild `compat_linf=0` | Zero compatibility error after rebuild can mean q was redefined by the chart, not preserved from pre-rebuild transport. | Admission reports must distinguish `q_T`, `q_phys`, and `r`. |
| Exact q projection makes the interface jagged | Treating every cell volume as physical overconstrains the smooth boundary. | Full nonlinear exact projection is fail-close/oracle only, not runtime default. |
| Surface tension amplifies high-frequency interface error | Curvature is a first/second derivative path from geometry error to force. | Never let non-geometric residual enter `E_h` or curvature through a reconstructed `phi`. |
| Graph and closed droplet were handled as separate theories | Chart type was confused with the owner. | Both become components of the same `PhaseRegion/InterfaceAtlas`. |
| Pressure, velocity, face cochain, and boundary spaces can disagree | A force can be algebraically correct but energetically wrong. | Force coupling remains blocked until `T_h` and `T_h^*` work identities are explicit. |

## 3. Variational contract

The discrete object is a point on a finite-dimensional admissible stratum:

```text
R_h in S_tau
S_tau = chart atlas + topology + boundary attachments + orientation + phase labels
```

For a fixed stratum `tau`, the required maps are:

```text
Q_h: R_h -> q_phys
P_h: R_h -> total perimeter
C_h: R_h -> declared constraints
T_h: R_h -> production endpoint state for force coupling  (future)
```

The one-step design invariant is:

```text
same R_h owns Q_h, E_h=sigma P_h, C_h, and future T_h
```

This forbids four-way splitting:

```text
q is transported
phi is reconstructed
force is computed from phi
velocity is projected in a separate metric
```

unless the maps are explicitly tied back to the same `R_h`.

## 4. Multi-component atlas

The first multi-component target is:

```text
Omega_g = Omega_bubble union Omega_layer
Gamma = Gamma_bubble union Gamma_layer
```

Represent this as:

```text
InterfaceAtlas
  component 0:
    chart_type: ClosedCurveChart or closed radial chart
    role: bubble
    phase_inside: gas
    orientation: positive gas-inside
    boundary_attachment: none
  component 1:
    chart_type: GraphChart or OpenCurveChart
    role: top air layer
    phase_above: gas
    orientation: positive gas-side normal
    boundary_attachment: top / side / periodic / wall
```

The chart types differ, but the mechanics do not:

```text
E_h = sigma (L_bubble + L_layer)
q_phys = Q_h(component_bubble) + Q_h(component_layer)
C_total = sum_i q_phys_i |cell_i|
```

Component volumes are optional constraints.  They can be exact only when the
topology ledger says the component identity is material over the step.  The
default hard constraint is total gas volume.

## 5. Vectorization-ready data layout

Use a packed component-major layout.  The hot path should avoid Python loops
over cells.  Small loops over chart types are acceptable because each chart
type dispatches to a vectorized kernel.

```text
PhaseRegionBatch
  batch_size: int
  component_offsets: int[B + 1]
  component_to_batch: int[n_components]
  chart_type: int[n_components]
  topology: int[n_components]
  attachment: int[n_components]
  orientation: float[n_components]
  phase_role: int[n_components]
  constraint_policy: int[n_components]
  dof_offsets: int[n_components + 1]
  dofs: float[n_dof]
  vertex_offsets: int[n_components + 1]
  vertices: float[n_vertices, 2]
  active_cell_offsets: int[n_components + 1]
  active_cell_ids: int[n_active]
  active_weights: float[n_active]
```

Dense oracle arrays are allowed for small diagnostic experiments:

```text
q_component: float[n_components, nx, ny]
q_phys: float[batch_size, nx, ny]
r: float[batch_size, nx, ny]
```

Runtime-facing kernels should prefer active-band sparse or CSR-like arrays:

```text
component c contributes only to active_cell_ids[lo:hi]
q_phys = segment_sum(component_contrib, component_to_batch, active_cell_ids)
```

Required vector primitives:

- `take`/gather for component-local dofs and active cells;
- `segment_sum` or `bincount` for q, perimeter, area, and residual reductions;
- padded chart blocks for fixed-mode graph and closed radial kernels;
- `where` masks for attachment/orientation branch selection;
- `einsum`/batched matvecs for low-mode Jacobians and KKT solves.

The scalar chart helpers remain valid only as reference kernels.  The public
atlas path must be batch-first so graph, closed, and open components can share
the same reduction and validation code.

## 6. Avoiding expensive nonlinear optimization

The runtime default must not be a large nonlinear solve over cells.  Use an
admission ladder:

### F0: direct moment projection

Map `q_T` to low-dimensional chart parameters by physically interpretable
moments.

For a closed bubble:

```text
area -> base radius
centroid -> center
angular low moments -> cos/sin radial modes
```

For a top layer:

```text
column volumes -> graph height modes
edge moments -> boundary attachment correction
low Fourier/Chebyshev modes -> smooth interface modes
```

Then apply one exact total-volume correction through the base mode or a shared
scalar Lagrange correction.  The remaining residual is reported as `r`.

### F1: small linearized variational KKT

When F0 is not enough, solve only over admitted low modes:

```text
min_delta 1/2 ||J_Q delta - r_low||_W^2
          + alpha delta^T H_E delta
subject to J_C delta = c
```

where `delta` is the chart-mode correction, not a cellwise unknown.  The matrix
size is:

```text
num_chart_modes + num_constraints
```

not `nx * ny`.  This makes the solve batchable and keeps full-grid data in
vectorized reductions that build `J_Q^T W J_Q`, `J_C`, and the right-hand side.

### F2: guarded second correction

Allow at most one additional low-mode correction if all are true:

```text
topology unchanged
attachment unchanged
orientation unchanged
E_h does not increase unexpectedly
actual residual reduction matches the linear prediction
```

This is a trust check, not tolerance weakening.

### F3: full nonlinear solve

Reserve full nonlinear optimization for oracle, diagnosis, and fail-close
analysis.  It must not become the standard runtime path unless a later
artifact proves cost, convergence, and energy consistency.

## 7. Closed bubble + top layer smoke oracle design

Before force coupling or T/8, build a no-runtime oracle with synthetic
`PhaseRegionBatch` entries:

```text
R_h[0] = bubble component + top-layer component
q_phys = Q_h(R_h)
E_h = sigma (L_bubble + L_layer)
r = q_T - q_phys
```

The oracle must visualize:

- the two atlas components over the grid;
- `q_phys`;
- synthetic `q_T`;
- residual `r`;
- component perimeter contributions;
- total and optional component volume diagnostics.

It must check:

- topology/attachment/orientation/phase labels are explicit;
- total gas volume is exact after F0/F1 correction;
- component volume policy is declared;
- `E_h` is perimeter of the same `R_h`;
- finite-difference `dE/dC` and low-mode covectors match analytic values;
- residual `r` is never used as force;
- scalar-vs-batch parity holds for the same atlas.

## 8. Equation -> Discretization -> Code design map

This checkpoint writes no code, but fixes the intended code ownership:

| Equation object | Discrete object | Future code surface |
|---|---|---|
| `Omega_g` | `PhaseRegionBatch` | `src/twophase/geometry/phase_region.py` |
| `Gamma = boundary Omega_g` | `InterfaceAtlas` components | `src/twophase/geometry/interface_atlas.py` |
| `q_i = |Omega_g cap cell_i| / |cell_i|` | `Q_h(R_h)` reductions | `src/twophase/geometry/phase_region_measure.py` |
| `E = sigma Per(Omega_g)` | component perimeter sum | existing chart geometry kernels plus atlas reductions |
| total/component volume constraints | declared `constraint_policy` and `C_h` | atlas validators and projection result objects |
| non-geometric measure residual | `r = q_T - q_phys` | projection/admission reports only |
| force endpoint | future `T_h` and `T_h^*` | blocked until work-identity artifact |

## 9. Module sequence

Implement later in these convergent modules:

1. Schema and validators only: `PhaseRegionBatch`, `InterfaceAtlas`, labels,
   attachments, orientation, and constraint policies.
2. Dense smoke oracle: closed bubble + top layer, visualization, parity, and
   finite-difference checks.
3. F0/F1 admission: synthetic `q_T` to admitted `R_h`, exact total volume, and
   visible residual.
4. Runtime snapshot adapter: read runtime `q_T` snapshots into the same report
   format while keeping `force_admissible=0`.
5. Force coupling: only after `T_h`, `T_h^*`, face cochains, pressure metric,
   and boundary conditions pass work-identity checks.

Each module requires code review, theory consistency review, and targeted
tests before the next module starts.

## 10. Decision

Proceed toward implementation only through the atlas schema and smoke oracle.
Do not repair screened graph-q projection as the main line.  The main line is:

```text
PhaseRegion-primary
-> InterfaceAtlas components
-> vectorized Q_h and perimeter reductions
-> F0/F1 low-mode admission
-> residual as diagnostic
-> force coupling only after work identities
```
