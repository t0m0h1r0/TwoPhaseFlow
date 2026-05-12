# CHK-RA-CH14-AO-FASTVOL-004 - AO-Fast geometry acceleration contract

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Worktree: `.claude/worktrees/codex-ra-ch14-ao-fast-volume-20260511`

## Scope

User correction: the requested work is AO acceleration, not primarily DC usage.
This checkpoint rewrites the unfinished CHK-004 work around the actual speed
target: reduce the cost of AO geometric cell-fraction evaluation and projection
without changing the SP-AO theory.

This remains a theory/specification checkpoint.  No solver source is changed.

## Target Bottleneck

The direct AO branch materializes the right state-space idea, but the direct
cost model is wrong for production:

```text
full-grid Q/S/J/dS recomputation,
full cell-shaped Schur vectors,
line-search trials that recut the whole grid,
Python/host scalar synchronization in iteration control,
diagnostics that may pull face-native objects into scalar pressure fields.
```

The AO speedup must attack these geometric costs.  DC is at most one candidate
inside the fast route; it is not the route itself.

## Acceleration Contract

AO-Fast keeps compact active geometry tables:

```text
A          mixed/cut cells plus one-face halo
dirty      active cells whose sign/case/crossing/metric/ownership changed
node_ids   shape (|A|, 4)
case_code  shape (|A|)
lambda_e   edge crossing fractions for active edges
Q_A,S_A    active exact volume and surface contributions
J_A,dS_A   active local derivatives
face_ids   active face incidence and face-Hodge links
component  connected interface component labels
```

The direct full grid `C_h` is not the iteration domain.  Full and empty cells
are flags.  They are revisited only when dirty detection says their sign/case
or halo ownership may have changed.

## Execution Order

```text
1. detect dirty cells from sign/case changes, moved crossing intervals,
   changed boundary/periodic ownership, or changed grid metric identity.
2. reuse active rows outside dirty plus one-face halo.
3. rebuild compact SoA rows only on dirty active cells.
4. compute exact Q/S residuals on A.
5. if exact gates pass, accept without solve.
6. otherwise run the declared primary active solver.  Frozen-stratum linear
   updates and residual-monotone DC may run only as proposal-only accelerators
   unless YAML declares them as the primary solver.
7. exact-recompute Q/S on A before commit.
8. if sign/case changed, refresh A once and recheck.
9. if exact gates still fail, apply the declared fallback policy: `none` fails
   closed, while `explicit_chain` allows only the listed transition and records
   the trigger.
```

The speed contract is therefore:

```text
direct AO:  O(k |C_h|) geometry work per candidate,
AO-Fast:    O(|dirty| + k |A|) active geometry/solve work.
```

The ledger must expose `|A|`, `|dirty|`, and refreshed-cell count.  If a step
degenerates to full-grid work, it must be recorded honestly as such.

## GPU Contract

The active tables are struct-of-arrays and stay on device.  Production kernels
should be organized as:

```text
K1: classify dirty/case rows and update compact active table
K2: fused Q/S/J/dS active geometry kernel
K3: active residual/reduction kernel
K4: active J and J^T gather/scatter for PCG/Newton candidate
K5: exact active acceptance kernel and ledger scalar reduction
```

Forbidden in the inner path:

```text
full-grid cut geometry for every trial,
host-side active-cell loops,
per-iteration .get()/asnumpy synchronization,
scalar pressure reconstruction as a required AO compute step,
rebuilding metric arrays when grid identity and metric fingerprints are unchanged.
```

## Approximation And Solver Role

Approximation is allowed only to propose active candidates.  The declared local
accuracy remains:

```text
first-order frozen geometry: O(beta_C^2),
second-order secant/Hessian candidate: O(beta_C^3) if promoted.
```

Active PCG/Newton is the main robust solve path.  DC may be used only as a
cheap preconditioned candidate when the active graph and metric cache are
stable, and only if exact `Q_h-q` residuals decrease.  The AO speedup is not
credited to DC; it is credited to active geometry and device-resident kernels.

## YAML/UX Fallback Policy

The solver UX is fail-close by default:

```yaml
solver:
  primary: active_pcg_newton
  accelerators:
    dc_candidate:
      enabled: true
      role: proposal_only
      on_reject: discard_candidate
  fallback:
    policy: none
```

This means DC rejection discards the proposal.  It does not switch to PCG.
PCG/Newton is either the declared primary solver, or it is a declared fallback
target:

```yaml
solver:
  primary: residual_monotone_dc
  fallback:
    policy: explicit_chain
    chain:
      - from: residual_monotone_dc
        to: active_pcg_newton
        triggers:
          - no_exact_residual_decrease
          - trust_region_exhausted
        record_as: dc_to_pcg_declared_fallback
```

Parser gates must reject `auto`, `try_next`, `best_effort`, bare
`on_failure: active_pcg_newton`, missing chain triggers, and accelerator
settings that switch the primary solver on rejection.  The ledger must record
`solver.primary`, accelerator acceptance, fallback policy, transition, trigger,
and exact residuals before/after.

CCD/DCCD/FCCD/UCCD are considered only for smooth auxiliary maps: `phi`
prediction, `W_eta`, face-state reconstruction, and pressure-adjoint
diagnostics.  They are not AO acceleration if they differentiate `theta_C` or
replace the geometric maps.

## Proof Obligations

```text
P1. active-table Q/S/J/dS equals full-grid reference on manufactured strata.
P2. dirty detection catches every sign/case/ownership/metric change.
P3. unchanged active rows are bitwise reused or numerically identical.
P4. O(|dirty| + k |A|) counters are exposed in the ledger.
P5. GPU inner path has zero per-iteration host synchronization.
P6. approximation remainders show the declared beta_C order.
P7. exact acceptance uses active recomputation before commit.
P8. scalar pressure reconstruction is diagnostic-only and may fail closed.
P9. fallback parser rejects implicit solver transitions and records every
    declared transition.
```

## Completion Judgement

The theory is now complete enough to start implementation.  The first code
slice should not activate chapter-14 AO YAMLs.  It should implement the active
table/cache layer and manufactured tests proving active-table exactness and
dirty-refresh correctness against a full-grid reference.

## SOLID-X

Theory/specification artifact only.  No solver source, experiment result,
tested implementation deletion, FD/WENO/PPE fallback, damping/CFL workaround,
smoothing, curvature cap, benchmark branch, blanket projection,
QP-as-physics path, or hidden DCCD/UCCD damper introduced.
