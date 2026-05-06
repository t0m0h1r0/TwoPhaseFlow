# CHK-RA-SRC-GPU-OPT-003 — FD PPE GPU-First Correction

## Scope

Follow-up to CHK-RA-SRC-GPU-OPT-002 after the user pointed out that FD is part
of the PPE/DC path and should be implemented GPU-first rather than merely
rejected on GPU.

## Finding — MAJOR Fixed

`FDPPEMatrix` was classified as a host-only legacy builder and rejected on GPU.
That was too conservative. The production `PPESolverFDDirect` path already uses
`PPEBuilder` and backend sparse factorization, but the exported FD PPE matrix
builder still represents the same low-order PPE/DC operator and should preserve
the GPU-first contract when a GPU backend is supplied.

## Fix

- Removed the GPU fail-closed guard from `FDPPEMatrix`.
- Replaced host `to_host` density/CCD-gradient materialization with backend
  arrays throughout `_density_fields()`.
- Replaced node-by-node host COO assembly with vectorized `xp` assembly for
  the 2-D uniform FD PPE operator.
- `build()` and `build_raw()` now return backend sparse matrices: SciPy on CPU,
  CuPyX sparse on GPU.
- `factorize()` now factors the backend CSC matrix directly.
- `build_helmholtz_filter()` no longer builds a host SciPy LIL matrix; it
  constructs the pinned Helmholtz matrix through backend COO/CSC arrays.
- The previous host-loop implementation is retained as
  `_assemble_host_legacy()` under C2 for regression audits.

## Clarification

FD is not the PPE RHS itself. It is the low-order PPE/DC operator used to solve
the PPE RHS or defect residual in the ch12+ integration policy. That makes the
GPU residency of FD PPE builders and base solvers part of the PPE GPU contract.

## Validation

- `test_fd_ppe_matrix.py` PASS:
  - vectorized backend assembly matches the legacy host loop exactly on CPU;
  - pinned PPE factorization and Helmholtz filter remain finite.
- `test_gpu_fail_closed.py` PASS after removing FD from the fail-closed list.
- `test_fvm_matrixfree.py::test_fd_matrixfree_cg_matches_fd_direct` PASS.
- `test_gpu_smoke.py::test_fd_ppe_matrix_gpu_factor_matches_cpu` added; skipped
  locally without `--gpu`, but asserts GPU sparse matrix data residency and
  CPU/GPU solve parity when CUDA is available.
- `git diff --check` PASS.

## SOLID-X

No C1 violation introduced. No tested implementation deleted: the host loop is
kept as an explicit legacy regression baseline. The fix moves FD PPE matrix
assembly toward the active backend instead of hiding a CPU path behind a GPU
configuration.
