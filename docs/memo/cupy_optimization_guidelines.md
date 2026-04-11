# CuPy / GPU Optimization Guidelines for `src/twophase/`

**Status:** ACTIVE — companion to CHK feat/cupy-backend (2026-04-11)
**Target hardware:** NVIDIA RTX 3080 Ti (sm_86, 12 GB, FP64 ≈ 1/32 FP32)
**Policy:** single source tree shared by NumPy and CuPy via `Backend` dispatch. NumPy path must remain bit-exact (PR-5).

---

## 1. Architectural principles

### 1.1 Dispatch, don't fork

All numerical modules must receive the array namespace through the
constructor as `backend: Backend` and use:

```python
self.xp = backend.xp                  # numpy or cupy
sp = backend.scipy.sparse             # scipy.sparse or cupyx.scipy.sparse
la = backend.scipy.linalg             # scipy.linalg or cupyx.scipy.linalg
```

**Never** `import numpy as np` for array construction inside hot-path
classes. Leave `import numpy as np` only for (a) literal scalars (`np.pi`,
`np.sqrt(2)`), (b) dtype tokens, (c) small host-side matrix factorisations
that are numerically sensitive (e.g. 2×2 CCD block LU, see §2.3).

### 1.2 One-liner call-site migration

`Backend.scipy` is a `cached_property` that returns the matching module for
the active device. Migrating a call site is a one-line edit:

```python
# before
import scipy.sparse.linalg as spla
L_pinned = spla.spsolve(L, rhs)
# after
L_pinned = backend.sparse_linalg.spsolve(L, rhs)
```

Any module already holding a `Backend` instance gains sparse / linalg
access without any additional plumbing.

### 1.3 Bit-exact on CPU

The NumPy path must continue to route through **real** `scipy` calls, not
through reimplementations. `Backend.scipy` returns `scipy` verbatim on CPU,
so bit-exactness is automatic; no tolerance changes are required for the
existing 194 NumPy tests.

---

## 2. Hot-path rules

### 2.1 Factorisations live on the device

Large LU / SpLU factors must be built **once** via the backend's linalg
and then **never** transferred. CCD block-circulant LU:

```python
A_dev = self.xp.asarray(A_host)                          # upload once
self._periodic_solvers[ax] = self.backend.linalg.lu_factor(A_dev)
# ... later, in the solve path:
x = self.backend.linalg.lu_solve(self._periodic_solvers[ax], rhs_dev)
```

PPE Kronecker operator: same pattern, but with a **version-keyed cache**
so the sparse matrix is only rebuilt when ρ changes (§2.4).

### 2.2 No per-step host↔device traffic

Per-timestep patterns that move arrays across the PCIe bus kill any GPU
speedup. Before merging any change, grep the diff for:

| Pattern | Allowed? | Notes |
|---|---|---|
| `np.asarray(self.backend.to_host(x))` inside a solve loop | **No** | Must move to an init-time precomputation or an I/O boundary. |
| `scipy.sparse.linalg.spsolve(L, rhs)` | **No** | Route through `backend.sparse_linalg.spsolve`; L and rhs must be device-native. |
| `scipy.linalg.solve_banded(ab, rhs)` | **No** | Route through `backend.solve_banded_batched` — GPU path uses `linalg_backend.thomas_batched`. |
| `arr.get()` inside a solve loop | **No** | Only permitted at checkpoint/VTK/experiment.io boundaries. |
| `float(arr)` / `arr.item()` inside a solve loop | **No** | Forces device sync. Aggregate to an end-of-step flush. |

### 2.3 Host-side numerics is fine when it's bounded

A Python loop over `n=256` 2×2 block LU updates (e.g. `BlockTridiagSolver.factorize`)
runs once per solver construction. Executing that on the host in NumPy is
**preferred**: LAPACK is battle-tested and the 2×2 pivots are numerically
sensitive. After the factorisation, stack the result into `(n, 2, 2)` arrays
and transfer once to the device; subsequent solves run entirely device-native.

### 2.4 Cache matrix operators by version

PPE solvers currently rebuild the sparse Kronecker operator every step.
On GPU this is fatal: CSR assembly on the host plus an H2D transfer
dominates the wall clock. The fix is a **version-keyed cache**:

```python
# __init__
self._L_cache = None
self._rho_version = -1
# solve()
if self._L_cache is None or rho.version != self._rho_version:
    L_host = self._build_sparse_operator(rho_host, drho_host)   # scipy CSR
    L_dev = backend.sparse.csr_matrix(L_host)                   # one H2D
    lu = backend.sparse_linalg.splu(L_dev.tocsc())
    self._L_cache = (L_dev, lu)
    self._rho_version = rho.version
L_dev, lu = self._L_cache
p_dev = lu.solve(rhs_dev)
```

`ScalarField.version: int` is bumped whenever `.data` is written. The key
invariant is that *the scheduler* (step loop) knows when ρ has been
recomputed — the PPE solver does not need to inspect the array.

### 2.5 Batched tridiagonal, not `solve_banded`

`scipy.linalg.solve_banded` has no direct `cupyx` equivalent. The compact
filters in `levelset/compact_filters.py` drive the only hot-path consumer
and the LHS is always strictly diagonally dominant (Helmholtz-κ and
Kim–Lele Padé) → unpivoted Thomas is provably stable. Use the new helper:

```python
x = backend.solve_banded_batched(ab, rhs, axis=ax)  # any axis, any batch shape
```

On CPU this delegates to `scipy.linalg.solve_banded` (bit-exact). On GPU it
delegates to `linalg_backend.thomas_batched`, which issues `2n` vectorised
kernel launches for the full n-point sweep. This is acceptable for
`n ≤ 256`; if profiling later shows it dominates, a PCR/CR upgrade is a
drop-in replacement.

### 2.6 Avoid Python scatter / indexed construction

Build RHS vectors with `xp.roll` + slice assignment, not with Python loops
over `range(N)`. See the periodic CCD rewrite in
[ccd_solver.py:_differentiate_periodic](../../src/twophase/ccd/ccd_solver.py)
for the canonical pattern:

```python
f_im1 = xp.roll(f_unique, 1, axis=0)
f_ip1 = xp.roll(f_unique, -1, axis=0)
rhs[0::2, :] = (_A1 / h) * (f_ip1 - f_im1)
rhs[1::2, :] = (_A2 / (h * h)) * (f_im1 - 2.0 * f_unique + f_ip1)
```

A `for i in range(N):` RHS builder is ~N kernel launches on GPU and
measurably dominates solves at N=128.

---

## 3. Host synchronisation traps

| Source | Symptom | Fix |
|---|---|---|
| `if np.any(mask): ...` in inner loop | device→host sync per step | Accumulate to a device-resident buffer; sync once at `flush()`. |
| `float(arr)` / `arr.item()` for diagnostics | device→host sync per step | Same — aggregate and flush at I/O cadence. |
| `arr.tolist()` in a hot path | device→host sync + Python list alloc | Hoist to `__init__` if the data is static; else keep a device/host mirror. |
| `while err > tol` with `err` derived from `xp.max(residual)` | one sync per iteration | Accept one sync per iteration (unavoidable) but **do not** sync inside the iteration body. |
| `np.savez(..., **arrays)` receiving a `cupy.ndarray` | silent failure / error | Always pass arrays through `backend.to_host()` at the I/O boundary. |

Canonical I/O boundary pattern:

```python
def save(path, fields):
    host_arrays = {k: backend.to_host(v) for k, v in fields.items()}
    np.savez(path, **host_arrays)
```

---

## 4. Testing

### 4.1 Dual-backend smoke tests

Existing NumPy tests stay as-is (they construct `Backend(use_gpu=False)`
directly). New shared tests use the `backend` fixture from
`src/twophase/tests/conftest.py`, which is `"cpu"`-only by default and
parametrises to `["cpu","gpu"]` when pytest is invoked with `--gpu`.

GPU smoke tests must exist for every hot-path module and assert
`rtol ≤ 1e-12` against the CPU reference on diagonally-dominant inputs and
`rtol ≤ 1e-10` on sparse LU (cuDSS pivoting differs from SuperLU in the
last few ULPs).

### 4.2 End-to-end benchmark

`experiment/ch13/exp13_02_rising_bubble` must run to `t_end` on both
backends and assert `max|ψ_gpu − ψ_cpu| < 1e-9`. This is the canonical
fidelity check and also the perf floor sanity check.

---

## 5. Hardware notes (RTX 3080 Ti)

- 12 GB VRAM is enough for 2D `1024²` and 3D `128³` double-precision runs
  with headroom for PPE factors. For `256³` expect to drop to FP32 or to
  swap to matrix-free GMRES+FD-prec (see `project_ccd_ppe_solver_analysis`
  memory).
- FP64 throughput is ≈ 1/32 of FP32 on consumer Ampere, so **memory
  bandwidth dominates**. Prefer fused vectorised ops over FLOP-heavy
  rewrites; do not count on TensorCore FP64 (it does not exist on sm_86).
- cuSPARSE / cuDSS SpLU is faster than scipy SuperLU at `N ≥ 128²` and
  orders of magnitude faster once matrix-caching is in place.
- `cupy.fuse` on small elementwise kernels is not supported on
  higher-order ufuncs; rely on `xp.` vectorisation for now.

---

## 6. Forbidden shortcuts

- No `RawKernel` / `ElementwiseKernel` until profiling proves a bottleneck.
- No hand-written CUDA C++ in `src/twophase/`.
- No multi-GPU / NCCL.
- No FP32 fallback unless explicitly requested (PR-5 is FP64-only).
- No detection-evasion of PR-5 via tolerance slack — the NumPy path is the
  reference and must stay bit-exact.

These are deliberate scope cuts for the first CuPy pass. Revisit in the
next perf-tuning round.

---

## References

- [backend.py](../../src/twophase/backend.py) — dispatch implementation
- [linalg_backend.py](../../src/twophase/linalg_backend.py) — batched Thomas
- [WIKI-L-015](../wiki/code/WIKI-L-015.md) — wiki entry for this guideline
- `project_ccd_ppe_solver_analysis` memory — 3D PPE direction
- `project_architecture_backward_compat_removal` memory — SimulationBuilder as sole path
