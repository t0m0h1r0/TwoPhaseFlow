---
id: WIKI-L-017
title: "GPU Experiment Patterns: sparse_solve_2d, to_float, Grid.meshgrid() N+1 Contract"
status: ACTIVE
created: 2026-04-15
depends_on: [WIKI-L-015]
sources:
  - path: "src/twophase/tools/experiment/gpu.py"
    description: "GPU-friendly helpers for experiment scripts"
  - commit: "2f2d21c"
    description: "ch11: optimize PPE experiments for GPU backend"
  - commit: "b51bc6d"
    description: "fix: field viz dimension mismatches in exp12_10 and exp12_12"
---

# GPU Experiment Patterns

[[WIKI-L-015]] covers the production-side GPU unification (`Backend`, `xp`
dispatch, SciPy shim). This entry documents the **experiment-side** patterns
in `src/twophase/tools/experiment/gpu.py` (commit `2f2d21c`).

Experiment scripts differ from library code: they use `scipy.sparse` for
verification matrices, manage their own RHS transfers, and produce numpy
arrays for visualization. The `gpu.py` module codifies 5 patterns that
prevent CPU/GPU interop bugs.

---

## Pattern 1 — Sparse Assembly on CPU, Then Transfer

CuPy cannot construct sparse matrices from mixed host/device COO data.

**Rule:** Always build the sparse matrix in `scipy.sparse`, then convert:

```python
mat = sp_cpu.csr_matrix((vals, (rows, cols)), shape=shape)
return backend.sparse.csr_matrix(mat)
```

This pattern is used by `fd_laplacian_dirichlet_2d`, `fd_laplacian_neumann_2d`,
`fd_varrho_dirichlet_2d`, and `pin_gauge`.

**Discovery:** ch11 Group D re-run — `exp11_12b` (split PPE + CCD) failed
because CuPy `csr_matrix` rejected mixed numpy/Python lists.

---

## Pattern 2 — `sparse_solve_2d`: RHS Transfer Before Solve

```python
def sparse_solve_2d(backend, matrix, rhs, shape=None):
    xp = backend.xp
    rhs_dev = xp.asarray(rhs)          # transfer once at entry
    sol = backend.sparse_linalg.spsolve(matrix, rhs_dev.ravel())
    return sol.reshape(out_shape)
```

Calling code can pass a numpy array; the transfer happens once via
`xp.asarray(rhs)`. This avoids per-iteration host-to-device round-trips in
defect-correction loops.

---

## Pattern 3 — `to_float(backend, value)`: Safe Scalar Reduction

```python
def to_float(backend, value) -> float:
    return float(np.asarray(backend.to_host(value)))
```

Never call `float(cupy_arr)` directly — it triggers a host sync. Route
through `backend.to_host()` first. Common wrappers:

- `max_abs_error(backend, a, b)` — `max(abs(a-b))` on device
- `l2_norm(backend, a)` — Euclidean norm on device

---

## Pattern 4 — `_SPARSE_SOLVE_WARNED`: Single-Warning Fallback

When CuPy sparse solve is unavailable (older CUDA images, missing
`cupyx.scipy.sparse.linalg`), `sparse_solve_2d` catches the exception and
falls back to CPU SciPy transparently.

```python
_SPARSE_SOLVE_WARNED = False

def _warn_sparse_cpu_fallback(exc):
    global _SPARSE_SOLVE_WARNED
    if _SPARSE_SOLVE_WARNED:
        return
    _SPARSE_SOLVE_WARNED = True
    print("WARNING: GPU sparse solve unavailable; falling back to SciPy ...")
```

The module-level flag ensures the warning prints **once per session**, not
once per solve call. Use this "single-warning pattern" for any GPU capability
that may be missing on some remote images.

---

## Pattern 5 — `Grid.meshgrid()` Returns N+1 Points (Cell Corners)

`Grid.meshgrid()` returns arrays of shape `(N+1, N+1)` — cell corner
coordinates, not cell centers.

**Bug:** Experiment scripts that construct `x1d = np.linspace(0, L, N)`
produce `N` points, causing dimension mismatches with `Grid.meshgrid()`
output when passed to `field_with_contour` or `streamlines_colored`.

**Fix:** Always use `N+1` points:

```python
x1d = np.linspace(0, L, N + 1)   # correct: matches Grid.meshgrid()
```

Also: `field_with_contour` and `streamlines_colored` transpose internally,
so do not apply `.T` before calling them (double-transpose bug in exp12_12,
fixed in commit `b51bc6d`).

---

## Cross-References

- [[WIKI-L-015]] — Production-side GPU patterns (Backend, xp dispatch)
- [[WIKI-M-009]] — Re-run methodology where these patterns were discovered
- [[WIKI-E-021]] — Ch12 re-run where the N+1 bug was encountered
