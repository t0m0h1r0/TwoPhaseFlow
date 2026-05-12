# CHK-RA-CH14-AO-FASTVOL-007 - AO-Fast GPU import gate

Date: 2026-05-12
Branch: `codex/ra-ch14-ao-fast-volume-20260511`
Reference branch: `codex/ra-ch14-osc-sharp-volume-20260510`
Worktree: `.claude/worktrees/codex-ra-ch14-ao-fast-volume-20260511`

## Scope

User direction: when importing work from the direct-AO branch, enforce GPU
optimization thoroughly.

This checkpoint strengthens the CHK-006 reuse policy.  It is a
design/specification checkpoint.  No solver source is changed and no production
YAML is activated.

## Decision

Every imported AO component must be classified before it enters production:

```text
oracle_only       exact dense reference or test helper; never called at runtime,
gpu_production    device-resident active implementation allowed in production,
reject            CPU/host-centric implementation not imported.
```

The reference branch may provide formulas and tests.  Production AO-Fast may
not inherit its full-grid arrays, dense line-search loop, scalar host residual
checks, or Python cell loops as control flow.

## GPU Admission Contract

An AO component may be marked `gpu_production` only if it satisfies all gates:

```text
G1. backend-native arrays only: no NumPy/CPU arrays in the production path.
G2. struct-of-arrays active storage: compact contiguous arrays for cell ids,
    node ids, case codes, edge lambdas, q/s/J/dS rows, and component labels.
G3. no inner-loop D2H: no .get(), asnumpy, float(...), bool(...), Python list
    materialization, or scalar transfer inside CG/Newton/DC/line-search loops.
G4. device reductions: residual norms, alpha candidates, line-search masks, and
    acceptance predicates are computed as device reductions; host sees only
    final ledger scalars after an outer step.
G5. fused active kernels: Q/S/J/dS refresh is fused over active rows and dirty
    rows; full-grid cut geometry per candidate is forbidden.
G6. metric reuse: grid coordinates, cell measures, and face metrics come from a
    device-resident fingerprinted cache, not repeated per-candidate conversion.
G7. preallocated work buffers: Krylov vectors, active residuals, and candidate
    geometry arrays are reused across iterations.
G8. explicit degeneration ledger: if dirty rows expand to full-grid work, the
    step is recorded as degenerate and not reported as active-band speedup.
G9. CPU path parity: CPU remains a bit-exact or tolerance-declared reference
    backend, but it must not dictate production GPU control structure.
```

Failure of any gate keeps the code in `oracle_only` or `reject`.  It is not a
reason to fall back to dense AO.

## Import Checklist

Before importing a symbol from `codex/ra-ch14-osc-sharp-volume-20260510`, record:

```text
symbol,
source file,
classification,
GPU gate status G1--G9,
allowed call sites,
inner-host-transfer audit result,
active-vs-dense equality tests,
ledger fields emitted.
```

Examples:

```text
P1 polygon/crossing formulas:
  classification: oracle_formula -> rewritten into gpu_production kernels.

cut_geometry_2d dense output:
  classification: oracle_only.

project_cell_volume_compatibility_2d:
  classification: oracle_only; production replacement is active_cached.

MetricCellComplex cache:
  classification: gpu_production only after cache arrays remain device-resident
  and invalidation does not force per-candidate host conversion.
```

## YAML And Runtime Gate

Production AO YAML must request the GPU contract explicitly:

```yaml
interface:
  state_space:
    compatibility:
      projection:
        implementation: active_cached
        dense_reference: test_only
        gpu_contract:
          required: true
          active_storage: struct_of_arrays
          inner_host_transfers: forbidden
          dense_runtime_fallback: forbidden
          record_kernel_counters: true
```

If `gpu_contract.required=true` and any production gate cannot be certified,
the parser/runtime must fail closed before chapter-14 activation.  It must not
silently run dense direct AO as a rescue path.

## Validation Contract

The first production implementation must add:

```text
no-inner-D2H tests for CG/Newton/DC/line search,
active-vs-dense Q/S/J/dS equality tests on CPU and CUDA,
metric-cache reuse/invalidation tests on CUDA,
dirty-halo refresh tests that prove O(|dirty| + k|A|) accounting,
ledger tests for |A|, |dirty|, refreshed rows, kernel launches, and host copies.
```

Remote GPU validation is mandatory before any chapter-14 AO YAML activation.

## SOLID-X

Design/specification artifact only.  No solver source, experiment result,
tested implementation deletion, FD/WENO/PPE fallback, damping/CFL workaround,
smoothing, curvature cap, benchmark branch, blanket projection,
QP-as-physics path, implicit dense fallback, implicit PCG fallback,
CPU-first AO production path, or hidden DCCD/UCCD damper introduced.
