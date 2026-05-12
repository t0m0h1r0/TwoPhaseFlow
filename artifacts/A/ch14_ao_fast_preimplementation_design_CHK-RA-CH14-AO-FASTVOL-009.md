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

AO-Fast iteration domain is not the full grid `C_h`.  It is an active table
over mixed cells plus the one-face halo needed to detect topology and ownership
changes.

Required arrays:

```text
cell_ids_A          shape (nA, 2), int32 or int64
node_ids_A          shape (nA, 4), int32 or int64, P1/Q1 cell-corner order
case_code_A         shape (nA,), uint8 fixed-stratum case id
edge_mask_A         shape (nA,), uint8 active crossing mask
lambda_edge_A       shape (nA, 4), real edge crossing fractions
q_A                 shape (nA,), exact active cell volumes
s_A                 shape (nA,), exact active interface measures
jq_local_A          shape (nA, 4), local dQ_h/dphi_node rows
ds_local_A          shape (nA, 4), local dS_h/dphi_node rows
row_norm_A          shape (nA,), diagnostic local sensitivity norm
component_A         shape (nA,), interface component id
halo_mask_A         shape (nA,), marks one-face halo rows
dirty_mask_A        shape (nA,), marks rows needing refresh
owner_epoch_A       shape (nA,), periodic/boundary ownership epoch
metric_key_A        shape (nA,), fingerprint of cell geometry metrics
```

The cache also owns preallocated solver buffers:

```text
r_A, p_A, z_A, Ap_A, lambda_A, delta_phi_nodes,
candidate_phi_nodes, candidate_q_A, candidate_s_A,
device reduction workspace, line-search mask workspace.
```

Dense grid-shaped arrays may appear only in tests, debug dumps, or explicit
oracle comparison.  They are not the production iteration domain.

## Execution Graph

The production step must follow this order:

```text
1. parse YAML and reject ambiguous state-space/fallback/GPU contracts.
2. read import manifest and reject unclassified production symbols.
3. build or reuse metric/cache fingerprints on backend-native arrays.
4. build active table A from current phi and boundary/periodic ownership.
5. detect dirty rows from sign, case, crossing, metric, or owner changes.
6. refresh only dirty rows plus required one-face halo.
7. compute exact active Q_h/S_h residuals and diagnostics on device.
8. run proposal-only accelerators, if declared, without committing state.
9. run declared primary active solver.
10. perform device-side line search under sign/case margin.
11. exact-recompute active Q_h/S_h on the accepted candidate.
12. if topology or active-set ownership changed, refresh once and recheck.
13. apply declared fallback policy:
    - policy none: fail closed.
    - explicit_chain: only listed transitions are allowed and ledgered.
14. commit q, phi, active table, geometry cache, and projection ledger.
```

The complexity ledger must report:

```text
n_cells, n_active, n_dirty, n_refreshed, n_halo,
solver family, proposal family, fallback transition or none,
exact q residual before/after, exact S diagnostic before/after,
max beta_C, min sign/case margin, Delta S_Pi,
GPU kernel launches, device bytes, host-transfer count.
```

If `n_dirty` or `n_refreshed` degenerates to full-grid work, the ledger must
record a degenerate active step.  It must not report that step as active-band
speedup.

## Direct Branch Import Manifest

Every symbol imported from `codex/ra-ch14-osc-sharp-volume-20260510` must be
classified before use:

```text
oracle_only       allowed in tests/debug dense reference only
gpu_production    allowed in AO-Fast runtime after GPU gates pass
reject            not imported
```

Initial manifest decisions:

| Source asset | Classification | Production rule |
|---|---|---|
| P1 cut-volume/cut-area formulas | oracle_formula -> gpu_production rewrite | Import formulas and manufactured tests, rewrite storage and loop domain as active SoA kernels. |
| Dense `cut_geometry_2d` output | oracle_only | Use only for active-vs-dense equality tests. |
| Dense `project_cell_volume_compatibility_2d` | oracle_only | Never call as production fallback. |
| `MetricCellComplex` metrics | gpu_production after cache audit | Accept only if coordinates, measures, incidence, and invalidation stay backend-native. |
| `GeometricPhaseState` q/theta/phi split | design interface first | Adopt the state separation after parser negative tests exist. |
| Dense scalar CG residual checks | reject for production control | Recreate residual reductions on device. |
| Parser fail-close gates | gpu_production after parser tests | Preserve exact negative cases and messages. |
| Capillary face-Hodge contracts | delayed production | Connect after active geometry/projection tests; preserve knowledge now. |
| Checkpoint face-history validation | delayed production | Connect only after runtime adapter gate. |
| `pressure_hodge` diagnostics | diagnostic_only | Scalar gauge pressure remains canonical plot field unless Hodge pressure is under test. |

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
```

Recommended implementation discipline:

```text
start with vectorized xp kernels where they preserve device residency,
switch hot active-row refresh and scatter/gather kernels to RawKernel or an
equivalent fused backend only after the parity tests define the expected values,
track kernel launches and host transfers from the first GPU slice.
```

## Numerical Contracts

Committed state acceptance is based on exact geometry:

```text
||Q_h(phi_plus)_A - q_target_A||_inf <= tau_q
min sign/case margin >= tau_margin
topology epoch unchanged, or one refresh/recheck succeeds
```

Suggested tolerances:

```text
tau_q_cpu = 10 * eps64 * max(1, max_C |C|)
tau_q_gpu = c_gpu * eps64 * max(1, max_C |C|)
tau_dense_active = c_oracle * eps64 * max(1, max_C |C|)
tau_surface_diag = c_surf * eps64 * max(1, max_A S_A)
```

`c_gpu`, `c_oracle`, and `c_surf` must be declared in tests before code is
accepted.  Any relaxed tolerance must be justified by a kernel reduction order
or conditioning estimate, not by visual agreement.

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

PCG tolerance should satisfy:

```text
tau_cg <= min(0.1 * tau_q, c_work * tau_surface_diag,
              c_round * sqrt(n_active) * eps64)
```

The constants are test configuration, not hidden magic numbers.

## Fail-Close State Machine

Default outcomes:

| Event | Default action |
|---|---|
| YAML omits geometric state-space | keep legacy diffuse route; do not infer AO. |
| YAML declares geometric AO but weakens GPU contract | parser error. |
| Import manifest lacks a production classification | parser/import error. |
| Degenerate nodal sign stratum | fail closed; no smoothing or clipping. |
| Full/empty cell target changes without topology route | fail closed. |
| Dirty set expands to full grid | allow exact step only if declared; ledger as degenerate, not fast. |
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

C1. dense oracle import
    Import direct-branch formulas/tests as oracle code.  No runtime call site.

C2. active table skeleton
    Add ActiveGeometryTable/Cache/Ledger and CPU active-vs-dense tests on
    regular manufactured strata.

C3. GPU active table
    Move active table arrays to backend-native GPU storage; add no-inner-D2H
    instrumentation tests.

C4. dirty plus one-face halo detector
    Sign/case/crossing/metric/ownership invalidation tests, including
    periodic and wall boundaries.

C5. active Q/S/J/dS kernels
    CPU/GPU active geometry equality against dense oracle; declared tolerance.

C6. active J/J^T/Schur operators
    Device-resident matvec tests and adjointness checks.

C7. active PCG/Newton and line search
    Exact residual acceptance, sign-margin trust region, and fail-close tests.

C8. YAML parser and UX
    `active_cached`, `dense_reference: test_only`, `gpu_contract.required`,
    `fallback.policy: none`, and explicit-chain negative tests.

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
[ ] Every imported symbol has manifest classification.
[ ] Active table shapes are SoA and backend-native.
[ ] No production solver loop contains inner host transfers.
[ ] Active-vs-dense parity tests pass on regular strata.
[ ] Dirty/halo tests cover sign, metric, boundary, and periodic changes.
[ ] Exact residual gates use physical q units.
[ ] DC is proposal-only unless explicitly declared primary.
[ ] Fallback is `none` by default and explicit-chain only otherwise.
[ ] Tolerances are declared, justified, and tested.
[ ] Runtime/capillary adapters remain disconnected until geometry/projection
    gates pass.
[ ] Chapter-14 YAMLs are not activated before the validation ladder passes.
```

Stop immediately if code tries to:

```text
use dense projection as a hidden fallback,
make CPU loops the production GPU design,
accept approximate residuals,
weaken fail-close by parser default,
activate chapter-14 YAML before active/gpu tests,
delete the direct AO branch before the import manifest is complete.
```

## Open Questions To Resolve During C1-C3

These are bounded design questions, not blockers for the whole route:

```text
1. Active compaction primitive:
   CuPy `where/nonzero` may be enough initially, but prefix-sum compaction
   should be measured before hot-kernel work.

2. RawKernel threshold:
   Begin with vectorized xp for correctness if it stays device-resident.
   Fuse with RawKernel where launch count or memory traffic dominates.

3. Periodic seam representation:
   Decide whether `owner_epoch_A` stores quotient owner ids or explicit seam
   pairs.  Tests must cover duplicated storage versus physical DOF ownership.

4. Full-grid dirty degeneration:
   Decide whether this is allowed as an exact but ledgered degenerate step or
   rejected for production chapter-14 runs by YAML policy.

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
Add an import manifest entry for every symbol.
Expose no production runtime call site.
Add manufactured active-vs-dense test fixtures that C2 can reuse.
```

Do not start with runtime YAML activation, chapter-14 experiments, or capillary
adapter work.  The first executable contract must be the oracle and manifest
boundary.
