# CHK-RA-CH14-AO-FASTVOL-006 - AO-Fast implementation design policy

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Reference branch: `codex/ra-ch14-osc-sharp-volume-20260510`
Worktree: `.claude/worktrees/codex-ra-ch14-ao-fast-volume-20260511`

## Scope

User request: design the high-speed AO route, using already developed work from
`codex/ra-ch14-osc-sharp-volume-20260510` when useful.

This checkpoint is a design/specification checkpoint.  No solver source is
changed and no chapter-14 YAML is activated.

## Diagnosis Of The Reference Branch

The reference branch is valuable because it implements the SP-AO state-space
semantics end-to-end:

```text
Q_h/S_h P1 cut geometry,
J_q/dS_h fixed-stratum derivatives,
q/theta/phi phase-state split,
hard compatibility projection,
geometric swept-volume/common-flux bridge,
capillary face-Hodge/runtime gates,
fail-close YAML parser and tests,
metric-cell-complex cache reuse.
```

It is not yet the production fast route.  Its dominant cost pattern remains:

```text
dense cell arrays for geometry and derivatives,
full-grid Q/S/J/dS recomputation per Newton/line-search trial,
masked vector work over all cells for every cut case,
cell-shaped Schur vectors,
scalar host synchronization inside CG residual tests,
runtime materialization paths built around dense q/theta/phi fields.
```

Therefore the reference branch should be treated as an exact dense oracle and
as a source of local formulas, gates, tests, and runtime contracts.  It should
not be merged wholesale as the AO-Fast compute path.

## Reuse Matrix

Reuse directly or with minimal adaptation:

```text
MetricCellComplex cache/invalidation:
  Keep as the metric fingerprint and device-resident edge/cell-measure cache.

P1 cut formulas:
  Reuse polygon/crossing/case algebra for Q_h, S_h, J_q, and dS_h.
  Change the storage target from dense (Nx,Ny,...) arrays to compact active rows.

GeometricPhaseState:
  Keep the q/theta/phi separation and q-unit compatibility ledger.
  Extend the ledger with active counters and fallback policy fields.

config_state_space parser:
  Keep fail-close stack validation.
  Extend with AO-Fast solver/fallback schema from CHK-005.

Runtime capillary/face-Hodge gates:
  Keep the semantic gates and fail-close behavior.
  Change their geometry input to a dense reference view or active geometry view.

Tests:
  Reuse manufactured dense exactness tests as oracle tests.
  Add active-vs-dense equality, dirty-refresh, and no-inner-D2H tests.
```

Rewrite rather than reuse as production:

```text
project_cell_volume_compatibility_2d:
  Keep as dense reference/debug oracle only.
  Production uses active_cached projection and device-resident Krylov control.

cut_geometry_2d / cut_geometry_derivatives_2d dense outputs:
  Keep API-compatible dense reference.
  Production path emits ActiveGeometryTable rows.

Schur CG residual control:
  Replace scalar-host residual tests with device-resident reductions and a
  single outer ledger transfer.

Chapter-14 AO YAML activation:
  Do not import until active table, parser gates, and reference equality tests
  pass.
```

## Target Architecture

Introduce AO-Fast as a second implementation behind the same SP-AO maps:

```text
DenseReferenceGeometry
  exact dense oracle from the reference branch.

ActiveGeometryTable
  cell_ids         shape (|A|, 2)
  node_ids         shape (|A|, 4)
  case_code        shape (|A|)
  edge_lambda      shape (|A|, 4)
  q_A, theta_A     shape (|A|)
  s_A              shape (|A|)
  jq_local_A       shape (|A|, 4)
  ds_local_A       shape (|A|, 4)
  row_norm_A       shape (|A|)
  component_A      shape (|A|)
  dirty_mask_A     shape (|A|)
  halo_mask_A      shape (|A|)

ActiveGeometryCache
  previous signs/cases/crossings,
  metric fingerprint,
  active table,
  one-face halo,
  warm-start lagrange/vector data,
  last accepted residual ledger.
```

`A` is the set of mixed cells plus one-face halo.  Full and empty cells are
represented by flags and cell measures, not by re-cutting their geometry at
every iteration.

## AO-Fast Step

The production projection step is:

```text
1. Load q^- and predicted phi^-.
2. Build or refresh ActiveGeometryCache.
3. Detect dirty cells from sign/case/crossing/metric/ownership changes.
4. Refresh compact rows on dirty plus one-face halo only.
5. Compute exact active residual R_A = q^-_A - Q_A(phi^-).
6. Reject immediately if q^- changes a full/empty cell outside the declared
   active/topology route.
7. Try proposal-only accelerators if configured; accepted proposals must pass
   exact active Q/S gates.
8. Run the declared primary active solver, normally matrix-free PCG/Newton.
9. Evaluate line-search candidates on device, recomputing exact active Q/S.
10. Commit only after exact q-unit residual, sign/case margin, and
    projection-work gates pass.
11. Record active counters and fallback policy fields.
```

The direct dense oracle may run in tests, diagnostics, or an explicitly named
debug mode.  It is not an implicit runtime fallback.

## Solver Policy

Default production YAML:

```yaml
interface:
  state_space:
    compatibility:
      projection:
        implementation: active_cached
        dense_reference: test_only
        solver:
          primary: active_pcg_newton
          accelerators:
            frozen_linear_candidate:
              enabled: true
              role: proposal_only
              on_reject: discard_candidate
            dc_candidate:
              enabled: false
              role: proposal_only
              on_reject: discard_candidate
          fallback:
            policy: none
```

`dense_reference: test_only` means "compare against the oracle in tests or
diagnostics."  It does not mean "fall back to dense AO when active AO fails."
Dense direct AO is not a runtime fallback policy.

## Complexity And Accuracy Contract

The dense reference has cost:

```text
O(k |C_h|)
```

for `k` geometry/line-search evaluations.  The production target is:

```text
O(|dirty| + k |A|)
```

where `|A|` is the active interface-band graph.  If dirty detection expands to
the full grid, the ledger must record the degeneration.  It may not report the
step as active-band work.

Accuracy is not relaxed:

```text
Committed q residual:       ||Q_h(phi^+) - q^-||_inf <= tau_q.
Active-vs-dense test:       Q_A, S_A, J_A, dS_A match DenseReferenceGeometry
                            on manufactured regular strata.
Approximate proposal order: frozen first-order O(beta_C^2);
                            promoted second-order O(beta_C^3).
```

For CPU dense-reference equality, expected tolerance is roundoff-level for the
same formula path.  For GPU active kernels, the test tolerance must be declared
in physical volume/length units and bounded by a small multiple of machine
epsilon and local cell measure; it is not a mass-clipping tolerance.

## First Implementation Slices

1. Import reference geometry as `DenseReferenceGeometry` and tests only.
2. Add `ActiveGeometryTable` builder using the same P1 case algebra.
3. Add active-vs-dense manufactured tests for uniform and nonuniform cells.
4. Add dirty detector and one-face halo refresh tests.
5. Add active matrix-free `J`, `J^T`, and Schur operators with no inner-loop
   host synchronization.
6. Extend YAML parser with `implementation: active_cached`, explicit fallback
   policy, and rejection of dense implicit fallback.
7. Connect runtime/capillary gates after active ledger counters are present.
8. Activate chapter-14 AO YAMLs only after the active route passes reference
   equality and fail-close tests.

## SOLID-X

Design/specification artifact only.  No solver source, experiment result,
tested implementation deletion, FD/WENO/PPE fallback, damping/CFL workaround,
smoothing, curvature cap, benchmark branch, blanket projection,
QP-as-physics path, implicit dense fallback, implicit PCG fallback, or hidden
DCCD/UCCD damper introduced.
