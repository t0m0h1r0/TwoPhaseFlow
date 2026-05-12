# CHK-RA-CH14-AO-FASTVOL-010 - Contrarian review of AO-Fast preimplementation design

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Reviewed artifact: `artifacts/A/ch14_ao_fast_preimplementation_design_CHK-RA-CH14-AO-FASTVOL-009.md`
Reference branch inspected: `codex/ra-ch14-osc-sharp-volume-20260510`

## Verdict

The CHK-009 direction is basically the right architecture: dense direct AO as
oracle, production AO-Fast as active SoA geometry plus GPU-resident projection,
fail-close by default, and no implicit dense/DC/PCG fallback.

But it is not yet safe to begin production implementation unchanged.  The
review found two blockers and several high-risk design gaps.  The next step
should be a CHK-011 design repair before C1/C2 code begins.

Resolution status: CHK-011 repaired all findings in
`artifacts/A/ch14_ao_fast_design_repair_CHK-RA-CH14-AO-FASTVOL-011.md` and
updated the implementation-facing CHK-009 design text.  Production
implementation must use the repaired CHK-009/CHK-011 contract.

## Findings

### F1 BLOCKER - Active set is defined from current phi, not from target q support

Evidence:

```text
CHK-009 lines 90-92: A is mixed cells plus one-face halo.
CHK-009 lines 133-136: build A from current phi, then compute residuals on A.
CHK-009 lines 225-228: acceptance checks Q_h(phi_plus)_A - q_target_A.
CHK-009 line 278: full/empty target changes fail closed.
SP-AO lines 250-262: after transport, the constraint is Q_h(phi)_C = q^-_C.
SP-AO lines 316-331: q is advanced by swept-volume transport.
```

Counterexample:

```text
At time n, cell C is empty by phi, so C is outside mixed A.
A certified swept-volume flux moves a small amount of liquid into C, so
0 < q^-_C < |C|.
```

Under CHK-009, either C is not in the residual set and the hard constraint is
not checked, or it is caught as a full/empty target change and fails closed.
The first outcome is wrong; the second makes ordinary interface advection
unusable unless every such transport is declared a topology route.

Required repair:

```text
Define the constraint set A_q as the union of:
  current mixed cells,
  previous mixed cells,
  flux-touched cells,
  cells with 0 < q_target_C < |C|,
  one-face halo needed for sign/case/ownership detection.

Store q_target_A and cell_measure_A explicitly.
Compute exact residuals over A_q, not only current phi-mixed rows.
Keep fail-close for nonrepresentable topology changes, not for every
previously full/empty cell receiving valid transported q.
```

### F2 BLOCKER - Import manifest enum is internally inconsistent

Evidence:

```text
CHK-009 lines 167-170: allowed classifications are oracle_only,
gpu_production, reject.
CHK-009 lines 175-186: table uses oracle_formula -> gpu_production rewrite,
design interface first, delayed production, and diagnostic_only.
CHK-009 lines 130-132: production rejects unclassified symbols.
```

This cannot become a machine-readable manifest.  The gate says unclassified
symbols fail, but the table introduces non-enum states.  That ambiguity is
exactly how dense reference helpers can leak into production under a friendly
interpretation.

Required repair:

```text
Use a closed enum only:
  oracle_only, gpu_production, reject.

Represent migration state separately:
  pending_rewrite, pending_gpu_audit, delayed_adapter, diagnostic_oracle.

Every row must also declare:
  allowed_import_module,
  forbidden_runtime_callers,
  required tests,
  no-D2H audit status,
  production replacement symbol.
```

### F3 HIGH - Data model lacks q_target_A, capacity, and target-state metadata

Evidence:

```text
CHK-009 lines 96-111 define q_A/s_A/J/dS but not q_target_A.
CHK-009 lines 117-119 define candidate buffers but not target q buffers.
CHK-009 lines 148-155 require residual ledger fields.
```

The projection solve cannot be specified only by current geometry rows.  It
needs target volumes, physical capacities, and target-state classification for
each active constraint row.

Required repair:

```text
Add q_target_A, cell_measure_A, target_theta_A, target_state_code_A, and
flux_touched_A.
Define target_state_code_A values for full, empty, mixed, invalid_out_of_bounds,
and topology_required.
Ledger residuals separately for current-mixed, target-mixed, and topology rows.
```

### F4 HIGH - Physical-volume tolerances are not unit- or scale-invariant

Evidence:

```text
CHK-009 lines 232-236:
tau_q_cpu = 10 * eps64 * max(1, max_C |C|)
tau_q_gpu = c_gpu * eps64 * max(1, max_C |C|)
```

`max(1, max_C |C|)` smuggles a dimensioned unit cell into a physical-volume
tolerance.  If the same geometry is expressed in different physical units, the
acceptance threshold changes for reasons unrelated to discretization error.
For very small cells it can also become a large relative tolerance.

Required repair:

```text
Use a declared physical scale:
  V_ref = max_C |C| or total_volume / n_cells, not max(1, ...)
  tau_q_abs = c_abs eps V_ref
  tau_q_rel = c_rel eps max(V_ref, ||q_target_A||_inf)
  tau_q = max(tau_q_abs, tau_q_rel, tau_floor_from_geometry_condition)

Record units and constants in YAML/test fixtures.
```

### F5 HIGH - PCG tolerance does not control q residual through conditioning

Evidence:

```text
CHK-009 lines 254-256: active PCG/Newton tolerance must not dominate tau_q.
CHK-009 lines 261-263: tau_cg <= min(0.1*tau_q, c_work*tau_surface_diag,
c_round*sqrt(n_active)*eps64).
SP-AO lines 287-294 require rank/conditioning gates.
```

The proposed PCG criterion has no Schur conditioning, rank, operator norm, or
preconditioner quality term.  Exact post-recompute prevents false acceptance,
but the solver can still stop too early and then fail close, or iterate too
long, for reasons that are artifacts of conditioning rather than AO theory.

Required repair:

```text
Add a bound of the form:
  ||delta r_q|| <= ||J W^{-1/2}|| * ||solver_error||
or use exact post-step residual decrease plus adaptive PCG tightening.

Record estimates for rank(S_q), kappa(S_q), row_norm range, and component
blocks.  Treat rank/conditioning failure as a distinct fail-close reason.
```

### F6 HIGH - One refresh/recheck is not a complete active-set policy

Evidence:

```text
CHK-009 line 141: if topology or ownership changed, refresh once and recheck.
CHK-009 line 227: topology epoch unchanged, or one refresh/recheck succeeds.
SP-AO lines 297-298: failure should fail close or enter a declared topology route.
```

One refresh is an implementation shortcut, not a convergence or topology
policy.  A legitimate interface move may require a bounded active-set outer
loop; an invalid one should enter a topology route or fail before solver-family
fallback is considered.

Required repair:

```text
Define active-set epochs:
  fixed_stratum, active_set_expanded, topology_required, invalid_degenerate.

Allow a bounded active-set outer loop with exact residual decrease and no solver
state commit between epochs, or fail close with a specific topology reason.
Do not let explicit solver fallback handle topology changes.
```

### F7 HIGH - Performance gates record counters but do not define pass criteria

Evidence:

```text
CHK-009 lines 148-155 require kernel launch and host-transfer counters.
CHK-009 lines 211-217 permit vectorized xp first, then RawKernel later.
Reference branch p1_cut_geometry.py lines 145-184 uses Python loops over case
ids/tokens, which can produce many kernels even without D2H transfer.
```

No-inner-D2H is necessary but not sufficient.  A vectorized implementation can
pass the D2H contract while launching O(case_count * token_count) kernels over
full-sized masks, losing the requested AO speedup.

Required repair:

```text
Add performance acceptance gates before production:
  active refresh kernel launches <= fixed small constant per refresh,
  no full-grid masks in production active kernels,
  measured work scales with n_active/n_dirty, not n_cells,
  benchmark against dense oracle at N=64/128 with ledgered speed ratio.
```

### F8 MEDIUM - New geometry package and oracle code need project-map governance

Evidence:

```text
CHK-009 lines 56-83 proposes src/twophase/geometry/*.
Current docs/01_PROJECT_MAP.md lines 21-90 list src/twophase packages but no
geometry package.
docs/01_PROJECT_MAP.md lines 272-290 require legacy/reference registration.
```

C1 will create a new production package and retain oracle/reference code.  If
the project map and reference registry are not updated in the same slice, the
worktree will drift from repo governance and later cleanup will be harder.

Required repair:

```text
C1 must update docs/01_PROJECT_MAP.md with src/twophase/geometry ownership.
Dense oracle modules must be registered as reference/oracle-only with forbidden
production call sites.
```

### F9 MEDIUM - Parser strictness is delayed too far relative to import

Evidence:

```text
CHK-009 lines 296-304 start with oracle import and active table.
CHK-009 lines 320-322 defer YAML parser/UX to C8.
Reference branch config_state_space.py defaults many geometric subkeys once
kind is declared, rather than requiring every production contract field.
```

Because parser defaults are part of the fail-close surface, importing the
direct branch parser knowledge late risks building tests around permissive
defaults and only discovering UX incompatibility near runtime activation.

Required repair:

```text
Move a parser contract skeleton and negative tests earlier, before active
projection production code:
  geometric state_space must explicitly declare projection implementation,
  dense_reference mode, gpu_contract.required, and fallback policy.

Runtime construction can still wait until C8.
```

## Recommended CHK-011 Repair Order

```text
1. Repair active constraint set:
   A_q = mixed/current/previous/flux-touched/target-mixed/halo.
2. Repair data model:
   add q_target_A, cell_measure_A, target_state_code_A, flux_touched_A.
3. Repair manifest enum:
   closed classification plus separate migration status.
4. Repair numerical contracts:
   unit-invariant tau_q and conditioning-aware PCG gates.
5. Repair topology policy:
   bounded active-set epoch loop or explicit topology fail-close.
6. Repair GPU performance gates:
   kernel-launch, full-grid-mask, and dense-vs-active benchmark thresholds.
7. Repair governance:
   require project-map/reference registry updates in C1.
8. Move parser negative contract tests earlier.
```

Only after these repairs should implementation proceed beyond oracle-only code.
