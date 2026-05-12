# CHK-RA-CH14-AO-FASTVOL-011 - AO-Fast design repair after contrarian review

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Repairs: `artifacts/A/ch14_ao_fast_preimplementation_design_CHK-RA-CH14-AO-FASTVOL-009.md`
Review: `artifacts/A/review_ch14_ao_fast_preimplementation_design_CHK-RA-CH14-AO-FASTVOL-010.md`

## Scope

User direction: fix every point raised by the contrarian review before code
development.

This checkpoint repairs the design/specification only.  No solver source is
changed, no chapter-14 YAML is activated, no main merge is performed, and the
direct dense-AO branch is not deleted.

## Repair Verdict

CHK-010 found that CHK-009 had the correct high-level architecture but was not
safe to implement unchanged.  This checkpoint makes the implementation-facing
design safe enough to proceed to oracle-only C1.

The two blocker fixes are:

```text
1. Replace current-phi-only active support with A_q constraint support.
2. Replace open-ended manifest states with a closed classification enum plus
   a separate migration-status field.
```

## F1/F3 Repair - A_q Constraint Support And Target Metadata

Production AO-Fast now uses:

```text
A_q = current_phi_mixed
    union previous_phi_mixed
    union flux_touched_cells
    union target_mixed_cells where 0 < q_target_C < |C|
    union one_face_halo(A_core)
```

This fixes the transported-target counterexample.  A previously full/empty
cell that receives valid transported liquid volume is now a constraint row,
not an automatic topology failure and not an unchecked residual.

The repair does not permit a full-grid target scan every step.  `A_q` is built
from compact support streams emitted by transport and the previous active
table:

```text
previous active table -> current/previous phi mixed rows,
swept-volume transport -> flux_touched_cells,
swept-volume transport -> target-state transitions,
compact adjacency -> one-face halo.
```

Ordinary runtime cost remains:

```text
O(|A_q| + |dirty| + k * matvec(|A_q|)).
```

Full-grid scans are initialization/restart/debug/dense-oracle/declared
degenerate work only.  A support tolerance `tau_support <= tau_q` may classify
roundoff-near-empty/full rows for support, but it may not clip `q_target_A` or
replace exact residual acceptance.

Required row metadata:

```text
q_target_A,
cell_measure_A,
target_theta_A,
target_state_code_A,
flux_touched_A,
origin_mask_A.
```

`target_state_code_A` distinguishes empty, full, mixed, out-of-bounds, and
topology-required target states.  Exact residual acceptance is over `A_q`:

```text
||Q_h(phi_plus)_Aq - q_target_A||_inf <= tau_q.
```

## F2 Repair - Closed Manifest Enum

The import manifest classification enum is closed:

```text
oracle_only,
gpu_production,
reject.
```

Migration state is separate:

```text
ready,
pending_rewrite,
pending_gpu_audit,
delayed_adapter,
diagnostic_oracle.
```

Each row must declare:

```text
allowed_import_module,
forbidden_runtime_callers,
required_tests,
no_d2h_audit_status,
production_replacement_symbol.
```

No other classification token is allowed.  This prevents dense oracle code from
becoming production code through a vague intermediate label.

## F4/F5 Repair - Unit-Invariant Tolerances And Conditioning-Aware PCG

The physical q tolerance no longer uses a dimensioned `max(1, volume)` shortcut.
It is built from declared physical scales:

```text
V_ref = max(max_Aq cell_measure_A, total_domain_volume / n_cells)
Q_ref = max(V_ref, ||q_target_A||_inf)
tau_q_abs = c_abs * eps64 * V_ref
tau_q_rel = c_rel * eps64 * Q_ref
tau_q_geom = c_geom * eps64 * kappa_geom * V_ref
tau_q = max(tau_q_abs, tau_q_rel, tau_q_geom)
```

The PCG/Newton gate must record and use conditioning:

```text
tau_cg <= min(
  0.1 * tau_q / max(1, cheap_norm_est(J W^{-1/2})),
  c_cond * tau_q / max(1, cheap_kappa_est(S_q)),
  c_work * tau_surface_diag,
  c_round * sqrt(n_active) * eps64 * Q_ref
)
```

Ledger additions:

```text
rank estimate,
kappa(S_q)_est,
row-norm range,
component block count,
PCG stop reason.
```

Conditioning failure is now a distinct fail-close reason, not an unexplained
solver failure.  The estimates are active-row/Krylov/Ritz estimates.  Dense
SVD/eigendecomposition and full Schur assembly are oracle/debug-only.

## F6 Repair - Active-Set Epoch Policy

The one-refresh shortcut is replaced by a bounded active-set epoch loop:

```text
fixed_stratum -> active_set_expanded -> refreshed_epoch -> accepted
fixed_stratum -> topology_required -> fail_close or declared topology route
fixed_stratum -> invalid_degenerate -> fail_close
```

Solver fallback does not handle topology.  Fallback remains solver-family
recovery only, and only under explicit-chain YAML.

## F7 Repair - GPU Performance Pass/Fail Gates

GPU counters now have gate semantics:

```text
no production full-grid masks,
active refresh launch count bounded by a fixed small constant per refresh type,
work scales with n_active and n_dirty rather than n_cells,
N=64 and N=128 dense-oracle-vs-AO-Fast benchmarks report speed ratio,
kernel launches, host transfers, and bytes moved.
```

Vectorized `xp` is allowed only if it remains active-row compact.  Full-grid
vectorized masks are oracle/debug code, not production AO-Fast.  Benchmarks and
dense-oracle comparisons are validation gates, not work inside production
timesteps.

## F8 Repair - Project-Map Governance

C1 now explicitly includes governance:

```text
update docs/01_PROJECT_MAP.md with src/twophase/geometry ownership,
register dense oracle modules as reference/oracle-only,
document forbidden production call sites,
keep runtime construction disconnected.
```

The project map is not changed in this docs-only checkpoint because the package
does not exist yet.  The C1 implementation cannot be accepted without that map
update.

## F9 Repair - Parser Contract Earlier

Parser negative tests move into C1 as a skeleton gate.  They must reject missing
or weakened declarations for:

```text
projection.implementation: active_cached,
dense_reference: test_only,
gpu_contract.required: true,
gpu_contract.inner_host_transfers: forbidden,
solver.fallback.policy: none or explicit_chain.
```

Runtime construction still waits until C8, but parser fail-close semantics are
locked before production geometry code depends on permissive defaults.

## Updated Implementation Ladder

```text
C1. dense oracle, closed manifest, governance, parser negative skeleton.
C2. A_q ActiveGeometryTable with q_target/capacity/target-state metadata.
C3. GPU active storage plus target metadata parity and no-D2H tests.
C4. dirty/flux-touched/target-mixed/halo detector.
C5. active Q/S/J/dS kernels with active-vs-dense equality.
C6. active J/J^T/Schur with rank, conditioning, and adjointness tests.
C7. active PCG/Newton, active-set epoch loop, line search, fail-close tests.
C8. YAML runtime construction and explicit fallback UX.
C9. runtime/checkpoint/capillary adapter behind gates.
C10. chapter-14 smoke YAML after all prior gates pass.
```

## Status Against Review Findings

| Finding | Status |
|---|---|
| F1 active set from current phi only | Fixed by `A_q`. |
| F2 inconsistent manifest enum | Fixed by closed enum plus migration status. |
| F3 missing target metadata | Fixed by `q_target_A`, capacity, target state, origin masks. |
| F4 non-unit-invariant tolerances | Fixed by physical `V_ref/Q_ref` tolerance contract. |
| F5 PCG conditioning gap | Fixed by rank/condition estimates and stop-reason ledger. |
| F6 one-refresh topology shortcut | Fixed by active-set epoch policy. |
| F7 GPU counters without thresholds | Fixed by explicit GPU performance gates. |
| F8 project-map governance | Fixed by C1 acceptance requirement. |
| F9 parser strictness too late | Fixed by C1 parser negative skeleton. |
