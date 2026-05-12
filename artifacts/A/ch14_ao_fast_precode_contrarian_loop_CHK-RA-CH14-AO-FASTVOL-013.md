# CHK-RA-CH14-AO-FASTVOL-013 - AO-Fast pre-code contrarian loop

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Reviewed design:
`artifacts/A/ch14_ao_fast_preimplementation_design_CHK-RA-CH14-AO-FASTVOL-009.md`
with repairs CHK-011 and CHK-012.

## Scope

User direction: before coding, repeat adversarial review and repair until no
major findings remain.

This artifact reviews specification/design only.  No solver source is changed,
no chapter-14 YAML is activated, no main merge is performed, and the direct
dense-AO branch remains available until its import manifest is complete.

## Severity Rule

```text
P0: would violate AO fidelity, fail-close, or production correctness.
P1: would likely cause hidden O(|C_h|), host-sync, dense fallback, or
    non-terminating heavy work in ordinary runtime.
P2: implementation detail that can be resolved in the named commit slice.
Stop condition: no unresolved P0/P1 findings.
```

## Round 1 Findings And Repairs

### R1-F1 - Production condition gate was diagnostic-only

Severity: P1.

Risk: the YAML examples used `condition_gate: diagnostic`.  That could allow an
ill-conditioned active Schur step to continue in production after the design
had already declared conditioning a fail-close reason.

Repair: production YAML examples now use `condition_gate: fail_close`, and
parser rejection lists include diagnostic-only condition gates for production
geometric-cell-fraction AO.

### R1-F2 - PCG tolerance mixed target and floor

Severity: P1.

Risk: CHK-009/CHK-011 put `c_round sqrt(n_active) eps Q_ref` inside the
`min(...)` tolerance.  That can request an unattainable tolerance and waste
iterations, or make failure look like a solver issue rather than a
conditioning/roundoff issue.

Repair: the design now separates `tau_cg_target` from `tau_cg_floor`.  If the
floor exceeds the target, the step is conditioning/roundoff limited and fails
closed or follows only a declared solver-chain transition.  Exact residual
recomputation remains the commit gate.

### R1-F3 - Compact support compaction could hide a full-grid mask

Severity: P1.

Risk: a GPU-looking implementation could build a full-grid boolean support mask
and call `where/nonzero` each timestep.  That is still full-grid discovery.

Repair: support compaction is restricted to compact candidate streams emitted
by transport, prior active rows, dirty rows, and compact adjacency.  Full-grid
`where/nonzero` is oracle/debug-only.

### R1-F4 - flux_touched could mean bulk velocity support

Severity: P1.

Risk: if `flux_touched_cells` includes every nonzero velocity face or every
bulk full-liquid to full-liquid exchange, `A_q` can approach the whole moving
phase region.

Repair: `flux_touched_cells` is now defined as state-changing transported
phase-volume support: cells whose transport can change empty/full/mixed target
state or active-band ownership.  It is not all nonzero velocity faces.

### R1-F5 - Active/support capacity was implicit

Severity: P1.

Risk: unknown compact stream sizes can lead to Python list appends, device-host
bounces, or silent dense buffer allocation.

Repair: production must declare `max_active_ratio`,
`max_support_stream_ratio`, and `max_epoch_growth_ratio`.  Active/support
buffers are preallocated on device.  Capacity overrun fails closed unless an
explicit diagnostic degenerate-exact mode is declared and ledgered as not-fast.

## Round 2 Re-Review

The repaired design was re-read against the same failure modes:

```text
full-grid support discovery,
bulk flux support explosion,
dense Schur/SVD/eigen diagnostics,
condition diagnostic-only production continuation,
PCG below roundoff floor,
implicit dense fallback,
implicit DC-to-PCG fallback,
host-side support allocation,
runtime dense oracle comparison,
chapter-14 YAML activation before gates.
```

Result: no unresolved P0/P1 findings remain.

Residual P2 items are intentionally owned by the validation ladder:

```text
C1 declares parser negative tests and oracle-only dense imports,
C3 proves preallocated GPU active storage and no full-grid support compaction,
C4 proves compact state-changing flux/target support,
C6 proves cheap rank/condition estimates,
C7 proves PCG target/floor behavior and fail-close,
C8 proves YAML/UX rejection of diagnostic-only condition gates.
```

These P2 items are not blockers to the first coding ticket because they are the
named tests and implementation obligations of the commit slices.  They must be
completed before runtime YAML activation.

## Stop Condition

Major findings are zero after Round 2.  Code development may start at C1 only:
dense oracle plus closed import manifest, parser negative skeleton, and project
map governance.  Runtime activation, chapter-14 YAMLs, capillary adapters,
dense fallback, full-grid support discovery, and CPU-first production loops
remain out of scope.
