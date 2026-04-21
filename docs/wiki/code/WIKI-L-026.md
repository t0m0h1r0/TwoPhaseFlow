---
ref_id: WIKI-L-026
title: "GPU Matrix-Free FVM PPE Roadmap: Variable-Batched PCR and Device-Resident Krylov"
domain: code
status: SPEC
superseded_by: null
sources:
  - path: docs/wiki/theory/WIKI-T-060.md
    description: Theory entry for GPU-native FVM projection
  - path: src/twophase/ppe/fvm_spsolve.py
    description: Legacy FVM PPE solver to preserve as fallback
  - path: src/twophase/ppe/ppe_builder.py
    description: Existing face-local coefficient formulas and geometry cache
  - path: src/twophase/linalg_backend.py
    description: Current PCR special case for common tridiagonal coefficients
  - path: src/twophase/backend.py
    description: Backend dispatch surface for batched solvers
depends_on:
  - "[[WIKI-T-060]]: GPU-Native FVM Projection"
  - "[[WIKI-L-015]]: CuPy / GPU Backend Unification"
  - "[[WIKI-L-022]]: G^adj FVM-Consistent Pressure Gradient"
consumers:
  - domain: experiment
    description: Future GPU speed/accuracy comparison against `fvm_spsolve`
  - domain: cross-domain
    description: WIKI-X-018 performance-axis companion
tags: [ppe, fvm, gpu, matrix_free, pcr, krylov, spec, additive_change]
compiled_by: Codex GPT-5
compiled_at: "2026-04-21"
---

# GPU Matrix-Free FVM PPE Roadmap

## Status

**SPEC + status.** This entry defines the implementation plan for the GPU-native FVM PPE derived in [WIKI-T-060](../theory/WIKI-T-060.md). CHK-162 lands the initial additive implementation in `src/twophase/linalg_backend.py`, `src/twophase/backend.py`, `src/twophase/ppe/fvm_matrixfree.py`, `src/twophase/ppe/factory.py`, `src/twophase/config.py`, and the associated tests. The implementation remains additive-only: the legacy `PPESolverFVMSpsolve` stays available per C2. Remaining work is GPU parity/performance benchmarking and a no-host-sync gate for the hot solve path.

## Phase 1 — Variable-batched tridiagonal primitive

### Target

- `src/twophase/linalg_backend.py`
- `src/twophase/backend.py`

### New primitive

Add a new helper whose diagonals vary across batch lines:

```python
def tridiag_variable_batched(xp, lower, diag, upper, rhs, axis):
    """Solve independent tridiagonal systems with per-line coefficients.

    lower, diag, upper, rhs: same shape after moveaxis(axis, 0) -> (n, *batch)
    """
```

The current `_pcr_solve_batched` already implements the common-matrix special case. The generalisation is mechanical:

- keep the same PCR elimination stages,
- replace broadcast diagonals of shape `(n, 1)` with full diagonals of shape `(n, B)`,
- update `a`, `d`, `c`, and `b` pointwise over both line index and batch index.

### Required backend surface

Expose the primitive from `Backend` with a wrapper analogous to `solve_banded_batched`. Do **not** overload the existing helper: the current signature implies one matrix shared across all batches.

## Phase 2 — New additive PPE solver

### Target

- new `src/twophase/ppe/fvm_matrixfree.py`

### Proposed class

```python
class PPESolverFVMMatrixFree(IPPESolver):
    def apply(self, p, rho):
        """Matrix-free L_FVM(rho) p via face-local operators."""

    def build_line_coeffs(self, rho, axis):
        """Return lower/main/upper arrays for all axis lines on device."""

    def solve(self, rhs, rho, dt=0.0, p_init=None):
        """FGMRES + variable-batched line preconditioner."""
```

### Design rules

- `apply(p, rho)` must be algebraically identical to the current CSR operator built by `PPEBuilder.build_values`.
- Geometry arrays (`d_face`, `dv`) are uploaded once and cached.
- $\rho$-dependent face coefficients and line diagonals are formed in `backend.xp`.
- The solve loop must not call `.get()`, `.item()`, `float(device_array)`, or `to_host()`.

## Phase 3 — Preconditioner shape

The line solve is a preconditioner, not a standalone solver. Recommended default:

```python
solver = FGMRES(
    A=lambda p: self.apply(p, rho),
    M=lambda r: self.apply_line_preconditioner(r, rho),
)
```

Acceptable preconditioner families:

- additive line-Jacobi: sum of axis line solves,
- multiplicative x→y sweep,
- symmetric forward/backward variant.

The final accepted solution is always for the full matrix-free operator `A`; no split operator is ever treated as the solved PDE.

## Phase 4 — Config and factory wiring

### Target

- `src/twophase/config.py`
- `src/twophase/ppe/factory.py`

### Additive registration

- add `ppe_solver_type="fvm_matrixfree"` to `SolverConfig` validation,
- register the new solver in `ppe.factory`,
- keep all defaults unchanged.

The legacy `fvm_spsolve` path remains available as a fallback / verification reference.

## Verification battery

1. `test_fvm_matrixfree_apply_matches_csr`
   - matrix-free `apply()` matches CSR matvec from `PPEBuilder.build_values`.

2. `test_variable_pcr_matches_cpu_reference`
   - random diagonally dominant variable-coefficient lines match CPU reference solve.

3. `test_fvm_matrixfree_gpu_matches_cpu`
   - full PPE solve parity on a small 2D variable-density case.

4. `test_fvm_matrixfree_no_hotloop_host_sync`
   - grep gate for `.get()`, `.item()`, `float(`, `to_host(` in the new solve path.

5. Experiment gate
   - remote GPU comparison vs `fvm_spsolve` on a representative ch12 or ch13 configuration.

## Rollback procedure

Because the solver is additive, rollback is one-symbol: switch `ppe_solver_type` back to `fvm_spsolve` (or current production default). No data format changes are required.

## Scope limits

- This roadmap targets the FVM PPE / projection path only.
- CPU-serial modules outside this path remain out of scope.
- Performance tuning after the first implementation should start with the variable-batched PCR kernel, not with premature solver-family changes.
