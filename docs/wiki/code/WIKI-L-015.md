---
id: WIKI-L-015
title: "CuPy / GPU Backend Unification: xp Dispatch, SciPy Shim, Batched Thomas"
status: ACTIVE
created: 2026-04-11
updated: 2026-04-11
depends_on: [WIKI-L-001, WIKI-L-008, WIKI-T-015]
---

# CuPy / GPU Backend Unification

## Motivation

The library already carried a partial `Backend(use_gpu=False|True)` scaffold
with an `xp` attribute, but every hot-path module still issued hard
`import numpy as np` and every PPE / compact-filter solve bounced through
CPU scipy even on a `use_gpu=True` run. Making CuPy a first-class target
for the §13 benchmark suite on an RTX 3080 Ti required closing that gap
without forking the codebase.

## Architecture

```
SimulationBuilder(cfg.use_gpu)
      │
      ▼
Backend (backend.py)
  ├── xp            : numpy | cupy
  ├── scipy         : scipy | cupyx.scipy             (cached_property)
  ├── sparse        : scipy.sparse | cupyx.scipy.sparse
  ├── sparse_linalg : scipy.sparse.linalg | cupyx.scipy.sparse.linalg
  ├── linalg        : scipy.linalg | cupyx.scipy.linalg
  ├── to_host / to_device / asnumpy / is_gpu
  └── solve_banded_batched
         ├── CPU: scipy.linalg.solve_banded (bit-exact)
         └── GPU: linalg_backend.thomas_batched
```

### Key files

| File | Role |
|------|------|
| `src/twophase/backend.py` | `Backend` class — lazy scipy / cupyx.scipy dispatch |
| `src/twophase/linalg_backend.py` | `thomas_batched(xp, ab, rhs, axis)` — device-native batched tridiagonal |
| `src/twophase/ccd/ccd_solver.py` | Periodic CCD: LU now device-resident; RHS built via `xp.roll` |
| `src/twophase/ccd/block_tridiag.py` | Factorisation stacked to `(n,2,2)`; single H→D after factorize |
| `src/twophase/pressure/ccd_ppe_base.py` | `_spsolve` helper: host CSR → device CSR → `spsolve` → host |
| `src/twophase/pressure/ppe_solver_ccd_lu.py` | Uses `_spsolve`; subclass trivially backend-agnostic |
| `src/twophase/levelset/compact_filters.py` | `solve_banded` → `backend.solve_banded_batched` |

## Call-site migration rules

1. **One-line substitution.** Every `import scipy.sparse.linalg as spla;
   spla.spsolve(L, rhs)` becomes `backend.sparse_linalg.spsolve(L, rhs)`.
   No DI container is introduced; the existing `Backend` instance is the
   dispatch point.
2. **Factorisations live on device.** `lu_factor` / `splu` / CCD block LU
   must be built once (via `backend.linalg` or `backend.sparse_linalg`)
   on a device-native array. Per-step transfer of LU factors is a GPU
   anti-pattern — see WIKI-T-015 §Cost analysis.
3. **Host sync is forbidden inside solve loops.** `float(arr)`, `arr.item()`,
   `if np.any(...)`, `while err > tol` with device-side `err` — all must
   be aggregated to an I/O boundary via lazy flush. Accept one sync per
   *outer* iteration (time step), never per inner iteration.
4. **Bit-exact NumPy path (PR-5).** `Backend.scipy` returns `scipy` verbatim
   on CPU, so the existing 194 NumPy tests pass without any tolerance
   change. GPU smoke tests use `rtol ≤ 1e-12` for elementwise pipelines
   and `rtol ≤ 1e-10` for sparse LU (cuDSS ULP drift).

## Batched Thomas solver

`scipy.linalg.solve_banded` has no direct `cupyx` counterpart. The only
hot-path consumer is `levelset.compact_filters` whose LHS is always
strictly diagonally dominant (Helmholtz-κ and Kim/Lele Padé filters), so
unpivoted Thomas is provably stable and sufficient.

`thomas_batched(xp, ab, rhs, axis)`:

- Moves the target axis to position 0, flattens the batch → `(n, B)`.
- Runs a classical Thomas forward sweep + back substitution as a Python
  loop of length `n`, vectorised across the batch dimension.
- Issues `2n` kernel launches per call — acceptable for `n ≤ 256` typical
  of compact-filter passes; PCR/CR is a drop-in upgrade if profiling later
  shows this as a bottleneck.

Verified against `scipy.linalg.solve_banded` to `rtol ≤ 1e-12` across
`n ∈ {8, 32, 128, 256}`, batch `∈ {1, 10³, 5·10⁴}`, axis `∈ {0,1,2}`
in `src/twophase/tests/test_linalg_backend.py`.

## Non-goals (first pass)

- No `RawKernel` / `ElementwiseKernel` / custom CUDA — revisit after
  profiling.
- No PCR/CR batched tridiagonal — classical Thomas is stable for the
  current consumers.
- No FP32 fallback, no multi-GPU, no kernel fusion on WENO.
- PPE operator matrix caching by `ScalarField.version` is scheduled as a
  follow-up phase within the same refactor and is *the* bottleneck to
  break before GPU wall-clock wins become visible.

## A3 traceability

- Equation: WIKI-T-015 §DC-PPE solve (factorisation cost analysis)
- Discretisation: WIKI-T-012 §CCD Kronecker assembly
- Code: `backend.py`, `linalg_backend.py`, `ccd/ccd_solver.py`,
  `ccd/block_tridiag.py`, `pressure/ccd_ppe_base.py`,
  `pressure/ppe_solver_ccd_lu.py`, `levelset/compact_filters.py`
- Memo: `docs/memo/cupy_optimization_guidelines.md`

## Related entries

- [[WIKI-L-001]] Algorithm overview — parent of all L-Domain entries
- [[WIKI-L-008]] SimulationBuilder — the construction path that owns `Backend`
- [[WIKI-T-015]] DC-PPE convergence theory — motivates the caching rule
- [[WIKI-T-019]] Filter design — driver of the compact-filter consumers of
  `solve_banded_batched`
