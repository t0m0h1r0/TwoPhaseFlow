# CHK-RA-CH14-AO-FASTVOL-012 - AO-Fast complexity audit

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Audited design: `artifacts/A/ch14_ao_fast_preimplementation_design_CHK-RA-CH14-AO-FASTVOL-009.md`
Prior repair: `artifacts/A/ch14_ao_fast_design_repair_CHK-RA-CH14-AO-FASTVOL-011.md`

## Scope

User direction: check whether the repaired AO-Fast design has become
computationally too heavy.

This audit checks the design/specification only.  No solver source is changed,
no chapter-14 YAML is activated, no main merge is performed, and the direct
dense-AO branch is not deleted.

## Verdict

The repaired design is acceptable only with additional cost guardrails.  The
architecture remains an AO speedup route, but three phrases in CHK-011 could
have been implemented too expensively:

```text
target_mixed_cells,
flux_touched_cells,
rank/conditioning estimates.
```

These are now constrained in CHK-009 and SP-AO:

```text
target/flux support must come from compact support streams,
ordinary runtime must not scan all cells to discover q support,
rank/conditioning diagnostics must be cheap active/Krylov estimates,
dense oracle/benchmark work must stay outside production timesteps.
```

The follow-up contrarian pass also constrains four hidden cost traps:

```text
support compaction must not use full-grid where/nonzero masks,
flux support means state-changing transported phase-volume support,
active/support buffers need declared device capacity and overrun behavior,
PCG must not iterate below its estimated attainable roundoff floor.
```

## Cost Budget

Ordinary AO-Fast runtime target:

```text
O(|A_q| + |dirty| + k * matvec(|A_q|)).
```

Allowed full-grid work:

```text
initialization,
restart validation,
explicit debug diagnostics,
dense-oracle tests,
metric-epoch rebuild when the grid truly changes,
declared degenerate exact step.
```

Forbidden ordinary-runtime work:

```text
scan every cell to find target_mixed_cells,
scan every face with nonzero velocity to define flux_touched_cells,
materialize full-grid masks in production active kernels,
assemble dense/full-grid Schur matrices,
run dense SVD/eigendecomposition for conditioning,
run dense oracle comparison inside a production timestep.
call where/nonzero over a full-grid support mask,
silently allocate active/support buffers through host lists.
```

## Audit Findings

### C1 - A_q can become full-grid if target support is discovered naively

Risk: `target_mixed_cells where 0<q_target_C<|C|` is correct mathematically,
but a naive implementation would inspect every `q_target_C` each timestep.

Repair: target support must be emitted by swept-volume transport as a compact
target-state transition stream.  Full-grid q scans are initialization,
restart/debug, oracle, or declared-degenerate work only.

### C2 - flux_touched must mean phase-flux support, not velocity support

Risk: in a moving flow, many velocity faces are nonzero.  If `flux_touched` is
defined from nonzero velocity faces, `A_q` becomes nearly full-grid.

Repair: `flux_touched_cells` means compact cells touched by nonzero transported
phase volume or target-state change, emitted by the geometric swept-volume
transport certificate.  It is not all faces with nonzero velocity.

### C3 - Roundoff support must not explode A_q

Risk: tiny roundoff values near `0` or `|C|` can classify large regions as
target-mixed.

Repair: support classification uses a declared `tau_support <= tau_q`.
Near-empty/full rows can be classified as empty/full for support construction,
but `q_target_A` is not clipped and exact residual acceptance remains in
physical q units.

### C4 - Conditioning gates must be cheap

Risk: rank/conditioning ownership can invite dense Schur assembly, SVD, or
eigenvalue solves.

Repair: rank and condition estimates must come from active-row row norms,
component blocks, Krylov residual history, or Ritz/Lanczos estimates already
available from PCG.  Dense SVD/eigendecomposition is oracle/debug-only.

### C5 - Benchmark gates are validation, not runtime

Risk: dense-vs-active speed checks at N=64/N=128 could be misread as runtime
work.

Repair: dense oracle and benchmark comparisons are validation gates outside
production timesteps.  Production ledgers record counters; benchmark jobs
interpret them.

### C6 - Support compaction can hide a full-grid mask

Risk: a superficially GPU implementation could build a full-grid boolean mask
and call `where/nonzero` every step.  That is still O(|C_h|) support discovery.

Repair: production support compaction runs over compact candidate streams
emitted by transport, previous active rows, dirty rows, and adjacency.  Full-grid
`where/nonzero` is oracle/debug-only.

### C7 - flux_touched can include irrelevant bulk phase flux

Risk: geometric swept-volume transport can move liquid through full cells.  If
every full-liquid to full-liquid exchange becomes `flux_touched`, the active
set can approach the whole liquid region.

Repair: `flux_touched_cells` means state-changing transported phase-volume
support: cells whose transport can change empty/full/mixed target state or
active-band ownership.  Bulk full/full exchanges are not active constraints
unless they create a target-state transition.

### C8 - Active capacity can silently become dynamic host allocation

Risk: compact streams with unknown size can tempt implementations to append to
Python lists, resize arrays, or bounce through host memory.

Repair: production declares active/support capacities and growth ratios.
Capacity overrun is fail-close or an explicitly ledgered diagnostic degenerate
step.  It is not an implicit dense fallback.

### C9 - PCG tolerance can be below the attainable floor

Risk: using roundoff as another upper bound in `min(...)` can request an
unattainable algebraic tolerance and waste iterations.

Repair: separate `tau_cg_target` from `tau_cg_floor`.  If the floor exceeds the
target, record conditioning/roundoff limited and fail closed or enter a
declared solver-chain transition.

### C10 - Production condition gates must not be diagnostic-only

Risk: a YAML example with `condition_gate: diagnostic` can encourage continuing
after a known ill-conditioned active Schur solve.

Repair: production geometric-cell-fraction AO uses `condition_gate:
fail_close`.  Diagnostic-only conditioning is allowed only for oracle/debug
runs that cannot commit production state.

## Implementation Acceptance Rules

Before production AO-Fast code is accepted:

```text
1. A_q construction tests must fail if ordinary runtime scans all cells.
2. Transport must expose compact flux/target support streams.
3. Host-transfer tests must also catch full-grid mask materialization.
4. Conditioning tests must prove estimates are active/Krylov-only.
5. Benchmarks must show active work scales with |A_q| and |dirty|, not |C_h|.
6. Degenerate full-grid steps must be explicit and ledgered as not-fast.
7. Support compaction tests must fail on full-grid where/nonzero masks.
8. Capacity-overrun tests must fail closed unless diagnostic degenerate mode is
   explicitly declared.
9. PCG tests must distinguish target tolerance from roundoff floor.
10. Production parser tests must reject diagnostic-only condition gates.
```

## Conclusion

The design is not inherently too heavy after this audit, but only because the
new constraints make compact support and cheap diagnostics mandatory.  Without
these constraints, CHK-011 would likely regress to `O(|C_h|)` discovery cost or
dense linear algebra diagnostics.
