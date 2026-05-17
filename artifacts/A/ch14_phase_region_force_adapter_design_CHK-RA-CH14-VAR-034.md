# CHK-RA-CH14-VAR-034 - PhaseRegion force adapter boundary design

Date: 2026-05-17

Scope: design the production-adjacent boundary for a future PhaseRegion
capillary force adapter.  This checkpoint is design-only: it does not add a
runtime force path, pressure/velocity coupling, nonlinear optimization,
micro-step, or T/8.

## Why This Gate Exists

`CHK-RA-CH14-VAR-033` proved that the Ch14 runtime initial snapshot can support
a zero-step fixed-stratum face-work diagnostic.  It did not define how a
production-adjacent object should own and expose that result.  The next risk is
accidentally hiding three different responsibilities in one helper:

```text
q_l / q_g ownership
phi / psi chart gauge
surface-energy face cochain
```

If those are bundled without an explicit admission status, the adapter would
look production-ready even though the Hodge/reaction residuals are still only
diagnostics and `force_admissible` remains false.

## Ownership Boundary

The adapter must be a one-way builder from a runtime snapshot into an explicit
candidate.  It must not mutate the runtime state and must not consume its own
candidate through pressure/velocity projection.

```text
RuntimePhaseSnapshot
  owns:
    grid
    phase_state.phi
    phase_state.q_l
    rho_l, rho_g, sigma
    bc_type / metric epoch

PhaseRegionForceCandidate
  owns:
    q_g_target = |C| - q_l
    psi_chart = H(-phi)
    face_mass_metric M_f
    closed-interface Riesz cochain s_f
    work diagnostics
    Hodge / component-reaction diagnostics
    force_admissible = false
```

The candidate is a diagnostic object until a later gate proves a pressure and
velocity consumer uses the same metric and energy pairing.

## A3 Contract

| Equation | Discretization | Adapter field / code boundary |
|---|---|---|
| `q_g = |C| - q_l` | exact finite-volume owner complement | `PhaseOwnerMapResult` |
| `psi = H(-phi)` | runtime chart evaluated on the admission nodes | `psi_chart` |
| `rho = rho_g + (rho_l-rho_g) psi` | nodal density for arithmetic face mass | `face_mass_components` input |
| `M_f` | face measure times face density on current grid epoch | `face_weight_components` |
| `T_h(u_f)=-D_f(psi_f u_f)` | FCCD conservative fixed-stratum transport | `transport_increment_from_face_velocity` |
| `s_f=-M_f^{-1}T_h^T dE_h` | closed-interface Riesz representative | `ClosedInterfaceRieszCochain` |
| `dE_h[T_h(u_f)]+<s_f,u_f>_{M_f}=0` | local virtual-work gate | `VirtualWorkCheck` |
| `s_f = range + hodge` | diagnostic pressure range/Hodge split | `WeightedHodgeDecomposition` |
| `hodge(s_f - beta B_f)` | diagnostic component-reaction residual | `ComponentReactionHodgeGate` |

## Candidate API Shape

The next code gate should add only a small contract helper, not a production
solver route:

```text
PhaseRegionForceAdmission
  valid: bool
  reason: str
  force_admissible: bool
  runtime_steps: int
  owner_map: PhaseOwnerMapResult
  cochain: ClosedInterfaceRieszCochain
  self_work: VirtualWorkCheck | None
  probe_work: VirtualWorkCheck | None
  hodge: WeightedHodgeDecomposition | None
  reaction: ComponentReactionHodgeGate | None
  metrics: dict[str, float]
```

Required invariants:

```text
runtime_steps == 0
force_admissible is False
owner_map.owner_phase == GAS
owner_map.complement_used is visible
phase_state.compatibility_residual_linf is reported, not hidden
face metric is built from nodal density, not cell density
all virtual displacements remain in the fixed stratum
```

The helper may return `valid=False` for admission failures such as bad
capacity, irregular stratum, nonpositive face weights, or failed work pairing.
It must not repair them by smoothing, damping, tolerance weakening, skipping
rebuilds, changing CFL, or falling back to FD/WENO/PPE families.

## Boundary and Nonuniform Policy

The adapter must never assume uniform spacing.  All geometry and face metrics
come from the runtime grid:

```text
cell_area = diff(x_edges) outer diff(y_edges)
face_measure = existing face_measure_components(grid)
face_density = arithmetic average of nodal rho on each face
FCCD weights = current grid / boundary epoch
```

Boundary state is part of the candidate identity.  At minimum the candidate
must report:

```text
bc_type
grid_alpha
min_dx
metric_epoch or explicit grid epoch
face component shapes
phase_threshold
```

Periodic and wall boundaries are not special fixes.  They are different
discrete charts for the same fixed-stratum identity, and any future consumer
must use the same FCCD divergence and face metric as the candidate.

## Vectorization Layout

The candidate should keep structure-of-arrays layout:

```text
face_components = [u_x_faces, u_y_faces]
face_weight_components = [M_x_faces, M_y_faces]
component metadata = packed atlas arrays
diagnostic scalars = flat metrics dict
```

This preserves vectorized face operations and avoids per-cell object graphs.
Dense Hodge matrices remain diagnostic-only and must not become a runtime
production dependency.  The production-adjacent helper may compute them only
when explicitly requested by a diagnostic flag.

## Nonlinear Optimization Policy

No nonlinear optimization belongs in this adapter.  The adapter consumes a
runtime chart and builds a force candidate on that fixed stratum.  If a later
gate needs to move the PhaseRegion state, it must use the previously designed
projection ladder:

```text
F0 chart moments
F1 low-mode KKT
F2 trust-checked second correction
F3 full nonlinear solve only as oracle / fail-close analysis
```

This prevents a slow optimizer from becoming an implicit repair step for
off-manifold `q` noise.

## Next Implementable Unit

The next safe code unit is a contract-level helper that factors the logic from
`diagnose_phase_region_runtime_force_dry_run.py` into reusable pure functions
or dataclasses while preserving `force_admissible=false`.  Acceptance requires:

```text
unit tests:
  q_l -> q_g exact complement
  nodal-density face metric shape and value checks
  cell-density metric misuse fails closed
  fixed-stratum velocity scaling stays inside sign margin

experiment:
  existing runtime force dry-run remains PASS
```

The helper still must not be connected to pressure/velocity projection or a
T/8 runtime run.

## Validation

```text
git diff --check = PASS
docs/wiki WIKI count = 427
docs/wiki/code WIKI-L count = 60
targeted design/wiki/ledger scan = PASS
```
