# CHK-RA-CH14-HODGE-GPU-OPT-001 — Hodge Projection GPU Optimization

Date: 2026-05-07  
Branch: `codex/ra-ch14-capillary-virtual-work-20260506`  
Scope: updated trace/Riesz weighted Hodge projection code.

## Problem

The corrected Hodge projection solve was mathematically right after
CHK-RA-CH14-HODGE-SOLVE-FIX-001, but the implementation still flattened face
cochains and evaluated norms through host NumPy in the projection path.  On a
GPU run this would either force device-host synchronization or mix CuPy sparse
operators with NumPy vectors.

The theoretical operator is unchanged:

```text
D_f M_f^{-1} D_f^T p = D_f c,
Pi_R c = M_f^{-1} D_f^T p,
h = c - Pi_R c.
```

Optimization must therefore preserve the same `D_f`, `M_f`, gauge-fixed normal
equation, and residual tests; it must not introduce any alternate force model.

## Changes

- `weighted_hodge_decomposition` now flattens face components on the active
  backend and computes weighted norms / divergence residuals through `xp`.
- The analytic FCCD divergence matrix cache is keyed by backend.  CPU keeps a
  SciPy CSR matrix; GPU receives a `cupyx.scipy.sparse.csr_matrix`.
- Sparse normal assembly uses the backend sparse module, so
  `D_f M_f^{-1} D_f^T` remains sparse on GPU.
- The GPU sparse gauge solve uses `cupyx.scipy.sparse.linalg.spsolve` and
  fails closed if CuPy cannot solve it; it does not silently fall back to a host
  solve.
- `component_reaction_hodge_gate` now computes its final residual divergence on
  the same backend instead of mixing a backend sparse `D_f` with NumPy flattening.
- Added a GPU regression test that manufactures a pure pressure-range cochain
  on CPU, transfers it to GPU, and checks that the GPU projection matches the
  CPU projection to `1e-10`.

The remaining host boundary is the construction of the sparse FCCD matrix
graph from grid/topology metadata before transfer to CSR.  That is setup/cache
materialization, not a per-projection dense cochain transfer.

## Validation

- `git diff --check`: PASS.
- Remote full pytest via
  `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock make test PYTEST_ARGS='twophase/tests/test_closed_interface_riesz.py twophase/tests/test_closed_interface_trace_riesz.py -q'`:
  PASS, `610 passed, 33 skipped in 41.66s`.
- Remote GPU targeted pytest via
  `SSH_AUTH_SOCK=/private/tmp/codex-ssh-agent-test.sock ssh python '/root/TwoPhaseFlow/.venv/bin/python -m pytest /root/TwoPhaseFlow/src/twophase/tests/test_closed_interface_riesz.py::test_weighted_hodge_projection_gpu_matches_cpu --gpu -q'`:
  PASS, `1 passed in 0.44s`.

## SOLID-X

No SOLID violation found.  The change is confined to the Hodge projection
implementation and its tests.  No tested implementation was deleted, and no
FD/WENO/PPE fallback, damping/CFL workaround, curvature cap, smoothing,
benchmark branch, blanket `c -> Pi_R c`, or QP-as-physics route was introduced.
