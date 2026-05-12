# CHK-RA-CH14-AO-FASTVOL-009 - AO-Fast preimplementation design gate

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Reference branch: `codex/ra-ch14-osc-sharp-volume-20260510`
Worktree: `.claude/worktrees/codex-ra-ch14-ao-fast-volume-20260511`

## Scope

User direction: before code development, perform enough design work to avoid
avoidable rework.

This checkpoint is the implementation gate for AO-Fast.  It fixes module
ownership, import boundaries, active data shapes, GPU requirements, numerical
tolerances, fail-close behavior, validation order, commit slicing, stop
conditions, and the first coding ticket.  It does not change solver source and
does not activate a chapter-14 YAML.

CHK-011 repair status: the contrarian review findings F1--F9 are incorporated
below.  Production implementation must follow this repaired text, not the
earlier current-phi-only active-set reading.

## Non-Negotiable Invariants

The implementation must preserve the SP-AO state-space exactly:

```text
q_C        physical liquid volume per cell, not a diffuse nodal scalar
theta_C    normalized view q_C / |C|
phi_i      continuous P1 gauge/interface trace
Q_h(phi)   exact P1 cut-cell volume map
S_h(phi)   exact P1 cut-interface measure map
J_q         fixed-stratum derivative dQ_h/dphi
dS_h        fixed-stratum derivative dS_h/dphi
T_q         geometric swept-volume transport operator for q
M_f         phase-aware face Hodge built from the same geometric state
```

The following are forbidden in production AO-Fast:

```text
diffuse theta transport as a substitute for q transport,
FD/WENO/PPE fallback for the geometric volume constraint,
smoothing, clipping, global correction, or volume redistribution,
implicit dense AO fallback,
implicit DC-to-PCG fallback,
runtime dense reference projection,
host-scalar control inside GPU Krylov/Newton/DC/line-search loops,
acceptance based on approximate residuals instead of exact Q_h/S_h recompute.
```

Default failure semantics are fail-close.  Fallback is allowed only when YAML
declares a complete `solver.fallback.policy: explicit_chain`.

## Package Blueprint

The first code implementation should keep the reference oracle, active geometry
tables, projection solver, and runtime adapter separate:

```text
src/twophase/geometry/dense_reference.py
  exact dense direct-AO formulas imported or wrapped as oracle/test code only.
  No production runtime may call this path.

src/twophase/geometry/active_table.py
  ActiveGeometryTable, ActiveGeometryCache, ActiveGeometryLedger dataclasses.
  Owns compact row arrays, metric fingerprints, topology epochs, and counters.

src/twophase/geometry/active_kernels.py
  backend-native CPU/GPU active row refresh for Q_h/S_h/J_q/dS_h.
  No parser, runtime, or line-search policy here.

src/twophase/geometry/active_projection.py
  active residual, J/J^T/Schur matvecs, active PCG/Newton, exact line search,
  and declared fallback state machine.

src/twophase/geometry/import_manifest.py
  machine-readable record for direct-branch symbol classification:
  oracle_only, gpu_production, or reject.

src/twophase/simulation/config_state_space.py
  YAML parser extension after active geometry and projection tests pass.
  Parser rejects contract weakening before runtime construction.

src/twophase/simulation/* runtime adapters
  connected only after parser, active geometry, GPU, and projection gates pass.
```

Do not connect chapter-14 experiment YAMLs until the active projection has a
device-resident implementation and the dense-oracle parity tests pass.

## Active Data Model

AO-Fast iteration domain is not the full grid `C_h`.  It is the compact
constraint table `A_q`, built from current geometry, previous geometry, and the
transported target volume:

```text
A_q = current_phi_mixed
    union previous_phi_mixed
    union flux_touched_cells
    union target_mixed_cells where 0 < q_target_C < |C|
    union one_face_halo(A_core)
```

`A_q` is therefore a hard-volume constraint support, not merely the set of
currently mixed cells under `phi`.  A previously full/empty cell that receives
a valid transported target volume enters `A_q`; it is not automatically a
topology failure.  Fail-close applies only when the target is out of physical
bounds, cannot be represented on the declared topology route, or crosses a
degenerate sign stratum.

The `A_q` union is a compact-support construction.  Production code must not
find `target_mixed_cells` or `flux_touched_cells` by scanning the full `q`
array each step.  Instead:

```text
current_phi_mixed     from previous active table plus dirty/halo refresh,
previous_phi_mixed    from previous active table,
flux_touched_cells    emitted as compact support by swept-volume transport,
target_mixed_cells    emitted from transport target-state transitions,
one_face_halo         generated from compact row adjacency.
```

Full-grid support scans are allowed only during initialization, restart
validation, dense-oracle tests, explicit debug diagnostics, metric-epoch
rebuilds, or a declared degenerate exact step.  Ordinary AO-Fast runtime must
remain:

```text
O(|A_q| + |dirty| + k * matvec(|A_q|)).
```

Support classification uses a declared `tau_support <= tau_q`: values within
`tau_support` of `0` or `|C|` may be classified as empty/full for support
purposes, but the stored `q_target_A` is not clipped and final acceptance still
uses the exact physical-volume residual.

Support streams are state-changing streams, not bulk-flow streams.  In
particular, `flux_touched_cells` means cells whose transported phase-volume
flux can change an empty/full/mixed target state or alter the active band.  It
does not mean every face carrying nonzero velocity, nor every full-liquid to
full-liquid volume exchange in the bulk.  The swept-volume transport step must
emit this compact support as a side product of its boundedness certificate or
from an already compact mixed-band source list.  A second full-grid pass to
discover the same support is not AO-Fast.

The active table has an explicit capacity contract.  YAML/test fixtures must
declare `max_active_ratio`, `max_support_stream_ratio`, and
`max_epoch_growth_ratio` before production activation.  Capacity overrun,
support-stream overrun, or epoch growth beyond the declared bound is a
fail-close event unless an explicit diagnostic degenerate-exact policy is
enabled.  Runtime code must not silently reallocate through host-side lists or
fall back to a dense grid buffer.

Required arrays:

```text
cell_ids_A          shape (nA, 2), int32 or int64
node_ids_A          shape (nA, 4), int32 or int64, P1/Q1 cell-corner order
case_code_A         shape (nA,), uint8 fixed-stratum case id
edge_mask_A         shape (nA,), uint8 active crossing mask
lambda_edge_A       shape (nA, 4), real edge crossing fractions
q_A                 shape (nA,), exact active cell volumes
q_target_A          shape (nA,), transported target physical volumes
cell_measure_A      shape (nA,), physical cell measures
target_theta_A      shape (nA,), q_target_A / cell_measure_A
target_state_code_A shape (nA,), uint8 empty/full/mixed/out_of_bounds/topology
s_A                 shape (nA,), exact active interface measures
jq_local_A          shape (nA, 4), local dQ_h/dphi_node rows
ds_local_A          shape (nA, 4), local dS_h/dphi_node rows
row_norm_A          shape (nA,), diagnostic local sensitivity norm
component_A         shape (nA,), interface component id
halo_mask_A         shape (nA,), marks one-face halo rows
dirty_mask_A        shape (nA,), marks rows needing refresh
flux_touched_A      shape (nA,), marks swept-volume transport support
origin_mask_A       shape (nA,), bitmask current/previous/target/flux/halo
owner_epoch_A       shape (nA,), periodic/boundary ownership epoch
metric_key_A        shape (nA,), fingerprint of cell geometry metrics
```

The cache also owns preallocated solver buffers:

```text
r_A, p_A, z_A, Ap_A, lambda_A, delta_phi_nodes,
candidate_phi_nodes, candidate_q_A, candidate_s_A,
candidate_target_state_A, active_epoch_workspace,
device reduction workspace, line-search mask workspace.
```

Dense grid-shaped arrays may appear only in tests, debug dumps, or explicit
oracle comparison.  They are not the production iteration domain.

## Execution Graph

The production step must follow this order:

```text
1. parse YAML and reject ambiguous state-space/fallback/GPU contracts.
2. read import manifest and reject unclassified production symbols.
3. build or reuse metric/cache fingerprints on backend-native arrays; for a
   fixed grid this is a grid-level epoch check, not a per-cell full-grid scan.
4. build `A_q` from compact support streams: current phi active rows, previous
   active rows, transport-emitted flux-touched cells, transport-emitted
   target-mixed cells, and boundary/periodic one-face halo.
5. attach `q_target_A`, `cell_measure_A`, `target_state_code_A`, and
   `origin_mask_A`; reject out-of-bounds targets before solving.
6. detect dirty rows from sign, case, crossing, metric, owner, target-state, or
   flux-support changes.
7. refresh only dirty rows plus required one-face halo.
8. compute exact Q_h/S_h residuals on `A_q` and diagnostics on device.
9. run proposal-only accelerators, if declared, without committing state.
10. run declared primary active solver inside a bounded active-set epoch loop.
11. perform device-side line search under sign/case margin.
12. exact-recompute active Q_h/S_h on the accepted candidate.
13. if active-set ownership expands, advance the active-set epoch and repeat
    refresh/recheck up to the declared epoch limit; if topology is required,
    fail closed or enter the declared topology route, not solver fallback.
14. apply declared fallback policy only to solver-family failure:
    - policy none: fail closed.
    - explicit_chain: only listed transitions are allowed and ledgered.
15. commit q, phi, active table, geometry cache, and projection ledger.
```

The complexity ledger must report:

```text
n_cells, n_active, n_dirty, n_refreshed, n_halo,
n_target_mixed, n_flux_touched, n_epoch_refresh, active_epoch,
solver family, proposal family, fallback transition or none,
exact q residual before/after, exact S diagnostic before/after,
max beta_C, min sign/case margin, Delta S_Pi,
rank estimate, Schur condition estimate, GPU kernel launches, device bytes,
host-transfer count, active/support capacity, capacity-overrun flag,
dense-vs-active speed ratio when benchmarked.
```

If `n_dirty` or `n_refreshed` degenerates to full-grid work, the ledger must
record a degenerate active step.  It must not report that step as active-band
speedup.

## Direct Branch Import Manifest

Every symbol imported from `codex/ra-ch14-osc-sharp-volume-20260510` must use
the closed production classification enum:

```text
oracle_only       allowed in tests/debug dense reference only
gpu_production    allowed in AO-Fast runtime after GPU gates pass
reject            not imported
```

Migration state is a separate field, never a classification:

```text
ready, pending_rewrite, pending_gpu_audit, delayed_adapter, diagnostic_oracle
```

Each manifest row must also declare `allowed_import_module`,
`forbidden_runtime_callers`, required tests, no-D2H audit status, and the
production replacement symbol.

Initial manifest decisions:

| Source asset | Classification | Migration state | Production rule |
|---|---|---|---|
| P1 cut-volume/cut-area formulas | `gpu_production` | `pending_rewrite` | Import formulas/tests, rewrite storage and loop domain as active SoA kernels before runtime use. |
| Dense `cut_geometry_2d` output | `oracle_only` | `diagnostic_oracle` | Use only for active-vs-dense equality tests. |
| Dense `project_cell_volume_compatibility_2d` | `oracle_only` | `diagnostic_oracle` | Never call as production fallback. |
| `MetricCellComplex` metrics | `gpu_production` | `pending_gpu_audit` | Accept only if coordinates, measures, incidence, and invalidation stay backend-native. |
| `GeometricPhaseState` q/theta/phi split | `gpu_production` | `pending_rewrite` | Adopt state separation only after parser negative tests exist. |
| Dense scalar CG residual checks | `reject` | `ready` | Recreate residual reductions on device. |
| Parser fail-close gates | `gpu_production` | `pending_rewrite` | Preserve exact negative cases and messages. |
| Capillary face-Hodge contracts | `gpu_production` | `delayed_adapter` | Connect after active geometry/projection tests; preserve knowledge now. |
| Checkpoint face-history validation | `gpu_production` | `delayed_adapter` | Connect only after runtime adapter gate. |
| `pressure_hodge` diagnostics | `oracle_only` | `diagnostic_oracle` | Scalar gauge pressure remains canonical plot field unless Hodge pressure is under test. |

The direct branch can be deleted only after formulas, tests, parser/runtime
knowledge, and negative findings are represented in this branch.

## GPU Contract

The GPU path is production design, not a port of the CPU dense path.

Required gates:

```text
G1. all production arrays are backend-native xp/cp arrays.
G2. active rows use struct-of-arrays storage.
G3. geometry refresh is fused over active/dirty rows.
G4. PCG/Newton/DC/line-search inner loops contain no .get(), asnumpy,
    float(...), bool(...), list materialization, or CPU scalar branching.
G5. residual, norm, sign-margin, and acceptance predicates use device
    reductions; host observes only outer ledger scalars.
G6. work buffers are preallocated and reused.
G7. metric and incidence caches are fingerprinted and reused.
G8. tests or instrumentation count host transfers in solver loops.
G9. CPU parity tests do not force GPU control structure.
G10. no production active kernel materializes full-grid masks or dense
     cell-shaped vectors.
G11. active refresh launches are bounded by a fixed small constant per refresh
     family, independent of case-token enumeration.
G12. measured work scales with n_active and n_dirty, not n_cells.
G13. benchmark gates compare dense oracle and AO-Fast at N=64 and N=128 and
     report speed ratio, kernel launches, host transfers, and bytes moved.
G14. benchmark and dense-oracle comparisons are validation gates, not runtime
     work inside production timesteps.
G15. support compaction runs on compact candidate streams.  Production code
     must not call where/nonzero over a full-grid boolean mask to discover
     active support.
G16. active/support buffers are preallocated on device; capacity overrun
     fails closed or enters an explicitly declared diagnostic degenerate step.
```

Recommended implementation discipline:

```text
start with vectorized xp kernels where they preserve device residency,
switch hot active-row refresh and scatter/gather kernels to RawKernel or an
equivalent fused backend only after the parity tests define the expected values,
track kernel launches and host transfers from the first GPU slice.
vectorized xp is acceptable only while it stays active-row compact; a
full-grid vectorized mask is oracle/debug code, not production AO-Fast.
```

## Numerical Contracts

Committed state acceptance is based on exact geometry:

```text
||Q_h(phi_plus)_Aq - q_target_A||_inf <= tau_q
min sign/case margin >= tau_margin
active-set epoch converged within the declared epoch limit
```

Suggested tolerances:

```text
V_ref = max(max_Aq cell_measure_A, total_domain_volume / n_cells)
Q_ref = max(V_ref, ||q_target_A||_inf)
tau_q_abs = c_abs * eps64 * V_ref
tau_q_rel = c_rel * eps64 * Q_ref
tau_q_geom = c_geom * eps64 * kappa_geom * V_ref
tau_q = max(tau_q_abs, tau_q_rel, tau_q_geom)
tau_dense_active = c_oracle * eps64 * V_ref
tau_surface_diag = c_surf * eps64 * max(S_ref, ||s_A||_inf)
```

`c_abs`, `c_rel`, `c_geom`, `c_oracle`, `c_surf`, `S_ref`, and the definition
of `kappa_geom` must be declared in tests before code is accepted.  Tolerances
are physical-volume tolerances; they must not contain a dimensionless
`max(1, volume)` shortcut.  Any relaxed tolerance must be justified by a kernel
reduction order or conditioning estimate, not by visual agreement.

Approximation roles:

```text
frozen-stratum linear step:
  proposal only unless YAML declares it primary; expected local model error
  O(||delta_phi||^2) before exact recompute.

second-order/DC candidate:
  proposal only by default; may reduce iteration count if exact residual
  decreases, but may not substitute for exact Q_h acceptance.

active PCG/Newton:
  default primary route; tolerance must be chosen so algebraic residual cannot
  dominate tau_q.
```

PCG uses a target tolerance and an attainable roundoff floor.  First compute
the requested algebraic target:

```text
tau_cg_target = min(
  0.1 * tau_q / max(1, cheap_norm_est(J W^{-1/2})),
  c_cond * tau_q / max(1, cheap_kappa_est(S_q)),
  c_work * tau_surface_diag
)
```

Then compare it to the estimated attainable floor:

```text
tau_cg_floor = c_round * sqrt(n_active) * eps64 * Q_ref
```

If `tau_cg_floor > tau_cg_target`, the step is conditioning/roundoff limited:
fail closed, or enter only an explicitly declared solver transition.  Do not
spin PCG below the floor and do not accept a step on algebraic tolerance alone.
The constants are test configuration, not hidden magic numbers.  The ledger
must record cheap rank estimate, cheap `kappa(S_q)` estimate, row-norm range,
component block count, `tau_cg_target`, `tau_cg_floor`, and whether PCG stopped
by algebraic tolerance, exact residual acceptance, conditioning/roundoff
fail-close, or iteration limit.  These estimates must be piggybacked on
existing active rows or Krylov/Ritz data; dense SVD/eigendecomposition and
full-grid matrix assembly are oracle/debug-only.

## Fail-Close State Machine

Default outcomes:

| Event | Default action |
|---|---|
| YAML omits geometric state-space | keep legacy diffuse route; do not infer AO. |
| YAML declares geometric AO but weakens GPU contract | parser error. |
| Import manifest lacks a production classification | parser/import error. |
| Degenerate nodal sign stratum | fail closed; no smoothing or clipping. |
| Previously full/empty cell receives valid mixed `q_target` | include it in `A_q`; do not fail solely for support expansion. |
| Target q is out of bounds or nonrepresentable on declared topology | fail closed with topology reason. |
| Dirty set expands to full grid | allow exact step only if YAML declares degenerate exact step; ledger as degenerate, not fast. |
| Active/support capacity is exceeded | fail closed unless YAML declares diagnostic degenerate exact step. |
| Active-set epoch exceeds limit | fail closed or enter declared topology route; never solver fallback. |
| PCG roundoff floor exceeds requested target | fail closed or enter declared solver-chain transition. |
| Proposal-only DC is rejected | discard candidate; state unchanged. |
| Primary solver fails and `fallback.policy: none` | fail closed. |
| Primary solver fails and explicit chain matches | run listed fallback and record transition. |
| `pressure_hodge` diagnostic fails | diagnostic fail; scalar gauge pressure plot may still be valid. |

There is no hidden recovery from DC to PCG.  PCG/Newton is either the declared
primary solver or a declared explicit fallback target.

## Validation Ladder And Commit Slices

Implementation should proceed in small, reviewable commits:

```text
C0. design/manifest gate
    This checkpoint.  Docs only.

C1. dense oracle, manifest, governance, parser skeleton
    Import direct-branch formulas/tests as oracle code.  No runtime call site.
    Add the closed manifest enum plus migration-state schema.  Update
    docs/01_PROJECT_MAP.md with geometry package ownership/reference status.
    Add parser negative tests for explicit `active_cached`, `dense_reference`,
    `gpu_contract.required`, and `fallback.policy`.

C2. active constraint table skeleton
    Add ActiveGeometryTable/Cache/Ledger over `A_q`, including q_target_A,
    cell_measure_A, target_state_code_A, flux_touched_A, and origin_mask_A.
    Add CPU active-vs-dense tests on regular manufactured strata.

C3. GPU active table
    Move active table arrays to backend-native GPU storage; add no-inner-D2H
    instrumentation tests, target-metadata parity tests, preallocated capacity
    tests, and no full-grid where/nonzero support-compaction tests.

C4. dirty, flux-touched, target-mixed, plus one-face halo detector
    Sign/case/crossing/metric/ownership invalidation tests, including compact
    flux support, compact target support, periodic boundaries, and wall
    boundaries.  Tests must prove `flux_touched` is state-changing
    phase-volume support, not all nonzero velocity faces.  Tests must fail if
    this slice scans all cells in ordinary runtime mode.

C5. active Q/S/J/dS kernels
    CPU/GPU active geometry equality against dense oracle; declared tolerance.

C6. active J/J^T/Schur operators
    Device-resident matvec tests, adjointness checks, rank estimates, and
    conditioning gates.

C7. active PCG/Newton, epoch loop, and line search
    Exact residual acceptance, sign-margin trust region, bounded active-set
    epoch loop, conditioning fail-close, and solver-fallback separation tests.

C8. YAML runtime construction and UX
    Complete runtime config construction for `active_cached`,
    `dense_reference: test_only`, `gpu_contract.required`,
    `fallback.policy: none`, and explicit-chain behavior.

C9. runtime/checkpoint/capillary adapter
    Connect q/theta/phi handoff, checkpoint face-history validation, and
    capillary contracts behind disabled or test-only gates.

C10. chapter-14 smoke YAML
    Activate only after C1-C9 pass.  Ledger must show active/gpu counters.
```

Each slice should be committed separately.  If a slice fails a proof obligation,
fix that slice before continuing.

## Review Checklist

Before any production code merge:

```text
[ ] Dense reference is oracle/test-only.
[ ] Every imported symbol has closed manifest classification and migration state.
[ ] Active table shapes are SoA and backend-native.
[ ] `A_q` includes current/previous mixed, flux-touched, target-mixed, and halo rows.
[ ] `q_target_A`, `cell_measure_A`, target state, and origin masks are present.
[ ] No production solver loop contains inner host transfers.
[ ] No production active kernel materializes full-grid masks.
[ ] `A_q` construction consumes compact support streams and does not scan all
    cells in ordinary runtime.
[ ] Active-vs-dense parity tests pass on regular strata.
[ ] Dirty/halo tests cover sign, metric, flux, target, boundary, and periodic changes.
[ ] Exact residual gates use physical q units.
[ ] DC is proposal-only unless explicitly declared primary.
[ ] Fallback is `none` by default and explicit-chain only otherwise.
[ ] Tolerances are unit-invariant, declared, justified, and tested.
[ ] Rank/conditioning gates and PCG stop reasons are ledgered.
[ ] Rank/conditioning estimates are cheap active/Krylov estimates, not dense
    eigensolves.
[ ] `condition_gate` is fail-close for production, not merely diagnostic.
[ ] PCG tolerance separates target tolerance from attainable roundoff floor.
[ ] Active/support capacity overrun fails closed or is explicitly diagnostic.
[ ] Support compaction does not use full-grid where/nonzero in production.
[ ] GPU performance thresholds pass or fail explicitly.
[ ] Dense oracle and benchmark comparisons are outside production timesteps.
[ ] Runtime/capillary adapters remain disconnected until geometry/projection
    gates pass.
[ ] Chapter-14 YAMLs are not activated before the validation ladder passes.
```

Stop immediately if code tries to:

```text
use dense projection as a hidden fallback,
make CPU loops the production GPU design,
build production residuals only on current-phi mixed cells,
discover target support by full-grid q scans in ordinary runtime,
run dense rank/SVD/eigen diagnostics in production,
call where/nonzero over a full-grid mask in production support compaction,
define flux support from all nonzero velocity faces,
silently reallocate active/support buffers through host lists,
set production `condition_gate` to diagnostic-only,
accept approximate residuals,
weaken fail-close by parser default,
activate chapter-14 YAML before active/gpu tests,
delete the direct AO branch before the import manifest is complete.
```

## Open Questions To Resolve During C1-C3

These are bounded design questions, not blockers for the whole route:

```text
1. Active compaction primitive:
   Compaction may use backend-native prefix-sum, segmented compaction, or a
   small RawKernel over compact candidate streams.  CuPy `where/nonzero` is
   acceptable only on compact candidate arrays; full-grid masks are
   oracle/debug-only.

2. RawKernel threshold:
   Begin with vectorized xp for correctness if it stays device-resident.
   Fuse with RawKernel where launch count or memory traffic dominates.

3. Periodic seam representation:
   Decide whether `owner_epoch_A` stores quotient owner ids or explicit seam
   pairs.  Tests must cover duplicated storage versus physical DOF ownership.

4. Full-grid dirty degeneration:
   Default production policy is fail-close for chapter-14 runs.  Exact but
   ledgered degenerate full-grid steps are allowed only behind an explicit YAML
   diagnostic/debug policy.

5. Warm-start invalidation:
   Define which topology epoch changes invalidate Krylov vectors and which
   merely require residual recompute.

6. Host-transfer instrumentation:
   Choose either backend spy wrappers, ledger counters, or CuPy stream hooks.
   The test must fail when inner-loop `.get()` style transfers reappear.
```

## First Coding Ticket

The first code task after this checkpoint should be C1:

```text
Create a dense oracle module from the direct AO branch formulas and tests.
Add the closed import manifest enum and migration-status schema.
Add parser negative tests for the front-door contract.
Update docs/01_PROJECT_MAP.md for the new geometry package/reference boundary.
Expose no production runtime call site.
Add manufactured active-vs-dense test fixtures that C2 can reuse.
```

Do not start with runtime YAML activation, chapter-14 experiments, or capillary
adapter work.  The first executable contract must be the oracle and manifest
boundary.
